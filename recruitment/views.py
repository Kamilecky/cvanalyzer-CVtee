"""recruitment/views.py - Widoki modułu rekrutacji HR."""

import logging

from django.conf import settings

logger = logging.getLogger(__name__)
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST
from django.db.models import Avg

from cv.models import CVDocument
from cv.services.parser import CVParser
from cv.services.section_detector import SectionDetector
from analysis.utils import start_cv_analysis
from analysis.models import AnalysisResult
from .models import JobPosition, CandidateProfile, JobFitResult, RequirementMatch, PositionWeightTemplate
from .forms import JobPositionForm, BulkUploadForm, CVUploadForm
from .tasks import (
    run_profile_extraction_in_thread,
    run_position_match_in_thread,
    run_bulk_matching_in_thread,
    run_selective_matching_in_thread,
)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@login_required
def dashboard_view(request):
    """Główny dashboard rekrutacyjny ze statystykami."""

    positions = JobPosition.objects.filter(user=request.user, is_active=True)
    profiles = CandidateProfile.objects.filter(user=request.user, status='done')

    total_positions = positions.count()
    total_candidates = profiles.count()
    total_matches = JobFitResult.objects.filter(user=request.user, status='done').count()

    recent_positions = positions[:5]
    top_candidates = profiles.annotate(
        avg_match=Avg('fit_results__overall_match'),
    ).filter(avg_match__isnull=False).order_by('-avg_match')[:10]

    return render(request, 'recruitment/dashboard.html', {
        'total_positions': total_positions,
        'total_candidates': total_candidates,
        'total_matches': total_matches,
        'recent_positions': recent_positions,
        'top_candidates': top_candidates,
    })


# ---------------------------------------------------------------------------
# Positions CRUD
# ---------------------------------------------------------------------------

@login_required
def position_list_view(request):
    positions = JobPosition.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'recruitment/position_list.html', {'positions': positions})


@login_required
def position_create_view(request):
    position_limit = settings.JOB_POSITION_LIMITS.get(request.user.plan)
    if position_limit is not None:
        current_count = JobPosition.objects.filter(
            user=request.user, is_active=True,
        ).count()
        if current_count >= position_limit:
            messages.error(
                request,
                _('Limit of %(limit)s active positions reached. '
                  'Upgrade your plan to create more.') % {'limit': position_limit},
            )
            return redirect('recruitment_position_list')

    if request.method == 'POST':
        form = JobPositionForm(request.POST)
        if form.is_valid():
            position = form.save(commit=False)
            position.user = request.user
            position.save()
            messages.success(request, _('Position "%(title)s" created.') % {'title': position.title})
            return redirect('recruitment_position_detail', position_id=position.id)
    else:
        form = JobPositionForm()

    return render(request, 'recruitment/position_form.html', {
        'form': form, 'title': 'Create Position',
    })


@login_required
def position_edit_view(request, position_id):
    position = get_object_or_404(JobPosition, id=position_id, user=request.user)

    if request.method == 'POST':
        form = JobPositionForm(request.POST, instance=position)
        if form.is_valid():
            form.save()
            messages.success(request, _('Position "%(title)s" updated.') % {'title': position.title})
            return redirect('recruitment_position_detail', position_id=position.id)
    else:
        form = JobPositionForm(instance=position)

    return render(request, 'recruitment/position_form.html', {
        'form': form, 'title': 'Edit Position', 'position': position,
    })


@login_required
@require_POST
def position_delete_view(request, position_id):
    position = get_object_or_404(JobPosition, id=position_id, user=request.user)
    position.is_active = False
    position.save(update_fields=['is_active'])
    messages.success(request, _('Position "%(title)s" deactivated.') % {'title': position.title})
    return redirect('recruitment_position_list')


@login_required
@require_POST
def candidate_delete_view(request, profile_id):
    """Hard-delete profilu kandydata + powiazanych JobFitResult (CASCADE)."""
    from django.urls import reverse
    qs = CandidateProfile.objects.filter(id=profile_id)
    if not request.user.is_superuser:
        qs = qs.filter(user=request.user)

    profile = qs.first()
    if not profile:
        return redirect(reverse('recruitment_candidate_list') + '?delete_error=1')

    name = profile.name or str(profile.id)[:8]
    profile.delete()
    messages.success(request, _('Candidate "%(name)s" deleted.') % {'name': name})
    return redirect('recruitment_candidate_list')


