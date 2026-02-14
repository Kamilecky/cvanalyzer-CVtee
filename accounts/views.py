"""
accounts/views.py - Widoki (views) aplikacji accounts.

Obsługuje pełny flow użytkownika:
- Rejestracja z weryfikacją email (register_view)
- Strona oczekiwania na weryfikację (registration_pending_view)
- Weryfikacja tokenu email (verify_email_view)
- Ponowne wysyłanie maila weryfikacyjnego (resend_verification_view)
- Logowanie z kontrolą weryfikacji email (login_view)
- Wylogowanie (logout_view)
- Profil użytkownika z edycją danych (profile_view)
- Zmiana hasła (change_password_view)
- Zmiana email (change_email_view)
- Reset hasła przez email (password_reset_view, password_reset_confirm_view)
- Usuwanie konta z potwierdzeniem hasłem (delete_account_view)
"""

import os
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.contrib import messages
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.views.decorators.http import require_POST

from .forms import (
    RegisterForm, LoginForm, ProfileForm,
    ChangePasswordForm, ChangeEmailForm,
)
from .models import User, EmailVerificationToken


# ---------------------------------------------------------------------------
# Helpery
# ---------------------------------------------------------------------------

def _send_verification_email(request, user):
    """Tworzy token weryfikacyjny i wysyła email z linkiem aktywacyjnym."""
    user.verification_tokens.filter(used=False).update(used=True)
    token = EmailVerificationToken.objects.create(user=user)
    verify_url = request.build_absolute_uri(f'/accounts/verify/{token.token}/')

    subject = 'CV Analyzer - Verify your email address'
    html_message = render_to_string('accounts/email/verification_email.html', {
        'user': user,
        'verify_url': verify_url,
        'expiry_hours': getattr(settings, 'EMAIL_VERIFICATION_TOKEN_EXPIRY_HOURS', 24),
    })
    plain_message = strip_tags(html_message)

    send_mail(
        subject, plain_message, settings.DEFAULT_FROM_EMAIL,
        [user.email], html_message=html_message, fail_silently=False,
    )


def _send_password_reset_email(request, user):
    """Wysyła email z linkiem do resetowania hasła."""
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    reset_url = request.build_absolute_uri(f'/accounts/reset/{uid}/{token}/')

    subject = 'CV Analyzer - Reset your password'
    html_message = render_to_string('accounts/email/password_reset_email.html', {
        'user': user,
        'reset_url': reset_url,
    })
    plain_message = strip_tags(html_message)

    send_mail(
        subject, plain_message, settings.DEFAULT_FROM_EMAIL,
        [user.email], html_message=html_message, fail_silently=False,
    )


# ---------------------------------------------------------------------------
# Rejestracja i weryfikacja email
# ---------------------------------------------------------------------------

def register_view(request):
    """Rejestracja nowego użytkownika z weryfikacją email."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.email_verified = False
            user.save()

            try:
                _send_verification_email(request, user)
                messages.success(
                    request,
                    'Account created! A verification link has been sent to your email. '
                    'Please check your inbox and click the link to activate your account.'
                )
            except Exception:
                messages.warning(
                    request,
                    'Account created, but we could not send the verification email. '
                    'Please try resending it from the login page.'
                )

            return redirect('registration_pending')
    else:
        form = RegisterForm()

    return render(request, 'accounts/register.html', {'form': form})


def registration_pending_view(request):
    """Strona informacyjna wyświetlana po rejestracji."""
    return render(request, 'accounts/registration_pending.html')


def verify_email_view(request, token):
    """Weryfikacja adresu email na podstawie tokenu UUID z linku."""
    try:
        verification = EmailVerificationToken.objects.get(token=token)
    except EmailVerificationToken.DoesNotExist:
        return render(request, 'accounts/verification_result.html', {
            'success': False,
            'message': 'Invalid verification link.',
        })

    if verification.used:
        return render(request, 'accounts/verification_result.html', {
            'success': False,
            'message': 'This verification link has already been used. You can log in to your account.',
        })

    if verification.is_expired():
        return render(request, 'accounts/verification_result.html', {
            'success': False,
            'message': 'This verification link has expired. Please request a new one.',
            'show_resend': True,
            'email': verification.user.email,
        })

    verification.used = True
    verification.save(update_fields=['used'])

    user = verification.user
    user.is_active = True
    user.email_verified = True
    user.save(update_fields=['is_active', 'email_verified'])

    return render(request, 'accounts/verification_result.html', {
        'success': True,
        'message': 'Your email has been verified successfully! You can now log in.',
    })


def resend_verification_view(request):
    """Ponowne wysyłanie emaila weryfikacyjnego."""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        if not email:
            messages.error(request, 'Please enter your email address.')
            return render(request, 'accounts/resend_verification.html')

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.success(request, 'If this email is registered, a new verification link has been sent.')
            return render(request, 'accounts/resend_verification.html')

        if user.email_verified and user.is_active:
            messages.info(request, 'This email is already verified. You can log in.')
            return redirect('login')

        try:
            _send_verification_email(request, user)
            messages.success(request, 'A new verification link has been sent to your email.')
        except Exception:
            messages.error(request, 'Could not send the verification email. Please try again later.')

        return render(request, 'accounts/resend_verification.html')

    return render(request, 'accounts/resend_verification.html')


# ---------------------------------------------------------------------------
# Logowanie / Wylogowanie
# ---------------------------------------------------------------------------

def login_view(request):
    """Logowanie użytkownika z kontrolą weryfikacji email."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if not user.email_verified:
                messages.warning(
                    request,
                    'Your email is not verified yet. '
                    '<a href="/accounts/resend-verification/" class="alert-link">'
                    'Resend verification email</a>.'
                )
                return render(request, 'accounts/login.html', {'form': form})
            login(request, user)
            next_url = request.GET.get('next', 'dashboard')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid email or password.')
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    """Wylogowanie użytkownika."""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('login')


