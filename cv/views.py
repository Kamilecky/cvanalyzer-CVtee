"""cv/views.py - Widoki aplikacji CV (upload, podgląd, lista, usuwanie)."""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from .models import CVDocument, CVSection
from .services.parser import CVParser
from .services.section_detector import SectionDetector
from analysis.utils import start_cv_analysis
from recruitment.tasks import run_profile_extraction_in_thread


def _process_uploaded_cv(uploaded_file, user):
    """Przetwarza pojedynczy plik CV: walidacja, parsowanie, zapis.

    Returns:
        CVDocument instance or None (if validation/parsing failed)
    """
    filename = uploaded_file.name

    is_valid, error = CVParser.validate_file(uploaded_file, filename)
    if not is_valid:
        return None

    result = CVParser.parse(uploaded_file, filename)
    if result['error'] or not result['text']:
        return None

    uploaded_file.seek(0)
    from analysis.services.analyzer import CVAnalyzer
    file_hash = CVAnalyzer.compute_file_hash(uploaded_file)

    uploaded_file.seek(0)
    cv_doc = CVDocument.objects.create(
        user=user,
        original_filename=filename,
        file=uploaded_file,
        file_format=result['format'],
        file_size=uploaded_file.size,
        extracted_text=result['text'],
        file_hash=file_hash,
        title=filename.rsplit('.', 1)[0],
    )

    sections = SectionDetector.detect_sections(result['text'])
    for s in sections:
        CVSection.objects.create(
            document=cv_doc,
            section_type=s['type'],
            title=s['title'],
            content=s['content'],
            start_position=s['start'],
            end_position=s['end'],
            order=s['order'],
        )

    return cv_doc


@login_required
def upload_view(request):
    """Upload CV: single or bulk.

    - Creates CVDocument + sections
    - Runs CV analysis (billing + history) via start_cv_analysis()
    - Runs profile extraction for recruitment
    """
    if request.method == 'POST':
        files_to_process = []

        single_cv = request.FILES.get('single_cv')
        if single_cv:
            files_to_process.append(single_cv)

        multiple_cvs = request.FILES.getlist('multiple_cvs')
        if multiple_cvs:
            files_to_process.extend(multiple_cvs)

        if not files_to_process:
            messages.error(request, _('No valid CV files uploaded.'))
            return redirect('cv_upload')

        uploaded_count = 0
        last_cv_doc = None

        for uploaded_file in files_to_process:
            cv_doc = _process_uploaded_cv(uploaded_file, request.user)
            if cv_doc:
                # CV analysis (billing + history)
                start_cv_analysis(cv_doc, request.user)

                # Profile extraction for recruitment
                run_profile_extraction_in_thread(cv_doc.id, request.user.id)

                uploaded_count += 1
                last_cv_doc = cv_doc

        if uploaded_count == 0:
            messages.error(request, _('No valid CV files uploaded.'))
            return redirect('cv_upload')
        elif uploaded_count == 1 and last_cv_doc:
            messages.success(request, _('CV "%(name)s" uploaded successfully!') % {'name': last_cv_doc.original_filename})
            return redirect('cv_detail', cv_id=last_cv_doc.id)
        else:
            messages.success(request, _('%(count)s CV(s) uploaded and processing.') % {'count': uploaded_count})
            return redirect('cv_list')

    return render(request, 'cv/upload.html')


@login_required
def cv_detail_view(request, cv_id):
    """Szczegóły CV - tekst, sekcje, akcje."""
    cv_doc = get_object_or_404(CVDocument, id=cv_id, user=request.user, is_active=True)
    sections = cv_doc.sections.all()
    return render(request, 'cv/detail.html', {'cv': cv_doc, 'sections': sections})


@login_required
def cv_list_view(request):
    """Lista dokumentów CV użytkownika."""
    cvs = CVDocument.objects.filter(user=request.user, is_active=True).order_by('-uploaded_at')
    return render(request, 'cv/list.html', {'cvs': cvs})


@login_required
@require_POST
def bulk_analyze_view(request):
    """Uruchamia analizę dla WSZYSTKICH CV na liście."""
    cvs = CVDocument.objects.filter(user=request.user, is_active=True)
    cv_count = cvs.count()

    if not cv_count:
        messages.warning(request, _('No CVs to analyze.'))
        return redirect('cv_list')

    remaining = request.user.remaining_analyses()
    if remaining != float('inf') and cv_count > remaining:
        messages.error(
            request,
            _('Not enough analyses remaining. You need %(needed)s but have %(remaining)s left. Upgrade your plan.')
            % {'needed': cv_count, 'remaining': int(remaining)},
        )
        return redirect('cv_list')

    analyzed = 0
    for cv_doc in cvs:
        analysis, status = start_cv_analysis(cv_doc, request.user)
        if status == 'limit_reached':
            break
        if status in ('started', 'cached'):
            analyzed += 1

    if analyzed > 0:
        messages.info(
            request,
            _('Bulk analysis started for %(count)s CV(s).') % {'count': analyzed},
        )
    else:
        messages.error(request, _('You have reached your monthly analysis limit. Upgrade your plan for more.'))

    return redirect('cv_list')


@login_required
@require_POST
def cv_delete_view(request, cv_id):
    """Soft-delete dokumentu CV."""
    cv_doc = get_object_or_404(CVDocument, id=cv_id, user=request.user)
    cv_doc.is_active = False
    cv_doc.save(update_fields=['is_active'])
    messages.success(request, _('CV "%(name)s" deleted.') % {'name': cv_doc.original_filename})
    return redirect('cv_list')