@login_required
def position_detail_view(request, position_id):
    """Szczegóły stanowiska + ranking kandydatów."""
    position = get_object_or_404(JobPosition, id=position_id, user=request.user)

    sort_by = request.GET.get('sort', 'overall_match')
    valid_sorts = ['overall_match', 'skill_match', 'experience_match', 'seniority_match']
    if sort_by not in valid_sorts:
        sort_by = 'overall_match'

    fit_results = JobFitResult.objects.filter(
        position=position, status='done',
    ).select_related('candidate').order_by(f'-{sort_by}')

    return render(request, 'recruitment/position_detail.html', {
        'position': position,
        'fit_results': fit_results,
        'current_sort': sort_by,
    })


# ---------------------------------------------------------------------------
# Candidates
# ---------------------------------------------------------------------------

@login_required
def candidate_list_view(request):
    """Lista kandydatów z wyszukiwaniem.

    Kandydaci powiązani z oflagowanym CV (security_flags != []) są automatycznie
    wykluczani z listy i pokazywani w ostrzeżeniu modalnym.
    """
    # 1. Wykryj CV z aktywnymi (nie odwołanymi) flagami bezpieczeństwa
    flagged_cv_doc_ids = set(
        AnalysisResult.objects
        .filter(user=request.user, injection_dismissed=False)
        .exclude(security_flags=[])
        .values_list('cv_document_id', flat=True)
    )

    # 2. Pobierz oflagowanych kandydatów (do modala ostrzeżenia)
    flagged_profiles = []
    if flagged_cv_doc_ids:
        flagged_profiles = list(
            CandidateProfile.objects
            .filter(user=request.user, cv_document_id__in=flagged_cv_doc_ids)
            .select_related('cv_document')
            .order_by('-created_at')
        )
        # Dołącz flagi do każdego profilu (do wyświetlenia w modalu)
        flagged_analyses = {
            a.cv_document_id: a
            for a in AnalysisResult.objects
            .filter(user=request.user, cv_document_id__in=flagged_cv_doc_ids)
            .exclude(security_flags=[])
            .order_by('-created_at')
        }
        for p in flagged_profiles:
            analysis = flagged_analyses.get(p.cv_document_id)
            p.flagged_analysis = analysis
            p.flagged_types = sorted({
                f.get('type', 'unknown')
                for f in (analysis.security_flags if analysis else [])
            })
            p.flagged_risk = (analysis.security_flags[0].get('risk_level', 'LOW')
                              if analysis and analysis.security_flags else 'LOW')

    # 3. Lista kandydatów BEZ oflagowanych
    profiles = CandidateProfile.objects.filter(
        user=request.user, status__in=['done', 'partial'],
    ).exclude(
        cv_document_id__in=flagged_cv_doc_ids,
    ).order_by('-created_at')

    q = request.GET.get('q', '').strip()
    if q:
        profiles = profiles.filter(name__icontains=q)

    profiles_list = list(profiles)

    # 4. Attach latest completed analysis ID to each profile (single query)
    cv_doc_ids = [p.cv_document_id for p in profiles_list if p.cv_document_id]
    analysis_map = {}
    for a in AnalysisResult.objects.filter(
        cv_document_id__in=cv_doc_ids, status__in=['done', 'partial'],
    ).order_by('-created_at').values('cv_document_id', 'id'):
        if a['cv_document_id'] not in analysis_map:
            analysis_map[a['cv_document_id']] = str(a['id'])
    for p in profiles_list:
        p.analysis_id = analysis_map.get(p.cv_document_id)

    active_positions = JobPosition.objects.filter(
        user=request.user, is_active=True,
    ).order_by('-created_at')

    return render(request, 'recruitment/candidate_list.html', {
        'profiles': profiles_list,
        'query': q,
        'active_positions': active_positions,
        'flagged_profiles': flagged_profiles,
        'flagged_count': len(flagged_profiles),
    })


