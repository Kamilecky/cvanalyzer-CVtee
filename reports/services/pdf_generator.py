"""reports/services/pdf_generator.py - Generowanie raportów PDF z ReportLab."""

import io
import logging
from django.core.files.base import ContentFile
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
)

from analysis.models import AnalysisResult
from reports.models import Report

logger = logging.getLogger(__name__)


class PDFGenerator:
    """Generuje raport PDF z wynikami analizy CV."""

    @staticmethod
    def generate(report_id):
        """Generuje plik PDF i zapisuje do modelu Report."""
        report = Report.objects.select_related('analysis', 'analysis__cv_document', 'user').get(id=report_id)
        analysis = report.analysis
        report.status = 'processing'
        report.save(update_fields=['status'])

        try:
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(
                buffer, pagesize=A4,
                rightMargin=2 * cm, leftMargin=2 * cm,
                topMargin=2 * cm, bottomMargin=2 * cm,
            )

            styles = getSampleStyleSheet()
            styles.add(ParagraphStyle(
                'SectionTitle', parent=styles['Heading2'],
                spaceAfter=10, textColor=colors.HexColor('#2563eb'),
            ))

            elements = []

            # Title
            elements.append(Paragraph('CV Analysis Report', styles['Title']))
            elements.append(Spacer(1, 0.5 * cm))
            elements.append(Paragraph(
                f'Document: {analysis.cv_document.original_filename}',
                styles['Normal'],
            ))
            elements.append(Paragraph(
                f'Generated for: {report.user.email}',
                styles['Normal'],
            ))
            elements.append(Paragraph(
                f'Date: {analysis.created_at.strftime("%B %d, %Y")}',
                styles['Normal'],
            ))
            elements.append(Spacer(1, 0.5 * cm))
            elements.append(HRFlowable(width='100%', color=colors.grey))
            elements.append(Spacer(1, 0.5 * cm))

            # Summary
            if analysis.summary:
                elements.append(Paragraph('Summary', styles['SectionTitle']))
                elements.append(Paragraph(analysis.summary, styles['Normal']))
                elements.append(Spacer(1, 0.5 * cm))

            # Section Analyses
            section_analyses = analysis.section_analyses.all()
            if section_analyses:
                elements.append(Paragraph('Section-by-Section Analysis', styles['SectionTitle']))
                for sa in section_analyses:
                    status_label = {'present': 'Present', 'missing': 'Missing', 'weak': 'Weak'}.get(sa.status, sa.status)
                    elements.append(Paragraph(
                        f'<b>{sa.section.title()}</b> [{status_label}]',
                        styles['Normal'],
                    ))
                    if sa.analysis_text:
                        elements.append(Paragraph(sa.analysis_text, styles['Normal']))
                    if sa.suggestions:
                        for suggestion in sa.suggestions:
                            elements.append(Paragraph(f'  - {suggestion}', styles['Normal']))
                    elements.append(Spacer(1, 0.3 * cm))

            # Problems
            problems = analysis.problems.all()
            if problems:
                elements.append(Paragraph('Problems Found', styles['SectionTitle']))
                for p in problems:
                    severity_color = {'critical': '#dc2626', 'warning': '#f59e0b', 'info': '#3b82f6'}.get(
                        p.severity, '#6b7280'
                    )
                    elements.append(Paragraph(
                        f'<font color="{severity_color}">[{p.get_severity_display()}]</font> '
                        f'<b>{p.title}</b>',
                        styles['Normal'],
                    ))
                    elements.append(Paragraph(p.description, styles['Normal']))
                    elements.append(Spacer(1, 0.3 * cm))

            # Recommendations
            recommendations = analysis.recommendations.all()
            if recommendations:
                elements.append(Paragraph('Recommendations', styles['SectionTitle']))
                for r in recommendations:
                    elements.append(Paragraph(
                        f'<b>[{r.get_priority_display()}]</b> {r.title}',
                        styles['Normal'],
                    ))
                    elements.append(Paragraph(r.description, styles['Normal']))
                    if r.suggested_text:
                        elements.append(Paragraph(
                            f'<i>Suggestion: {r.suggested_text}</i>',
                            styles['Normal'],
                        ))
                    elements.append(Spacer(1, 0.3 * cm))

            # Skill Gaps
            skill_gaps = analysis.skill_gaps.all()
            if skill_gaps:
                elements.append(Paragraph('Skill Gaps', styles['SectionTitle']))
                sg_data = [['Skill', 'Current', 'Recommended', 'Importance']]
                for sg in skill_gaps:
                    sg_data.append([
                        sg.skill_name,
                        sg.current_level or '-',
                        sg.recommended_level or '-',
                        sg.importance,
                    ])
                sg_table = Table(sg_data, colWidths=[5 * cm, 3 * cm, 3 * cm, 3 * cm])
                sg_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563eb')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f4ff')]),
                ]))
                elements.append(sg_table)

            # Footer
            elements.append(Spacer(1, 1 * cm))
            elements.append(HRFlowable(width='100%', color=colors.grey))
            elements.append(Paragraph(
                'Generated by CV Analyzer - AI-Powered Resume Analysis',
                ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.grey),
            ))

            doc.build(elements)

            pdf_content = buffer.getvalue()
            buffer.close()

            filename = f'cv_analysis_report_{analysis.id}.pdf'
            report.file.save(filename, ContentFile(pdf_content), save=False)
            report.status = 'done'
            report.error_message = ''
            report.save()

            return report

        except Exception as e:
            logger.error(f"PDF generation failed for report {report_id}: {e}")
            report.status = 'failed'
            report.error_message = str(e)
            report.save(update_fields=['status', 'error_message'])
            return report
