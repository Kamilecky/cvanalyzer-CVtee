"""cv/views.py - Widoki aplikacji CV (upload, podgląd, lista, usuwanie)."""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST

from .models import CVDocument, CVSection
from .forms import CVUploadForm
from .services.parser import CVParser
from .services.section_detector import SectionDetector


@login_required
def upload_view(request):
    """Upload CV z drag & drop. Parsuje tekst i wykrywa sekcje."""
    if request.method == 'POST':
        form = CVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = request.FILES['file']
            filename = uploaded_file.name

            is_valid, error = CVParser.validate_file(uploaded_file, filename)
            if not is_valid:
                messages.error(request, error)
                return redirect('cv_upload')

            result = CVParser.parse(uploaded_file, filename)
            if result['error']:
                messages.error(request, f'Error parsing file: {result["error"]}')
                return redirect('cv_upload')

            if not result['text']:
                messages.error(request, 'Could not extract text. Please try another format.')
                return redirect('cv_upload')

            # Oblicz hash pliku dla cache (identyczne CV = natychmiastowy wynik)
            uploaded_file.seek(0)
            from analysis.services.analyzer import CVAnalyzer
            file_hash = CVAnalyzer.compute_file_hash(uploaded_file)

            uploaded_file.seek(0)
            cv_doc = CVDocument.objects.create(
                user=request.user,
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

            messages.success(request, f'CV "{filename}" uploaded successfully!')
            return redirect('cv_detail', cv_id=cv_doc.id)
    else:
        form = CVUploadForm()

    return render(request, 'cv/upload.html', {'form': form})


@login_required
def cv_detail_view(request, cv_id):
    """Szczegóły CV - tekst, sekcje, akcje."""
    cv_doc = get_object_or_404(CVDocument, id=cv_id, user=request.user, is_active=True)
    sections = cv_doc.sections.all()
    return render(request, 'cv/detail.html', {'cv': cv_doc, 'sections': sections})


@login_required
def cv_list_view(request):
    """Lista dokumentów CV użytkownika."""
    cvs = CVDocument.objects.filter(user=request.user, is_active=True)
    return render(request, 'cv/list.html', {'cvs': cvs})


@login_required
@require_POST
def cv_delete_view(request, cv_id):
    """Soft-delete dokumentu CV."""
    cv_doc = get_object_or_404(CVDocument, id=cv_id, user=request.user)
    cv_doc.is_active = False
    cv_doc.save(update_fields=['is_active'])
    messages.success(request, f'CV "{cv_doc.original_filename}" deleted.')
    return redirect('cv_list')