@login_required
def candidate_upload_view(request):
    """Upload CV: pojedyncze lub wiele plikow jednoczesnie."""
    positions = JobPosition.objects.filter(user=request.user, is_active=True).order_by('-created_at')

    if request.method == 'POST':
        form = CVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            # Save selected positions to session for auto-matching
            position_ids = request.POST.getlist('position_ids')
            if position_ids:
                request.session['selected_position_ids'] = position_ids

            files_to_process = []

            single_cv = form.cleaned_data.get('single_cv')
            if single_cv:
                files_to_process.append(single_cv)

            multiple_cvs = request.FILES.getlist('multiple_cvs')
            if multiple_cvs:
                files_to_process.extend(multiple_cvs)

            uploaded_count = 0
            last_cv_doc = None
            from django.utils.translation import get_language as _get_language
            lang = (_get_language() or 'en')[:2]
            for uploaded_file in files_to_process:
                cv_doc = _process_uploaded_cv(uploaded_file, request.user)
                if cv_doc:
                    if cv_doc.injection_flag:
                        messages.warning(
                            request,
                            _('CV "%(name)s" was flagged as suspicious and will not be processed.')
                            % {'name': cv_doc.original_filename},
                        )
                    else:
                        run_profile_extraction_in_thread(cv_doc.id, request.user.id, language=lang)

                        # CV analysis (billing + history) — same logic as /cv/upload/
                        start_cv_analysis(cv_doc, request.user, language=lang)

                    uploaded_count += 1
                    last_cv_doc = cv_doc

            if uploaded_count == 1 and last_cv_doc:
                messages.info(request, _('CV "%(name)s" uploaded. Extracting profile...') % {'name': last_cv_doc.original_filename})
                return redirect('recruitment_candidate_processing', cv_id=last_cv_doc.id)
            elif uploaded_count > 1:
                messages.success(request, _('%(count)s CV(s) uploaded and processing.') % {'count': uploaded_count})
                return redirect('recruitment_candidate_list')
            else:
                messages.error(request, _('No valid CV files uploaded.'))
                return redirect('recruitment_candidate_upload')
    else:
        form = CVUploadForm()

    return render(request, 'recruitment/bulk_upload.html', {
        'form': form,
        'positions': positions,
    })


def _process_uploaded_cv(uploaded_file, user):
    """Przetwarza pojedynczy plik CV: walidacja, parsowanie, zapis."""
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

    # Duplicate detection: return existing CVDocument if same file was already uploaded
    if file_hash:
        existing = CVDocument.objects.filter(user=user, file_hash=file_hash, is_active=True).first()
        if existing:
            logger.info(f"Duplicate CV detected for user {user.id}: hash {file_hash[:8]} matches CV {existing.id}")
            return existing

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
    from cv.models import CVSection
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
def bulk_upload_view(request):
    """Bulk upload wielu CV — redirect do combined upload."""
    return redirect('recruitment_candidate_upload')


@login_required
def candidate_processing_view(request, cv_id):
    """Strona oczekiwania na ekstrakcję profilu."""
    cv_doc = get_object_or_404(CVDocument, id=cv_id, user=request.user)

    try:
        profile = cv_doc.candidate_profile
        if profile.status == 'done':
            return redirect('recruitment_candidate_detail', profile_id=profile.id)
        elif profile.status == 'partial':
            messages.warning(request, _('Partial profile — some data extracted via fallback.'))
            return redirect('recruitment_candidate_detail', profile_id=profile.id)
        elif profile.status == 'failed':
            messages.error(request, _('Profile extraction failed: %(error)s') % {'error': profile.error_message})
            return redirect('recruitment_candidate_list')
    except CandidateProfile.DoesNotExist:
        pass

    return render(request, 'recruitment/processing.html', {
        'cv_doc': cv_doc,
        'message': 'Extracting candidate profile from CV...',
    })


@login_required
def candidate_status_api(request, cv_id):
    """JSON API dla pollingu statusu ekstrakcji profilu."""
    cv_doc = get_object_or_404(CVDocument, id=cv_id, user=request.user)

    try:
        profile = cv_doc.candidate_profile
        data = {'status': profile.status}
        if profile.status in ('done', 'partial'):
            from django.urls import reverse
            position_ids = request.session.get('selected_position_ids')
            if position_ids:
                data['redirect_url'] = reverse('recruitment_auto_match', args=[profile.id])
            else:
                data['redirect_url'] = reverse('recruitment_select_positions', args=[profile.id])
        elif profile.status == 'failed':
            data['error'] = profile.error_message
        return JsonResponse(data)
    except CandidateProfile.DoesNotExist:
        return JsonResponse({'status': 'pending'})


