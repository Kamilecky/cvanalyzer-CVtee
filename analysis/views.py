"""analysis/views.py - Widoki aplikacji analizy AI CV."""

from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from cv.models import CVDocument
from .models import AnalysisResult
from .tasks import run_analysis_in_thread, run_rewrite_in_thread
from .utils import start_cv_analysis, invalidate_history_cache, _history_cache_key, HISTORY_CACHE_TTL


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
    """Rozpoczyna nową analizę CV — deleguje do start_cv_analysis()."""
    cv_doc = get_object_or_404(CVDocument, id=cv_id, user=request.user, is_active=True)

    from django.utils.translation import get_language
    lang = (get_language() or 'en')[:2]
    analysis, status = start_cv_analysis(cv_doc, request.user, language=lang)

    if status == 'limit_reached':
        messages.error(request, _('You have reached your monthly analysis limit. Upgrade your plan for more.'))
        return redirect('cv_detail', cv_id=cv_id)

    if status == 'no_text':
        messages.error(request, _('This CV has no extracted text. Please re-upload.'))
        return redirect('cv_detail', cv_id=cv_id)

    if status == 'cached':
        messages.success(request, _('Instant result from cache (identical CV analyzed before).'))
        return redirect('analysis_result', analysis_id=analysis.id)

    # status == 'started'
    return redirect('analysis_processing', analysis_id=analysis.id)


@login_required
def processing_view(request, analysis_id):
    """Strona oczekiwania na wynik analizy z polling."""
    analysis = get_object_or_404(AnalysisResult, id=analysis_id, user=request.user)

    if analysis.status == 'done':
        return redirect('analysis_result', analysis_id=analysis.id)
    if analysis.status == 'partial':
        messages.warning(request, _('Partial results — some AI prompts failed. Data may be incomplete.'))
        return redirect('analysis_result', analysis_id=analysis.id)
    if analysis.status == 'failed':
        messages.error(request, _('Analysis failed: %(error)s') % {'error': analysis.error_message})
        return redirect('cv_detail', cv_id=analysis.cv_document_id)
    if analysis.status == 'pending_ai':
        return render(request, 'analysis/processing.html', {
            'analysis': analysis,
            'pending_ai': True,
        })

    return render(request, 'analysis/processing.html', {'analysis': analysis})


@login_required
def analysis_status_api(request, analysis_id):
    """JSON endpoint do pollingu statusu analizy z progress %."""
    analysis = get_object_or_404(AnalysisResult, id=analysis_id, user=request.user)
    data = {
        'status': analysis.status,
        'progress': analysis.progress,
    }
    if analysis.status in ('done', 'partial'):
        from django.urls import reverse
        data['redirect_url'] = reverse('analysis_result', args=[analysis.id])
    elif analysis.status == 'failed':
        data['error'] = analysis.error_message
    return JsonResponse(data)


@login_required
def result_view(request, analysis_id):
    """Wynik analizy - sekcje, problemy, rekomendacje, skill gaps."""
    analysis = get_object_or_404(
        AnalysisResult, id=analysis_id, user=request.user,
        status__in=['done', 'partial'],
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

    # Check for metadata warnings and prompt errors
    raw = analysis.raw_ai_response or {}
    metadata = raw.get('metadata', {})
    short_text_warning = metadata.get('short_text_warning', False)
    prompt_errors = raw.get('prompt_errors', [])

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
        'is_partial': analysis.status == 'partial',
        'short_text_warning': short_text_warning,
        'prompt_errors': prompt_errors,
    })


@login_required
def history_view(request):
    """Historia analiz użytkownika — paginacja 20/strona, cache Redis 60 s."""
    try:
        page_num = int(request.GET.get('page', 1))
    except (ValueError, TypeError):
        page_num = 1

    cache_key = _history_cache_key(request.user.id, page_num)
    ctx = cache.get(cache_key)

    if ctx is None:
        qs = (
            AnalysisResult.objects
            .filter(user=request.user)
            .select_related('cv_document')
            # Defer heavy fields not needed on the list page
            .defer(
                'raw_ai_response', 'summary', 'sections_detected',
                'error_message', 'celery_task_id', 'openai_tokens_used',
                'processing_time_seconds', 'percentile_rank', 'completed_at',
            )
            # Replace N+1 a.problems.count with a single annotated query
            .annotate(problem_count=Count('problems'))
            .order_by('-created_at')
        )
        paginator = Paginator(qs, 20)
        page_obj = paginator.get_page(page_num)
        # Force evaluation so the queryset is picklable for Redis
        page_obj.object_list = list(page_obj.object_list)
        ctx = {'page_obj': page_obj, 'analyses': page_obj}
        cache.set(cache_key, ctx, HISTORY_CACHE_TTL)

    return render(request, 'analysis/history.html', ctx)


@login_required
@require_POST
def history_delete_all_view(request):
    """Usuwa WSZYSTKIE analizy użytkownika z historii."""
    deleted_count, _ = AnalysisResult.objects.filter(user=request.user).delete()
    invalidate_history_cache(request.user.id)
    messages.success(request, _('Deleted %(n)d analyses from history.') % {'n': deleted_count})
    return redirect('analysis_history')


@login_required
@require_POST
def analysis_delete_view(request, analysis_id):
    """Hard-delete wyniku analizy + powiazanych danych (CASCADE)."""
    analysis = get_object_or_404(AnalysisResult, id=analysis_id, user=request.user)
    cv_name = analysis.cv_document.original_filename
    analysis.delete()
    invalidate_history_cache(request.user.id)
    messages.success(request, _('Analysis for "%(name)s" deleted.') % {'name': cv_name})
    return redirect('analysis_history')


@login_required
@require_POST
def rewrite_section_view(request, analysis_id):
    """Rozpoczyna przepisywanie sekcji CV (Premium)."""
    analysis = get_object_or_404(AnalysisResult, id=analysis_id, user=request.user, status='done')

    if not request.user.has_feature('ai_rewriting'):
        messages.error(request, _('AI rewriting is available for Premium users. Upgrade your plan.'))
        return redirect('analysis_result', analysis_id=analysis_id)

    section_type = request.POST.get('section_type', '')
    original_text = request.POST.get('original_text', '')

    if not section_type or not original_text:
        messages.error(request, _('Missing section data.'))
        return redirect('analysis_result', analysis_id=analysis_id)

    run_rewrite_in_thread(str(analysis.id), section_type, original_text)
    messages.info(request, _('Rewriting "%(section)s" section... Refresh in a moment.') % {'section': section_type})
    return redirect('analysis_result', analysis_id=analysis_id)
