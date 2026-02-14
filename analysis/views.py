"""analysis/views.py - Widoki aplikacji analizy AI CV."""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from cv.models import CVDocument
from .models import AnalysisResult
from .tasks import run_analysis_in_thread, run_rewrite_in_thread


@login_required
def dashboard_view(request):
    """Dashboard - statystyki, ostatnie analizy, szybkie akcje."""
    recent_analyses = AnalysisResult.objects.filter(
        user=request.user, status='done'
    ).select_related('cv_document')[:5]

    cv_count = CVDocument.objects.filter(user=request.user, is_active=True).count()

    return render(request, 'analysis/dashboard.html', {
        'recent_analyses': recent_analyses,
        'cv_count': cv_count,
    })


@login_required
@require_POST
def start_analysis_view(request, cv_id):
    """Rozpoczyna nową analizę CV (threading.Thread).

    Optymalizacje:
    - Hash-based cache: jeśli identyczne CV, zwraca wynik natychmiast
    - threading.Thread: natychmiastowa odpowiedź, analiza w tle
    """
    cv_doc = get_object_or_404(CVDocument, id=cv_id, user=request.user, is_active=True)

    if not request.user.can_analyze():
        messages.error(request, 'You have reached your monthly analysis limit. Upgrade your plan for more.')
        return redirect('cv_detail', cv_id=cv_id)

    if not cv_doc.extracted_text:
        messages.error(request, 'This CV has no extracted text. Please re-upload.')
        return redirect('cv_detail', cv_id=cv_id)

    # Hash-based cache
    from analysis.services.analyzer import CVAnalyzer
    cached = CVAnalyzer.check_cache(cv_doc)
    if cached:
        cloned = CVAnalyzer.clone_analysis(cached, cv_doc, request.user)
        messages.success(request, 'Instant result from cache (identical CV analyzed before).')
        return redirect('analysis_result', analysis_id=cloned.id)

    analysis = AnalysisResult.objects.create(
        user=request.user,
        cv_document=cv_doc,
        status='pending',
    )

    # Uruchom analizę w tle (threading.Thread)
    run_analysis_in_thread(str(analysis.id))

    return redirect('analysis_processing', analysis_id=analysis.id)


@login_required
def processing_view(request, analysis_id):
    """Strona oczekiwania na wynik analizy z polling."""
    analysis = get_object_or_404(AnalysisResult, id=analysis_id, user=request.user)

    if analysis.status == 'done':
        return redirect('analysis_result', analysis_id=analysis.id)
    if analysis.status == 'failed':
        messages.error(request, f'Analysis failed: {analysis.error_message}')
        return redirect('cv_detail', cv_id=analysis.cv_document_id)

    return render(request, 'analysis/processing.html', {'analysis': analysis})


@login_required
def analysis_status_api(request, analysis_id):
    """JSON endpoint do pollingu statusu analizy z progress %."""
    analysis = get_object_or_404(AnalysisResult, id=analysis_id, user=request.user)
    data = {
        'status': analysis.status,
        'progress': analysis.progress,
    }
    if analysis.status == 'done':
        from django.urls import reverse
        data['redirect_url'] = reverse('analysis_result', args=[analysis.id])
    elif analysis.status == 'failed':
        data['error'] = analysis.error_message
    return JsonResponse(data)


@login_required
def result_view(request, analysis_id):
    """Wynik analizy - sekcje, problemy, rekomendacje, skill gaps."""
    analysis = get_object_or_404(
        AnalysisResult, id=analysis_id, user=request.user, status='done'
    )
    section_analyses = analysis.section_analyses.all()
    problems = analysis.problems.all()
    recommendations = analysis.recommendations.all()
    skill_gaps = analysis.skill_gaps.all()
    rewrites = analysis.rewrites.all()
    sections = analysis.cv_document.sections.all()

    has_recommendations = request.user.has_feature('recommendations')
    has_skill_gap = request.user.has_feature('skill_gap')
    has_rewriting = request.user.has_feature('ai_rewriting')

    return render(request, 'analysis/result.html', {
        'analysis': analysis,
        'section_analyses': section_analyses,
        'problems': problems,
        'recommendations': recommendations,
        'skill_gaps': skill_gaps,
        'rewrites': rewrites,
        'sections': sections,
        'has_recommendations': has_recommendations,
        'has_skill_gap': has_skill_gap,
        'has_rewriting': has_rewriting,
    })


@login_required
def history_view(request):
    """Historia wszystkich analiz użytkownika."""
    analyses = AnalysisResult.objects.filter(
        user=request.user
    ).select_related('cv_document').order_by('-created_at')

    return render(request, 'analysis/history.html', {'analyses': analyses})


@login_required
@require_POST
def rewrite_section_view(request, analysis_id):
    """Rozpoczyna przepisywanie sekcji CV (Premium)."""
    analysis = get_object_or_404(AnalysisResult, id=analysis_id, user=request.user, status='done')

    if not request.user.has_feature('ai_rewriting'):
        messages.error(request, 'AI rewriting is available for Premium users. Upgrade your plan.')
        return redirect('analysis_result', analysis_id=analysis_id)

    section_type = request.POST.get('section_type', '')
    original_text = request.POST.get('original_text', '')

    if not section_type or not original_text:
        messages.error(request, 'Missing section data.')
        return redirect('analysis_result', analysis_id=analysis_id)

    run_rewrite_in_thread(str(analysis.id), section_type, original_text)
    messages.info(request, f'Rewriting "{section_type}" section... Refresh in a moment.')
    return redirect('analysis_result', analysis_id=analysis_id)
