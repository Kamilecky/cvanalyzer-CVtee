"""jobs/urls.py - Routing modułu dopasowania do ofert pracy."""

from django.urls import path
from . import views

urlpatterns = [
    path('match/', views.match_input_view, name='job_match_input'),
    path('match/processing/<uuid:match_id>/', views.match_processing_view, name='job_match_processing'),
    path('match/status/<uuid:match_id>/', views.match_status_api, name='job_match_status'),
    path('match/result/<uuid:match_id>/', views.match_result_view, name='job_match_result'),
    path('history/', views.match_history_view, name='job_match_history'),
]