# ---------------------------------------------------------------------------
# Profil i zarządzanie kontem
# ---------------------------------------------------------------------------

@login_required
def profile_view(request):
    """Profil użytkownika - edycja danych i podgląd statystyk."""
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated.')
            return redirect('profile')
    else:
        form = ProfileForm(instance=request.user)

    limit = request.user.get_plan_limit()
    context = {
        'form': form,
        'plan_limit': limit if limit else 'Unlimited',
        'analyses_used': request.user.analyses_used_this_month,
        'remaining': request.user.remaining_analyses(),
    }
    return render(request, 'accounts/profile.html', context)


@login_required
def change_password_view(request):
    """Zmiana hasła użytkownika."""
    if request.method == 'POST':
        form = ChangePasswordForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password has been changed successfully.')
            return redirect('profile')
    else:
        form = ChangePasswordForm(request.user)

    return render(request, 'accounts/change_password.html', {'form': form})


@login_required
def change_email_view(request):
    """Zmiana adresu email z potwierdzeniem hasłem i nową weryfikacją."""
    if request.method == 'POST':
        form = ChangeEmailForm(request.POST)
        if form.is_valid():
            new_email = form.cleaned_data['new_email']
            password = form.cleaned_data['password']

            if not request.user.check_password(password):
                messages.error(request, 'Incorrect password.')
                return render(request, 'accounts/change_email.html', {'form': form})

            request.user.email = new_email
            request.user.email_verified = False
            request.user.save(update_fields=['email', 'email_verified'])

            try:
                _send_verification_email(request, request.user)
                messages.success(request, 'Email changed. A verification link has been sent to your new address.')
            except Exception:
                messages.warning(request, 'Email changed, but we could not send the verification email.')

            return redirect('profile')
    else:
        form = ChangeEmailForm()

    return render(request, 'accounts/change_email.html', {'form': form})


# ---------------------------------------------------------------------------
# Reset hasła
# ---------------------------------------------------------------------------

def password_reset_view(request):
    """Żądanie resetu hasła - podanie adresu email."""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        if email:
            try:
                user = User.objects.get(email=email, is_active=True)
                _send_password_reset_email(request, user)
            except (User.DoesNotExist, Exception):
                pass

        messages.success(request, 'If this email is registered, a password reset link has been sent.')
        return redirect('password_reset_done')

    return render(request, 'accounts/password_reset.html')


def password_reset_done_view(request):
    """Strona informacyjna po wysłaniu linku resetowego."""
    return render(request, 'accounts/password_reset_done.html')


def password_reset_confirm_view(request, uidb64, token):
    """Ustawianie nowego hasła z linku resetowego."""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            password1 = request.POST.get('new_password1', '')
            password2 = request.POST.get('new_password2', '')

            if password1 and password1 == password2:
                user.set_password(password1)
                user.save()
                messages.success(request, 'Your password has been reset. You can now log in.')
                return redirect('password_reset_complete')
            else:
                messages.error(request, 'Passwords do not match.')

        return render(request, 'accounts/password_reset_confirm.html', {
            'validlink': True, 'uidb64': uidb64, 'token': token,
        })
    else:
        return render(request, 'accounts/password_reset_confirm.html', {
            'validlink': False,
        })


def password_reset_complete_view(request):
    """Strona potwierdzenia po pomyślnym resecie hasła."""
    return render(request, 'accounts/password_reset_complete.html')


# ---------------------------------------------------------------------------
# Usuwanie konta
# ---------------------------------------------------------------------------

@login_required
@require_POST
def delete_account_view(request):
    """Trwałe usunięcie konta z potwierdzeniem hasłem i czyszczeniem plików."""
    password = request.POST.get('password', '')
    user = request.user

    if not user.check_password(password):
        messages.error(request, 'Incorrect password. Account was not deleted.')
        return redirect('profile')

    # Usuń pliki CV z dysku
    for cv_doc in user.cv_documents.all():
        if cv_doc.file:
            try:
                filepath = cv_doc.file.path
                if os.path.exists(filepath):
                    os.remove(filepath)
            except Exception:
                pass

    # Usuń pliki raportów PDF z dysku
    for report in user.reports.all():
        if report.file:
            try:
                filepath = report.file.path
                if os.path.exists(filepath):
                    os.remove(filepath)
            except Exception:
                pass

    email = user.email
    logout(request)
    user.delete()

    messages.success(request, f'Account "{email}" has been permanently deleted.')
    return redirect('login')
