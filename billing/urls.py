"""billing/urls.py - Routing systemu płatności Stripe."""

from django.urls import path
from . import views

urlpatterns = [
    path('pricing/', views.pricing_view, name='pricing'),
    path('checkout/<int:plan_id>/', views.checkout_view, name='checkout'),
    path('success/', views.checkout_success_view, name='checkout_success'),
    path('cancel/', views.checkout_cancel_view, name='checkout_cancel'),
    path('subscription/', views.subscription_view, name='subscription'),
    path('portal/', views.billing_portal_view, name='billing_portal'),
    path('webhook/', views.stripe_webhook_view, name='stripe_webhook'),
]
