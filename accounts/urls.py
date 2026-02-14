"""
accounts/urls.py - Routing aplikacji accounts.

Ścieżki:
- /accounts/register/               -> Rejestracja
- /accounts/registration-pending/    -> Oczekiwanie na weryfikację
- /accounts/verify/<uuid>/           -> Weryfikacja tokenu email
- /accounts/resend-verification/     -> Ponowne wysyłanie emaila
- /accounts/login/                   -> Logowanie
- /accounts/logout/                  -> Wylogowanie
- /accounts/profile/                 -> Profil użytkownika
- /accounts/change-password/         -> Zmiana hasła
- /accounts/change-email/            -> Zmiana adresu email
- /accounts/password-reset/          -> Reset hasła (żądanie)
- /accounts/password-reset/done/     -> Reset hasła (potwierdzenie wysłania)
- /accounts/reset/<uidb64>/<token>/  -> Reset hasła (nowe hasło)
- /accounts/reset/done/              -> Reset hasła (ukończony)
- /accounts/account-delete/          -> Usunięcie konta (POST)
"""

from django.urls import path
from . import views

urlpatterns = [
    # Rejestracja i weryfikacja email
    path('register/', views.register_view, name='register'),
    path('registration-pending/', views.registration_pending_view, name='registration_pending'),
    path('verify/<uuid:token>/', views.verify_email_view, name='verify_email'),
    path('resend-verification/', views.resend_verification_view, name='resend_verification'),

    # Logowanie / Wylogowanie
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Profil i zarządzanie kontem
    path('profile/', views.profile_view, name='profile'),
    path('change-password/', views.change_password_view, name='change_password'),
    path('change-email/', views.change_email_view, name='change_email'),
    path('account-delete/', views.delete_account_view, name='account_delete'),

    # Reset hasła
    path('password-reset/', views.password_reset_view, name='password_reset'),
    path('password-reset/done/', views.password_reset_done_view, name='password_reset_done'),
    path('reset/<uidb64>/<token>/', views.password_reset_confirm_view, name='password_reset_confirm'),
    path('reset/done/', views.password_reset_complete_view, name='password_reset_complete'),
]
