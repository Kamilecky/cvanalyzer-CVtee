"""cv/urls.py - Routing aplikacji CV."""

from django.urls import path
from . import views

urlpatterns = [
    path('upload/', views.upload_view, name='cv_upload'),
    path('<int:cv_id>/', views.cv_detail_view, name='cv_detail'),
    path('list/', views.cv_list_view, name='cv_list'),
    path('<int:cv_id>/delete/', views.cv_delete_view, name='cv_delete'),
]
