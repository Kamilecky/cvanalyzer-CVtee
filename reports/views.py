"""reports/views.py - Widoki generowania i pobierania raportów PDF."""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, FileResponse

from analysis.models import AnalysisResult
from .models import Report
from .tasks import generate_pdf_report_task


@login_required
def generate_report_view(request, analysis_id):
    """Rozpoczyna generowanie raportu PDF."""
    if not request.user.has_feature('pdf_export'):
        messages.error(request, 'PDF export is available for Pro and Premium users.')
        return redirect('analysis_result', analysis_id=analysis_id)

    analysis = get_object_or_404(
        AnalysisResult, id=analysis_id, user=request.user, status='done'
    )

    existing = Report.objects.filter(analysis=analysis, status='done').first()
    if existing:
        return redirect('report_download', report_id=existing.id)

    report = Report.objects.create(
        user=request.user,
        analysis=analysis,
        status='pending',
    )

    task = generate_pdf_report_task.delay(str(report.id))
    report.celery_task_id = task.id
    report.save(update_fields=['celery_task_id'])

    return render(request, 'reports/generating.html', {'report': report})


@login_required
def report_status_api(request, report_id):
    """JSON endpoint do pollingu statusu raportu."""
    report = get_object_or_404(Report, id=report_id, user=request.user)
    data = {'status': report.status}
    if report.status == 'done':
        from django.urls import reverse
        data['download_url'] = reverse('report_download', args=[report.id])
    elif report.status == 'failed':
        data['error'] = report.error_message
    return JsonResponse(data)


@login_required
def download_report_view(request, report_id):
    """Pobieranie wygenerowanego raportu PDF."""
    report = get_object_or_404(Report, id=report_id, user=request.user, status='done')

    if not report.file:
        messages.error(request, 'Report file not found.')
        return redirect('dashboard')

    return FileResponse(
        report.file.open('rb'),
        as_attachment=True,
        filename=f'cv_analysis_report_{report.analysis_id}.pdf',
    )