@login_required
def candidate_detail_view(request, profile_id):
    """Profil kandydata + wszystkie dopasowania do stanowisk."""
    profile = get_object_or_404(CandidateProfile, id=profile_id, user=request.user)

    fit_results = list(
        JobFitResult.objects.filter(
            candidate=profile, status='done',
        ).select_related('position').order_by('-overall_match')
    )

    # Show "no match" modal when ALL results are weak or not recommended
    all_not_fit = bool(fit_results) and all(
        fit.fit_recommendation in ('not_recommended', 'weak_fit')
        for fit in fit_results
    )

    return render(request, 'recruitment/candidate_detail.html', {
        'profile': profile,
        'fit_results': fit_results,
        'all_not_fit': all_not_fit,
    })


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------

@login_required
@require_POST
def match_all_positions_view(request, profile_id):
    """Uruchamia matching kandydata do wszystkich aktywnych stanowisk."""
    profile = CandidateProfile.objects.filter(
        id=profile_id, user=request.user, status__in=['done', 'partial']
    ).first()
    if not profile:
        messages.error(request, _('Candidate profile not found or not yet ready for matching.'))
        return redirect('recruitment_candidate_list')

    positions = JobPosition.objects.filter(user=request.user, is_active=True)
    if not positions.exists():
        messages.warning(request, _('No active positions to match against.'))
        return redirect('recruitment_candidate_detail', profile_id=profile_id)

    run_bulk_matching_in_thread(str(profile.id), request.user.id)
    messages.info(request, _('Matching %(name)s to all active positions...') % {'name': profile.name})
    return redirect('recruitment_candidate_detail', profile_id=profile.id)


@login_required
def fit_result_detail_view(request, fit_id):
    """Szczegółowy wynik dopasowania kandydata do stanowiska."""
    fit = get_object_or_404(
        JobFitResult, id=fit_id, user=request.user,
        status__in=['done', 'partial'],
    )

    requirement_matches = fit.requirement_matches.all().order_by('-match_percentage')

    section_scores = fit.section_scores.all().order_by('-weight', '-score')

    return render(request, 'recruitment/fit_result.html', {
        'fit': fit,
        'requirement_matches': requirement_matches,
        'section_scores': section_scores,
        'is_partial': fit.status == 'partial',
    })


@login_required
def fit_status_api(request, fit_id):
    """JSON API dla pollingu statusu dopasowania."""
    fit = get_object_or_404(JobFitResult, id=fit_id, user=request.user)
    data = {
        'status': fit.status,
        'progress': fit.progress,
        'overall_match': fit.overall_match,
    }
    if fit.status in ('done', 'partial'):
        from django.urls import reverse
        data['redirect_url'] = reverse('recruitment_fit_result', args=[fit.id])
    elif fit.status == 'failed':
        data['error'] = fit.error_message
    return JsonResponse(data)


@login_required
@require_POST
def generate_questions_view(request, fit_id):
    """Generuje pytania rekrutacyjne AI (Premium)."""
    if not request.user.has_feature('interview_questions'):
        messages.error(request, _('Interview questions require Premium plan.'))
        return redirect('recruitment_fit_result', fit_id=fit_id)

    fit = get_object_or_404(
        JobFitResult, id=fit_id, user=request.user, status='done',
    )

    from recruitment.services.interview_generator import InterviewGenerator
    generator = InterviewGenerator()
    questions = generator.generate_questions(fit)

    if questions:
        messages.success(request, _('%(count)s interview questions generated.') % {'count': len(questions)})
    else:
        messages.error(request, _('Failed to generate interview questions.'))

    return redirect('recruitment_fit_result', fit_id=fit_id)


# ---------------------------------------------------------------------------
# Selective Matching
# ---------------------------------------------------------------------------

