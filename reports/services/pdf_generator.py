"""reports/services/pdf_generator.py - Generowanie raportów PDF z ReportLab."""

import io
import logging
from django.core.files.base import ContentFile
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether,
)

from analysis.models import AnalysisResult
from reports.models import Report

logger = logging.getLogger(__name__)

# ── Colour palette (matches the app's blue theme) ──────────────────────────
C_BLUE       = colors.HexColor('#2563eb')
C_BLUE_DARK  = colors.HexColor('#1e40af')
C_BLUE_LIGHT = colors.HexColor('#dbeafe')
C_RED        = colors.HexColor('#dc2626')
C_RED_LIGHT  = colors.HexColor('#fee2e2')
C_AMBER      = colors.HexColor('#d97706')
C_AMBER_LT   = colors.HexColor('#fef3c7')
C_GREEN      = colors.HexColor('#16a34a')
C_GREEN_LT   = colors.HexColor('#dcfce7')
C_GREY       = colors.HexColor('#6b7280')
C_GREY_LIGHT = colors.HexColor('#f3f4f6')
C_TEXT       = colors.HexColor('#111827')
PAGE_W, PAGE_H = A4


def _build_styles():
    """Returns a dict of named ParagraphStyles used throughout the document."""
    base = getSampleStyleSheet()
    s = {}
    s['title'] = ParagraphStyle(
        'DocTitle', parent=base['Title'],
        fontSize=22, textColor=colors.white, spaceAfter=2,
        fontName='Helvetica-Bold',
    )
    s['section'] = ParagraphStyle(
        'SectionTitle', parent=base['Heading2'],
        fontSize=13, textColor=C_BLUE_DARK, spaceBefore=14, spaceAfter=6,
        fontName='Helvetica-Bold',
    )
    s['body'] = ParagraphStyle(
        'Body', parent=base['Normal'],
        fontSize=9, textColor=C_TEXT, leading=14, spaceAfter=4,
    )
    s['label'] = ParagraphStyle(
        'Label', parent=base['Normal'],
        fontSize=8, textColor=C_GREY, fontName='Helvetica-Bold', spaceAfter=2,
    )
    s['italic'] = ParagraphStyle(
        'Italic', parent=base['Normal'],
        fontSize=9, textColor=C_GREY, fontName='Helvetica-Oblique',
        leftIndent=12, spaceAfter=4,
    )
    return s


def _page_footer(canvas, doc):
    """Draws page number + brand in the bottom margin of every page."""
    canvas.saveState()
    canvas.setFont('Helvetica', 7)
    canvas.setFillColor(C_GREY)
    canvas.drawString(2 * cm, 1.2 * cm, 'CVeeto \u2014 AI-Powered Resume Analysis')
    canvas.drawRightString(PAGE_W - 2 * cm, 1.2 * cm, f'Page {doc.page}')
    canvas.restoreState()


def _escape(text):
    """Escape XML special characters for ReportLab Paragraph."""
    return (
        str(text)
        .replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
    )


