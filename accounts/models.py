"""
accounts/models.py - Modele danych aplikacji accounts.

Zawiera:
- User: Niestandardowy model użytkownika z email jako polem logowania,
  planem subskrypcyjnym, licznikiem analiz, integracją Stripe.
- EmailVerificationToken: Token UUID do weryfikacji adresu email
  z czasem ważności i flagą jednorazowego użycia.
- GuestSession: Śledzenie sesji gościa (1 darmowa analiza bez logowania).
"""

import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.utils import timezone


class User(AbstractUser):
    """Niestandardowy model użytkownika z rozszerzeniami RaaS.

    Używa email jako pola logowania (USERNAME_FIELD).
    Przechowuje plan subskrypcyjny, zużycie analiz, status weryfikacji email
    oraz ID klienta Stripe do integracji z systemem płatności.
    """

    PLAN_CHOICES = [
        ('free', 'Free'),
        ('pro', 'Pro'),
        ('premium', 'Premium'),
    ]
    ROLE_CHOICES = [
        ('user', 'User'),
        ('admin', 'Admin'),
    ]

    email = models.EmailField(unique=True)
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='free')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')
    analyses_used_this_month = models.PositiveIntegerField(default=0)
    email_verified = models.BooleanField(default=False)
    stripe_customer_id = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        db_table = 'accounts_user'

    def __str__(self):
        return self.email

    def get_plan_limit(self):
        """Zwraca miesięczny limit analiz dla aktualnego planu. None = bez limitu."""
        return settings.PLAN_LIMITS.get(self.plan)

    def can_analyze(self):
        """Sprawdza czy użytkownik może wykonać kolejną analizę."""
        limit = self.get_plan_limit()
        if limit is None:
            return True
        return self.analyses_used_this_month < limit

    def remaining_analyses(self):
        """Zwraca liczbę pozostałych analiz (float('inf') dla planów bez limitu)."""
        limit = self.get_plan_limit()
        if limit is None:
            return float('inf')
        return max(0, limit - self.analyses_used_this_month)

    def use_analysis(self, count=1):
        """Zwiększa licznik użytych analiz."""
        self.analyses_used_this_month += count
        self.save(update_fields=['analyses_used_this_month'])

    def reset_monthly_usage(self):
        """Resetuje miesięczny licznik analiz (wywoływane przez Celery Beat)."""
        self.analyses_used_this_month = 0
        self.save(update_fields=['analyses_used_this_month'])

    def has_feature(self, feature_name):
        """Sprawdza czy plan użytkownika zawiera daną funkcję."""
        plan_features = settings.PLAN_FEATURES.get(self.plan, {})
        return plan_features.get(feature_name, False)


class EmailVerificationToken(models.Model):
    """Token UUID do weryfikacji adresu email.

    Generowany przy rejestracji i ponownym wysyłaniu.
    Każdy token jest jednorazowy (used=True po użyciu) i ma czas ważności
    określony przez EMAIL_VERIFICATION_TOKEN_EXPIRY_HOURS w settings.
    """

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='verification_tokens'
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    used = models.BooleanField(default=False)

    class Meta:
        db_table = 'accounts_email_verification_token'

    def __str__(self):
        return f'Token for {self.user.email} ({"used" if self.used else "active"})'

    def is_expired(self):
        """Sprawdza czy token przekroczył czas ważności."""
        expiry_hours = getattr(settings, 'EMAIL_VERIFICATION_TOKEN_EXPIRY_HOURS', 24)
        expiry_time = self.created_at + timezone.timedelta(hours=expiry_hours)
        return timezone.now() > expiry_time

    def is_valid(self):
        """Sprawdza czy token jest ważny (nieużyty i niewygasły)."""
        return not self.used and not self.is_expired()


class GuestSession(models.Model):
    """Śledzenie sesji gościa dla jednorazowej darmowej analizy.

    Pozwala niezalogowanemu użytkownikowi wykonać 1 analizę.
    Po rejestracji sesja może zostać powiązana z nowym kontem (converted_to_user).
    """

    session_key = models.CharField(max_length=40, unique=True)
    ip_address = models.GenericIPAddressField()
    analysis_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    converted_to_user = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='guest_sessions'
    )

    class Meta:
        db_table = 'accounts_guest_session'

    def __str__(self):
        return f'Guest {self.session_key[:8]}... ({"used" if self.analysis_used else "available"})'