@login_required
def select_positions_view(request, profile_id):
    """Wybor stanowisk do matchingu (checkboxy)."""
    profile = CandidateProfile.objects.filter(
        id=profile_id, user=request.user, status__in=['done', 'partial']
    ).first()
    if not profile:
        messages.error(request, _('Candidate profile not found or not yet ready for matching.'))
        return redirect('recruitment_candidate_list')

    positions = JobPosition.objects.filter(user=request.user, is_active=True).order_by('-created_at')

    existing_fits = {
        str(fit.position_id): fit
        for fit in JobFitResult.objects.filter(
            candidate=profile, status='done',
        ).select_related('position')
    }

    positions_with_status = []
    for pos in positions:
        fit = existing_fits.get(str(pos.id))
        positions_with_status.append({
            'position': pos,
            'existing_match': fit.overall_match if fit else None,
            'fit_id': fit.id if fit else None,
        })

    return render(request, 'recruitment/select_positions.html', {
        'profile': profile,
        'positions_with_status': positions_with_status,
    })


@login_required
@require_POST
def match_selected_positions_view(request, profile_id):
    """Uruchamia matching kandydata do WYBRANYCH stanowisk."""
    profile = CandidateProfile.objects.filter(
        id=profile_id, user=request.user, status__in=['done', 'partial']
    ).first()
    if not profile:
        messages.error(request, _('Candidate profile not found or not yet ready for matching.'))
        return redirect('recruitment_candidate_list')

    position_ids = request.POST.getlist('position_ids')
    if not position_ids:
        messages.error(request, _('Select at least one position to analyze.'))
        return redirect('recruitment_select_positions', profile_id=profile.id)

    run_selective_matching_in_thread(str(profile.id), request.user.id, position_ids)
    messages.info(request, _('Matching %(name)s to %(count)s selected position(s)...') % {'name': profile.name, 'count': len(position_ids)})
    return redirect('recruitment_candidate_detail', profile_id=profile.id)


@login_required
def selective_match_status_api(request, profile_id):
    """JSON API: status matchingu wybranych stanowisk."""
    profile = get_object_or_404(CandidateProfile, id=profile_id, user=request.user)

    pending_fits = JobFitResult.objects.filter(
        candidate=profile,
        status__in=['pending', 'processing', 'pending_ai'],
    )

    if pending_fits.exists():
        return JsonResponse({'status': 'processing'})

    from django.urls import reverse
    return JsonResponse({
        'status': 'done',
        'redirect_url': reverse('recruitment_candidate_detail', args=[profile.id]),
    })


# ---------------------------------------------------------------------------
# Position Ranks
# ---------------------------------------------------------------------------

@login_required
def position_ranks_view(request):
    """Ranking top 3 kandydatow per stanowisko z podswietlonymi skillami."""
    positions = JobPosition.objects.filter(user=request.user, is_active=True).order_by('-created_at')

    position_ranks = []
    for position in positions:
        top_fits = JobFitResult.objects.filter(
            position=position, status='done',
        ).select_related('candidate').order_by('-overall_match')[:3]

        if not top_fits:
            position_ranks.append({
                'position': position,
                'candidates': [],
            })
            continue

        candidates = []
        for rank, fit in enumerate(top_fits, 1):
            profile = fit.candidate
            candidate_skills = profile.skills or []

            # Use AI-computed matching_skills (semantic match) for highlighting.
            # Fall back to exact lowercase comparison against position.required_skills
            # only when matching_skills is empty (e.g. legacy records).
            if fit.matching_skills:
                matched_lower = {s.lower() for s in fit.matching_skills}
            else:
                matched_lower = {s.lower() for s in (position.required_skills or [])}

            highlighted_skills = []
            for skill in candidate_skills:
                highlighted_skills.append({
                    'name': skill,
                    'is_match': skill.lower() in matched_lower,
                })

            candidates.append({
                'rank': rank,
                'fit': fit,
                'profile': profile,
                'highlighted_skills': highlighted_skills,
            })

        position_ranks.append({
            'position': position,
            'candidates': candidates,
        })

    return render(request, 'recruitment/position_ranks.html', {
        'position_ranks': position_ranks,
    })


# ---------------------------------------------------------------------------
# Auto Match + Summary
# ---------------------------------------------------------------------------

@login_required
def auto_match_view(request, profile_id):
    """Auto-matching po ekstrakcji profilu z pozycjami z sesji."""
    profile = CandidateProfile.objects.filter(
        id=profile_id, user=request.user, status__in=['done', 'partial']
    ).first()
    if not profile:
        messages.error(request, _('Candidate profile not found or not yet ready for matching.'))
        return redirect('recruitment_candidate_list')

    position_ids = request.session.pop('selected_position_ids', [])
    if not position_ids:
        return redirect('recruitment_select_positions', profile_id=profile.id)

    run_selective_matching_in_thread(str(profile.id), request.user.id, position_ids)

    return render(request, 'recruitment/match_processing.html', {
        'profile': profile,
    })