class PDFGenerator:
    """Generuje profesjonalny raport PDF z wynikami analizy CV."""

    @staticmethod
    def generate(report_id):
        """Generuje plik PDF i zapisuje do modelu Report.

        Ulepszenia vs poprzednia wersja:
        - prefetch_related: 1 dodatkowe zapytanie zamiast N dla relacji
        - numery stron w stopce
        - kolorowy nagłówek z meta-danymi analizy
        - tabela Quick Stats (problemy wg severity)
        - kolorowe kafelki problemow i rekomendacji
        - sekcja Rewritten Sections (Premium)
        - czytelna nazwa pliku PDF (nazwa CV, nie UUID)
        """
        report = Report.objects.select_related(
            'analysis', 'analysis__cv_document', 'user',
        ).prefetch_related(
            'analysis__section_analyses',
            'analysis__problems',
            'analysis__recommendations',
            'analysis__skill_gaps',
            'analysis__rewrites',
        ).get(id=report_id)

        analysis = report.analysis
        report.status = 'processing'
        report.save(update_fields=['status'])

        try:
            # Materialize all prefetched relations once (no extra DB hits below)
            section_analyses = list(analysis.section_analyses.all())
            problems         = list(analysis.problems.all())
            recommendations  = list(analysis.recommendations.all())
            skill_gaps       = list(analysis.skill_gaps.all())
            rewrites         = list(analysis.rewrites.all())

            s = _build_styles()
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(
                buffer, pagesize=A4,
                rightMargin=2 * cm, leftMargin=2 * cm,
                topMargin=2 * cm, bottomMargin=2.5 * cm,
            )
            elements = []
            col_full = PAGE_W - 4 * cm

            # ── Blue header ─────────────────────────────────────────────────
            cv_name  = _escape(analysis.cv_document.original_filename)
            date_str = analysis.created_at.strftime('%B %d, %Y')

            header_tbl = Table(
                [[Paragraph('CV Analysis Report', s['title'])]],
                colWidths=[col_full],
            )
            header_tbl.setStyle(TableStyle([
                ('BACKGROUND',    (0, 0), (-1, -1), C_BLUE),
                ('TOPPADDING',    (0, 0), (-1, -1), 16),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('LEFTPADDING',   (0, 0), (-1, -1), 16),
            ]))
            elements.append(header_tbl)
            elements.append(Spacer(1, 0.3 * cm))

            meta_col = col_full / 3
            meta_tbl = Table(
                [[
                    Paragraph(f'<b>Document:</b> {cv_name}', s['body']),
                    Paragraph(f'<b>User:</b> {_escape(report.user.email)}', s['body']),
                    Paragraph(f'<b>Date:</b> {date_str}', s['body']),
                ]],
                colWidths=[meta_col, meta_col, meta_col],
            )
            meta_tbl.setStyle(TableStyle([
                ('BACKGROUND',    (0, 0), (-1, -1), C_BLUE_LIGHT),
                ('TOPPADDING',    (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('LEFTPADDING',   (0, 0), (-1, -1), 10),
            ]))
            elements.append(meta_tbl)
            elements.append(Spacer(1, 0.5 * cm))

            # ── Quick Stats ─────────────────────────────────────────────────
            critical_n = sum(1 for p in problems if p.severity == 'critical')
            warning_n  = sum(1 for p in problems if p.severity == 'warning')
            info_n     = sum(1 for p in problems if p.severity == 'info')
            high_recs  = sum(1 for r in recommendations if r.priority == 'high')
            col_q      = col_full / 4

            stats_tbl = Table(
                [
                    [
                        Paragraph('<b>Critical</b>', s['label']),
                        Paragraph('<b>Warnings</b>', s['label']),
                        Paragraph('<b>Info</b>', s['label']),
                        Paragraph('<b>High-priority recs.</b>', s['label']),
                    ],
                    [
                        Paragraph(f'<font color="#dc2626"><b>{critical_n}</b></font>', s['section']),
                        Paragraph(f'<font color="#d97706"><b>{warning_n}</b></font>', s['section']),
                        Paragraph(f'<font color="#2563eb"><b>{info_n}</b></font>', s['section']),
                        Paragraph(f'<font color="#16a34a"><b>{high_recs}</b></font>', s['section']),
                    ],
                ],
                colWidths=[col_q] * 4,
            )
            stats_tbl.setStyle(TableStyle([
                ('BACKGROUND',    (0, 0), (-1, -1), C_GREY_LIGHT),
                ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
                ('TOPPADDING',    (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID',          (0, 0), (-1, -1), 0.5, colors.white),
            ]))
            elements.append(stats_tbl)
            elements.append(Spacer(1, 0.5 * cm))

            # ── Summary ─────────────────────────────────────────────────────
            if analysis.summary:
                elements.append(Paragraph('Summary', s['section']))
                elements.append(HRFlowable(width='100%', color=C_BLUE_LIGHT, thickness=1))
                elements.append(Spacer(1, 0.15 * cm))
                elements.append(Paragraph(_escape(analysis.summary), s['body']))
                elements.append(Spacer(1, 0.3 * cm))

            # ── Section-by-section analysis ──────────────────────────────────
            if section_analyses:
                elements.append(Paragraph('Section-by-Section Analysis', s['section']))
                elements.append(HRFlowable(width='100%', color=C_BLUE_LIGHT, thickness=1))
                elements.append(Spacer(1, 0.15 * cm))

                STATUS_COLOR = {
                    'present': '#16a34a',
                    'missing': '#dc2626',
                    'weak':    '#d97706',
                }
                for sa in section_analyses:
                    fg_hex = STATUS_COLOR.get(sa.status, '#6b7280')
                    block = [Paragraph(
                        f'<b>{_escape(sa.section.title())}</b>'
                        f' <font color="{fg_hex}">[{sa.get_status_display()}]</font>',
                        s['body'],
                    )]
                    if sa.analysis_text:
                        block.append(Paragraph(_escape(sa.analysis_text), s['body']))
                    for tip in (sa.suggestions or []):
                        block.append(Paragraph(f'\u2022 {_escape(tip)}', s['italic']))
                    block.append(Spacer(1, 0.2 * cm))
                    elements.append(KeepTogether(block))

            # ── Problems ─────────────────────────────────────────────────────
            if problems:
                elements.append(Paragraph('Problems Found', s['section']))
                elements.append(HRFlowable(width='100%', color=C_BLUE_LIGHT, thickness=1))
                elements.append(Spacer(1, 0.15 * cm))

                SEV_BG = {'critical': C_RED_LIGHT, 'warning': C_AMBER_LT, 'info': C_BLUE_LIGHT}
                SEV_FG = {'critical': '#dc2626',   'warning': '#d97706',   'info': '#2563eb'}
                for p in problems:
                    bg     = SEV_BG.get(p.severity, C_GREY_LIGHT)
                    fg_hex = SEV_FG.get(p.severity, '#6b7280')
                    inner  = [
                        Paragraph(
                            f'<font color="{fg_hex}"><b>[{p.get_severity_display().upper()}]</b></font>'
                            f' <b>{_escape(p.title)}</b>',
                            s['body'],
                        ),
                        Paragraph(_escape(p.description), s['body']),
                    ]
                    if p.affected_text:
                        inner.append(Paragraph(
                            f'<i>Affected: &quot;{_escape(p.affected_text[:120])}&quot;</i>',
                            s['italic'],
                        ))
                    box = Table([[inner]], colWidths=[col_full])
                    box.setStyle(TableStyle([
                        ('BACKGROUND',    (0, 0), (-1, -1), bg),
                        ('TOPPADDING',    (0, 0), (-1, -1), 6),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                        ('LEFTPADDING',   (0, 0), (-1, -1), 10),
                        ('RIGHTPADDING',  (0, 0), (-1, -1), 10),
                    ]))
                    elements.append(KeepTogether([box, Spacer(1, 0.2 * cm)]))

            # ── Recommendations ───────────────────────────────────────────────
            if recommendations:
                elements.append(Paragraph('Recommendations', s['section']))
                elements.append(HRFlowable(width='100%', color=C_BLUE_LIGHT, thickness=1))
                elements.append(Spacer(1, 0.15 * cm))

                PRIO_FG = {'high': '#dc2626', 'medium': '#d97706', 'low': '#16a34a'}
                for r in recommendations:
                    fg_hex = PRIO_FG.get(r.priority, '#6b7280')
                    block  = [
                        Paragraph(
                            f'<font color="{fg_hex}"><b>[{r.get_priority_display()}]</b></font>'
                            f' <b>{_escape(r.title)}</b>',
                            s['body'],
                        ),
                        Paragraph(_escape(r.description), s['body']),
                    ]
                    if r.suggested_text:
                        block.append(Paragraph(
                            f'<i>Suggestion: {_escape(r.suggested_text)}</i>',
                            s['italic'],
                        ))
                    elements.append(KeepTogether(block + [Spacer(1, 0.25 * cm)]))

            # ── Skill Gaps ────────────────────────────────────────────────────
            if skill_gaps:
                elements.append(Paragraph('Skill Gaps', s['section']))
                elements.append(HRFlowable(width='100%', color=C_BLUE_LIGHT, thickness=1))
                elements.append(Spacer(1, 0.15 * cm))

                sg_rows = [[
                    Paragraph('<b>Skill</b>', s['label']),
                    Paragraph('<b>Current</b>', s['label']),
                    Paragraph('<b>Recommended</b>', s['label']),
                    Paragraph('<b>Importance</b>', s['label']),
                ]]
                for sg in skill_gaps:
                    sg_rows.append([
                        Paragraph(_escape(sg.skill_name), s['body']),
                        Paragraph(_escape(sg.current_level or '\u2014'), s['body']),
                        Paragraph(_escape(sg.recommended_level or '\u2014'), s['body']),
                        Paragraph(_escape(sg.importance), s['body']),
                    ])
                sg_tbl = Table(sg_rows, colWidths=[5.5 * cm, 3 * cm, 3 * cm, 3 * cm])
                sg_tbl.setStyle(TableStyle([
                    ('BACKGROUND',    (0, 0), (-1, 0),  C_BLUE),
                    ('TEXTCOLOR',     (0, 0), (-1, 0),  colors.white),
                    ('FONTNAME',      (0, 0), (-1, 0),  'Helvetica-Bold'),
                    ('FONTSIZE',      (0, 0), (-1, -1), 9),
                    ('GRID',          (0, 0), (-1, -1), 0.5, colors.white),
                    ('ROWBACKGROUNDS',(0, 1), (-1, -1), [colors.white, C_BLUE_LIGHT]),
                    ('TOPPADDING',    (0, 0), (-1, -1), 5),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                    ('LEFTPADDING',   (0, 0), (-1, -1), 6),
                ]))
                elements.append(sg_tbl)
                elements.append(Spacer(1, 0.4 * cm))

            # ── Rewritten Sections (Premium) ──────────────────────────────────
            if rewrites:
                elements.append(Paragraph('Rewritten Sections', s['section']))
                elements.append(HRFlowable(width='100%', color=C_BLUE_LIGHT, thickness=1))
                elements.append(Spacer(1, 0.15 * cm))

                half = (col_full - 0.4 * cm) / 2
                for rw in rewrites:
                    rw_tbl = Table(
                        [
                            [Paragraph('<b>Original</b>', s['label']),
                             Paragraph('<b>Rewritten</b>', s['label'])],
                            [Paragraph(_escape(rw.original_text), s['body']),
                             Paragraph(_escape(rw.rewritten_text), s['body'])],
                        ],
                        colWidths=[half, half],
                    )
                    rw_tbl.setStyle(TableStyle([
                        ('BACKGROUND',    (0, 0), (0, -1), C_GREY_LIGHT),
                        ('BACKGROUND',    (1, 0), (1, -1), C_GREEN_LT),
                        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
                        ('TOPPADDING',    (0, 0), (-1, -1), 6),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                        ('LEFTPADDING',   (0, 0), (-1, -1), 8),
                        ('GRID',          (0, 0), (-1, -1), 0.5, colors.white),
                    ]))
                    elements.append(KeepTogether([
                        Paragraph(f'<b>{_escape(rw.section_type.title())}</b>', s['body']),
                        Spacer(1, 0.1 * cm),
                        rw_tbl,
                        Spacer(1, 0.3 * cm),
                    ]))

            # ── Build ─────────────────────────────────────────────────────────
            doc.build(elements, onFirstPage=_page_footer, onLaterPages=_page_footer)

            pdf_bytes = buffer.getvalue()
            buffer.close()

            safe_name = (
                analysis.cv_document.original_filename
                .replace(' ', '_').replace('/', '-')[:50]
            )
            filename = f'cv_report_{safe_name}.pdf'

            report.file.save(filename, ContentFile(pdf_bytes), save=False)
            report.status = 'done'
            report.error_message = ''
            report.save()
            return report

        except Exception as e:
            logger.error(f'PDF generation failed for report {report_id}: {e}', exc_info=True)
            report.status = 'failed'
            report.error_message = str(e)
            report.save(update_fields=['status', 'error_message'])
            return report
