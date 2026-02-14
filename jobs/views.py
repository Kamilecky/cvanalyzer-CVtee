"""jobs/views.py - Widoki dopasowania CV do ofert pracy."""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse

from cv.models import CVDocument
from .models import JobPosting, MatchResult
from .forms import JobMatchForm
from .tasks import run_job_match_task
from .services.scraper import JobScraper


@login_required
def match_input_view(request):
    """Formularz wprowadzania oferty pracy do dopasowania."""
    if not request.user.has_feature('job_matching'):
        messages.error(request, 'Job matching is available for Pro and Premium users.')
        return redirect('dashboard')

    cvs = CVDocument.objects.filter(user=request.user, is_active=True)
    if not cvs.exists():
        messages.warning(request, 'Upload a CV first before matching with jobs.')
        return redirect('cv_upload')

    if request.method == 'POST':
        form = JobMatchForm(request.POST)
        if form.is_valid():
            cv_doc = get_object_or_404(
                CVDocument, id=form.cleaned_data['cv_id'],
                user=request.user, is_active=True
            )
            source_type = form.cleaned_data['source_type']
            job_text = form.cleaned_data.get('job_text', '')
            job_url = form.cleaned_data.get('job_url', '')
            title = form.cleaned_data.get('job_title', '')
            company = form.cleaned_data.get('company', '')

            if source_type == 'url' and job_url:
                scrape_result = JobScraper.scrape_url(job_url)
                if scrape_result['error']:
                    messages.error(request, f'Could not fetch job posting: {scrape_result["error"]}')
                    return redirect('job_match_input')
                job_text = scrape_result['text']
                if not title:
                    title = scrape_result['title']

            job = JobPosting.objects.create(
                user=request.user,
                source_type=source_type,
                source_url=job_url,
                title=title,
                company=company,
                raw_text=job_text,
            )

            match = MatchResult.objects.create(
                user=request.user,
                cv_document=cv_doc,
                job_posting=job,
                status='pending',
            )

            task = run_job_match_task.delay(str(match.id))
            match.celery_task_id = task.id
            match.save(update_fields=['celery_task_id'])

            return redirect('job_match_processing', match_id=match.id)
    else:
        cv_id = request.GET.get('cv_id', cvs.first().id if cvs.exists() else '')
        form = JobMatchForm(initial={'cv_id': cv_id})

    return render(request, 'jobs/match_input.html', {'form': form, 'cvs': cvs})


@login_required
def match_processing_view(request, match_id):
    """Strona oczekiwania na wynik dopasowania."""
    match = get_object_or_404(MatchResult, id=match_id, user=request.user)

    if match.status == 'done':
        return redirect('job_match_result', match_id=match.id)
    if match.status == 'failed':
        messages.error(request, f'Matching failed: {match.error_message}')
        return redirect('job_match_input')

    return render(request, 'jobs/match_processing.html', {'match': match})


@login_required
def match_status_api(request, match_id):
    """JSON endpoint do pollingu statusu dopasowania."""
    match = get_object_or_404(MatchResult, id=match_id, user=request.user)
    data = {'status': match.status}
    if match.status == 'done':
        from django.urls import reverse
        data['redirect_url'] = reverse('job_match_result', args=[match.id])
    elif match.status == 'failed':
        data['error'] = match.error_message
    return JsonResponse(data)


@login_required
def match_result_view(request, match_id):
    """Wynik dopasowania CV do oferty pracy."""
    match = get_object_or_404(
        MatchResult, id=match_id, user=request.user, status='done'
    )
    return render(request, 'jobs/match_result.html', {'match': match})


@login_required
def match_history_view(request):
    """Historia dopasowań użytkownika."""
    matches = MatchResult.objects.filter(
        user=request.user
    ).select_related('cv_document', 'job_posting').order_by('-created_at')
    return render(request, 'jobs/match_history.html', {'matches': matches})