@login_required
def match_summary_view(request, profile_id):
    """Podsumowanie dopasowania: tylko % per stanowisko."""
    profile = CandidateProfile.objects.filter(
        id=profile_id, user=request.user, status__in=['done', 'partial']
    ).first()
    if not profile:
        messages.error(request, _('Candidate profile not found or not yet ready for matching.'))
        return redirect('recruitment_candidate_list')

    fit_results = JobFitResult.objects.filter(
        candidate=profile, status='done',
    ).select_related('position').order_by('-overall_match')

    return render(request, 'recruitment/match_summary.html', {
        'profile': profile,
        'fit_results': fit_results,
    })


# ---------------------------------------------------------------------------
# Bulk Analysis (all candidates × selected positions)
# ---------------------------------------------------------------------------

@login_required
@require_POST
def bulk_analysis_view(request):
    """Uruchamia matching WSZYSTKICH kandydatów do wybranych stanowisk."""
    position_ids = request.POST.getlist('position_ids')
    if not position_ids:
        messages.error(request, _('Select at least one position.'))
        return redirect('recruitment_candidate_list')

    positions = JobPosition.objects.filter(
        id__in=position_ids, user=request.user, is_active=True,
    )
    if not positions.exists():
        messages.error(request, _('Select at least one position.'))
        return redirect('recruitment_candidate_list')

    candidates = CandidateProfile.objects.filter(
        user=request.user, status='done',
    )
    if not candidates.exists():
        messages.warning(request, _('No candidates available for analysis.'))
        return redirect('recruitment_candidate_list')

    valid_position_ids = [str(p.id) for p in positions]
    for profile in candidates:
        run_selective_matching_in_thread(
            str(profile.id), request.user.id, valid_position_ids,
        )

    messages.info(
        request,
        _('Bulk analysis started: %(candidates)s candidates × %(positions)s positions.')
        % {'candidates': candidates.count(), 'positions': positions.count()},
    )
    return redirect('recruitment_candidate_list')


@login_required
def bulk_analysis_status_api(request):
    """JSON API: status zbiorczego matchingu."""
    pending_count = JobFitResult.objects.filter(
        user=request.user,
        status__in=['pending', 'processing', 'pending_ai'],
    ).count()

    return JsonResponse({
        'status': 'processing' if pending_count > 0 else 'done',
        'pending_count': pending_count,
    })


# ---------------------------------------------------------------------------
# Position Ranking with Custom Weights
# ---------------------------------------------------------------------------

@login_required
def position_ranking_view(request, position_id):
    """Panel rankingu kandydatów z wagami kryteriów HR."""
    position = get_object_or_404(JobPosition, id=position_id, user=request.user)

    template, _ = PositionWeightTemplate.objects.get_or_create(position=position)
    weights = template.to_dict()

    from recruitment.services.weight_engine import compute_ranking, get_panel_suggestions, CRITERIA_LABELS
    ranking = compute_ranking(position, weights, request.user)
    panel_suggestions = get_panel_suggestions(position, ranking)

    criteria = [
        {'key': key, 'label': label, 'value': weights[key]}
        for key, label in CRITERIA_LABELS.items()
    ]

    return render(request, 'recruitment/position_ranking.html', {
        'position': position,
        'weights': weights,
        'criteria': criteria,
        'ranking': ranking,
        'panel_suggestions': panel_suggestions,
        'total_candidates': len(ranking),
    })


@login_required
def live_ranking_api(request, position_id):
    """JSON API: przelicza ranking na żywo bez zapisywania wag (preview)."""
    position = get_object_or_404(JobPosition, id=position_id, user=request.user)

    from recruitment.services.weight_engine import weights_from_dict, compute_ranking
    weights = weights_from_dict(request.GET)
    ranking = compute_ranking(position, weights, request.user)

    return JsonResponse({'ranking': ranking})


