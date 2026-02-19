"""analysis/urls.py - Routing aplikacji analizy AI."""

from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('start/<int:cv_id>/', views.start_analysis_view, name='start_analysis'),
    path('processing/<uuid:analysis_id>/', views.processing_view, name='analysis_processing'),
    path('status/<uuid:analysis_id>/', views.analysis_status_api, name='analysis_status'),
    path('result/<uuid:analysis_id>/', views.result_view, name='analysis_result'),
    path('history/', views.history_view, name='analysis_history'),
    path('delete/<uuid:analysis_id>/', views.analysis_delete_view, name='analysis_delete'),
    path('rewrite/<uuid:analysis_id>/', views.rewrite_section_view, name='analysis_rewrite'),
]
