"""
accounts/admin.py - Konfiguracja panelu administracyjnego dla modeli accounts.

Rejestruje User, EmailVerificationToken i GuestSession z niestandardowymi
widokami, filtrami i polami wyszukiwania.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, EmailVerificationToken, GuestSession


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Panel admina dla niestandardowego modelu User."""

    list_display = (
        'email', 'username', 'plan', 'role',
        'email_verified', 'analyses_used_this_month',
        'is_active', 'created_at',
    )
    list_filter = ('plan', 'role', 'is_active', 'email_verified')
    search_fields = ('email', 'username')
    ordering = ('-created_at',)

    fieldsets = BaseUserAdmin.fieldsets + (
        ('CV Analyzer', {
            'fields': (
                'plan', 'role', 'analyses_used_this_month',
                'email_verified', 'stripe_customer_id',
            ),
        }),
    )


@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(admin.ModelAdmin):
    """Panel admina dla tokenów weryfikacji email."""

    list_display = ('user', 'token', 'used', 'created_at')
    list_filter = ('used',)
    search_fields = ('user__email',)
    readonly_fields = ('token', 'created_at')


@admin.register(GuestSession)
class GuestSessionAdmin(admin.ModelAdmin):
    """Panel admina dla sesji gościnnych."""

    list_display = ('session_key', 'ip_address', 'analysis_used', 'converted_to_user', 'created_at')
    list_filter = ('analysis_used',)
    search_fields = ('ip_address', 'session_key')
