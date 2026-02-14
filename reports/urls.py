"""reports/urls.py - Routing modułu raportów PDF."""

from django.urls import path
from . import views

urlpatterns = [
    path('generate/<uuid:analysis_id>/', views.generate_report_view, name='report_generate'),
    path('status/<uuid:report_id>/', views.report_status_api, name='report_status'),
    path('download/<uuid:report_id>/', views.download_report_view, name='report_download'),
]
