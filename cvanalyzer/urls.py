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
from django.shortcuts import redirect

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
    path('', lambda request: redirect('dashboard'), name='home'),
]

# Serwowanie plików media w trybie deweloperskim
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
