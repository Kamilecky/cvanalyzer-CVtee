"""
cvanalyzer/urls.py - Główna konfiguracja URL projektu.

Routing:
- /admin/          -> Panel administracyjny Django
- /accounts/       -> Autoryzacja, profil, weryfikacja email
- /cv/             -> Upload i zarządzanie dokumentami CV
- /analysis/       -> Dashboard, analiza AI, historia wyników
- /jobs/           -> Dopasowanie do ofert pracy
- /billing/        -> Stripe subskrypcje, plany, płatności
- /reports/        -> Generowanie raportów PDF
- /try/            -> Gościnny upload (analiza bez logowania)
- /                -> Przekierowanie na dashboard
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
from django.shortcuts import redirect
from django.views.generic import TemplateView
from billing import views as billing_views

urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('cv/', include('cv.urls')),
    path('analysis/', include('analysis.urls')),
    path('jobs/', include('jobs.urls')),
    path('billing/', include('billing.urls')),
    path('reports/', include('reports.urls')),
    path('recruitment/', include('recruitment.urls')),
    # Legal pages — publicly accessible, no login required
    path('privacy-policy/', TemplateView.as_view(template_name='legal/privacy_policy.html'), name='privacy_policy'),
    path('terms-of-service/', TemplateView.as_view(template_name='legal/terms_of_service.html'), name='terms_of_service'),
    path('cookies-policy/', TemplateView.as_view(template_name='legal/cookies_policy.html'), name='cookies_policy'),
    # Production Stripe webhook — single source of truth for subscription state
    path('api/stripe/webhook/', billing_views.stripe_webhook_api_view, name='stripe_webhook_api'),
    path('api/create-checkout-session/', billing_views.create_checkout_session_api, name='create_checkout_session_api'),
    path('', lambda request: redirect('dashboard'), name='home'),
]

def _ratelimited_view(request, exception):
    return HttpResponse(
        'Too many attempts. Please wait and try again.',
        status=429,
        content_type='text/plain',
    )

handler429 = _ratelimited_view

# Serwowanie plików media w trybie deweloperskim
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