@login_required
def position_weights_api(request, position_id):
    """JSON API: GET pobiera wagi, POST zapisuje i zwraca nowy ranking."""
    import json as _json

    position = get_object_or_404(JobPosition, id=position_id, user=request.user)

    if request.method == 'POST':
        try:
            data = _json.loads(request.body)
        except Exception:
            data = {}

        from recruitment.services.weight_engine import weights_from_dict, compute_ranking, get_panel_suggestions
        weights = weights_from_dict(data)

        template, _ = PositionWeightTemplate.objects.get_or_create(position=position)
        template.w_experience = weights['experience']
        template.w_education = weights['education']
        template.w_certifications = weights['certifications']
        template.w_hard_skills = weights['hard_skills']
        template.w_soft_skills = weights['soft_skills']
        template.w_languages = weights['languages']
        template.save()

        ranking = compute_ranking(position, weights, request.user)
        panel_suggestions = get_panel_suggestions(position, ranking)
        return JsonResponse({'saved': True, 'weights': weights, 'ranking': ranking, 'panel_suggestions': panel_suggestions})

    # GET
    template, _ = PositionWeightTemplate.objects.get_or_create(position=position)
    return JsonResponse({'weights': template.to_dict()})


# ---------------------------------------------------------------------------
# Flagged CVs — Prompt Injection Security
# ---------------------------------------------------------------------------

@login_required
def flagged_cvs_view(request):
    """Lista CV z wykrytymi próbami Prompt Injection.

    Pokazuje dwie sekcje:
    - Aktywne (injection_dismissed=False) — wymagają uwagi
    - Odwołane (injection_dismissed=True) — zarchiwizowane przez rekrutera
    """
    if not request.user.has_feature('recruitment'):
        messages.error(request, _('Recruitment module requires a Pro plan or higher.'))
        return redirect('billing_plans')

    show_dismissed = request.GET.get('show_dismissed') == '1'

    active_results    = []
    dismissed_results = []

    try:
        flagged_analyses = (
            AnalysisResult.objects
            .filter(user=request.user)
            .exclude(security_flags=[])
            .select_related('cv_document')
            .order_by('-created_at')
        )
        for analysis in flagged_analyses:
            profile = None
            try:
                profile = analysis.cv_document.candidate_profile
            except Exception:
                pass
            flags = analysis.security_flags or []
            item = {
                'analysis':    analysis,
                'cv_document': analysis.cv_document,
                'profile':     profile,
                'flags':       flags,
                'flag_types':  sorted({f.get('type', 'unknown') for f in flags}),
            }
            if analysis.injection_dismissed:
                dismissed_results.append(item)
            else:
                active_results.append(item)
    except Exception as e:
        logger.warning(f"flagged_cvs_view query error: {e}")

    return render(request, 'recruitment/flagged_cvs.html', {
        'results':          active_results,
        'dismissed':        dismissed_results,
        'total':            len(active_results),
        'dismissed_count':  len(dismissed_results),
        'show_dismissed':   show_dismissed,
    })


@login_required
@require_POST
def flagged_cv_dismiss_view(request, analysis_id):
    """Odwołuje (dismissuje) alert dla pojedynczego CV."""
    analysis = get_object_or_404(
        AnalysisResult, id=analysis_id, user=request.user,
    )
    analysis.injection_dismissed = True
    analysis.save(update_fields=['injection_dismissed'])
    messages.success(request, _('Alert dismissed. The CV will no longer appear in the warning badge.'))
    return redirect('recruitment_flagged_cvs')


@login_required
@require_POST
def flagged_cv_restore_view(request, analysis_id):
    """Przywraca odwołany alert dla pojedynczego CV."""
    analysis = get_object_or_404(
        AnalysisResult, id=analysis_id, user=request.user,
    )
    analysis.injection_dismissed = False
    analysis.save(update_fields=['injection_dismissed'])
    messages.success(request, _('Alert restored. The CV will appear in the warning badge again.'))
    return redirect('recruitment_flagged_cvs')


@login_required
@require_POST
def flagged_cvs_dismiss_all_view(request):
    """Odwołuje wszystkie aktywne alerty (zbiorczo)."""
    updated = (
        AnalysisResult.objects
        .filter(user=request.user, injection_dismissed=False)
        .exclude(security_flags=[])
        .update(injection_dismissed=True)
    )
    messages.success(
        request,
        _('%(n)d alert(s) dismissed. The badge and warnings will no longer appear.') % {'n': updated},
    )
    return redirect('recruitment_flagged_cvs')
