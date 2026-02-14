"""recruitment/urls.py - URL routing modułu rekrutacji."""

from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('', views.dashboard_view, name='recruitment_dashboard'),

    # Positions
    path('positions/', views.position_list_view, name='recruitment_position_list'),
    path('positions/create/', views.position_create_view, name='recruitment_position_create'),
    path('positions/<uuid:position_id>/', views.position_detail_view, name='recruitment_position_detail'),
    path('positions/<uuid:position_id>/edit/', views.position_edit_view, name='recruitment_position_edit'),
    path('positions/<uuid:position_id>/delete/', views.position_delete_view, name='recruitment_position_delete'),

    # Candidates
    path('candidates/', views.candidate_list_view, name='recruitment_candidate_list'),
    path('candidates/upload/', views.candidate_upload_view, name='recruitment_candidate_upload'),
    path('candidates/bulk-upload/', views.bulk_upload_view, name='recruitment_bulk_upload'),
    path('candidates/processing/<int:cv_id>/', views.candidate_processing_view, name='recruitment_candidate_processing'),
    path('candidates/<int:cv_id>/status/', views.candidate_status_api, name='recruitment_candidate_status'),
    path('candidates/<uuid:profile_id>/', views.candidate_detail_view, name='recruitment_candidate_detail'),
    path('candidates/<uuid:profile_id>/match-all/', views.match_all_positions_view, name='recruitment_match_all'),
    path('candidates/<uuid:profile_id>/select-positions/', views.select_positions_view, name='recruitment_select_positions'),
    path('candidates/<uuid:profile_id>/match-selected/', views.match_selected_positions_view, name='recruitment_match_selected'),
    path('candidates/<uuid:profile_id>/selective-status/', views.selective_match_status_api, name='recruitment_selective_match_status'),
    path('candidates/<uuid:profile_id>/auto-match/', views.auto_match_view, name='recruitment_auto_match'),
    path('candidates/<uuid:profile_id>/match-summary/', views.match_summary_view, name='recruitment_match_summary'),

    # Position Ranks
    path('position-ranks/', views.position_ranks_view, name='recruitment_position_ranks'),

    # Fit results
    path('fit/<uuid:fit_id>/', views.fit_result_detail_view, name='recruitment_fit_result'),
    path('fit/<uuid:fit_id>/status/', views.fit_status_api, name='recruitment_fit_status'),
    path('fit/<uuid:fit_id>/questions/', views.generate_questions_view, name='recruitment_generate_questions'),
]
