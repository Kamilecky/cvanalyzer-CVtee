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
    path('positions/<uuid:position_id>/ranking/', views.position_ranking_view, name='recruitment_position_ranking'),
    path('positions/<uuid:position_id>/live-ranking/', views.live_ranking_api, name='recruitment_live_ranking'),
    path('positions/<uuid:position_id>/weights/', views.position_weights_api, name='recruitment_position_weights'),

    # Candidates
    path('candidates/', views.candidate_list_view, name='recruitment_candidate_list'),
    path('candidates/upload/', views.candidate_upload_view, name='recruitment_candidate_upload'),
    path('candidates/bulk-upload/', views.bulk_upload_view, name='recruitment_bulk_upload'),
    path('candidates/bulk-analyze/', views.bulk_analysis_view, name='recruitment_bulk_analyze'),
    path('candidates/bulk-analyze/status/', views.bulk_analysis_status_api, name='recruitment_bulk_analyze_status'),
    path('candidates/processing/<int:cv_id>/', views.candidate_processing_view, name='recruitment_candidate_processing'),
    path('candidates/<int:cv_id>/status/', views.candidate_status_api, name='recruitment_candidate_status'),
    path('candidates/<uuid:profile_id>/', views.candidate_detail_view, name='recruitment_candidate_detail'),
    path('candidates/<uuid:profile_id>/delete/', views.candidate_delete_view, name='recruitment_candidate_delete'),
    path('candidates/<uuid:profile_id>/match-all/', views.match_all_positions_view, name='recruitment_match_all'),
    path('candidates/<uuid:profile_id>/select-positions/', views.select_positions_view, name='recruitment_select_positions'),
    path('candidates/<uuid:profile_id>/match-selected/', views.match_selected_positions_view, name='recruitment_match_selected'),
    path('candidates/<uuid:profile_id>/selective-status/', views.selective_match_status_api, name='recruitment_selective_match_status'),
    path('candidates/<uuid:profile_id>/auto-match/', views.auto_match_view, name='recruitment_auto_match'),
    path('candidates/<uuid:profile_id>/match-summary/', views.match_summary_view, name='recruitment_match_summary'),
    path('candidates/<uuid:profile_id>/intelligence/', views.generate_intelligence_profile_view, name='recruitment_generate_intelligence_profile'),

    # Position Ranks
    path('position-ranks/', views.position_ranks_view, name='recruitment_position_ranks'),

    # Security — Flagged CVs (Prompt Injection)
    path('flagged-cvs/',                              views.flagged_cvs_view,            name='recruitment_flagged_cvs'),
    path('flagged-cvs/dismiss-all/',                  views.flagged_cvs_dismiss_all_view, name='recruitment_flagged_cvs_dismiss_all'),
    path('flagged-cvs/<uuid:analysis_id>/dismiss/',   views.flagged_cv_dismiss_view,     name='recruitment_flagged_cv_dismiss'),
    path('flagged-cvs/<uuid:analysis_id>/restore/',   views.flagged_cv_restore_view,     name='recruitment_flagged_cv_restore'),

    # Fit results
    path('fit/<uuid:fit_id>/', views.fit_result_detail_view, name='recruitment_fit_result'),
    path('fit/<uuid:fit_id>/status/', views.fit_status_api, name='recruitment_fit_status'),
    path('fit/<uuid:fit_id>/questions/', views.generate_questions_view, name='recruitment_generate_questions'),
    path('fit/<uuid:fit_id>/intelligence/', views.generate_intelligence_view, name='recruitment_generate_intelligence'),
]
