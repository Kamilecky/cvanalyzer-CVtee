"""billing/models.py - Modele systemu płatności Stripe."""

from django.db import models
from django.conf import settings


class Plan(models.Model):
    """Plan subskrypcyjny z cenami i limitami."""

    name = models.CharField(max_length=50, unique=True)
    display_name = models.CharField(max_length=100)
    stripe_price_id = models.CharField(max_length=255, blank=True, default='')
    price_monthly = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    analysis_limit = models.PositiveIntegerField(null=True, blank=True)
    features = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']
        db_table = 'billing_plan'

    def __str__(self):
        return self.display_name


class Subscription(models.Model):
    """Aktywna subskrypcja użytkownika w Stripe."""

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('past_due', 'Past Due'),
        ('canceled', 'Canceled'),
        ('trialing', 'Trialing'),
        ('incomplete', 'Incomplete'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='subscription',
    )
    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True)
    stripe_subscription_id = models.CharField(max_length=255, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'billing_subscription'

    def __str__(self):
        return f'{self.user.email} - {self.plan} ({self.status})'


class UsageRecord(models.Model):
    """Rekord użycia funkcji (analiza, dopasowanie, raport)."""

    ACTION_CHOICES = [
        ('analysis', 'CV Analysis'),
        ('job_match', 'Job Matching'),
        ('pdf_report', 'PDF Report'),
        ('rewrite', 'AI Rewrite'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='usage_records',
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    analysis = models.ForeignKey(
        'analysis.AnalysisResult', on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        db_table = 'billing_usage_record'

    def __str__(self):
        return f'{self.user.email} - {self.action} @ {self.created_at}'


class Invoice(models.Model):
    """Faktura Stripe."""

    STATUS_CHOICES = [
        ('paid', 'Paid'),
        ('open', 'Open'),
        ('void', 'Void'),
        ('uncollectible', 'Uncollectible'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='invoices',
    )
    stripe_invoice_id = models.CharField(max_length=255, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='usd')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    invoice_url = models.URLField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        db_table = 'billing_invoice'

    def __str__(self):
        return f'Invoice {self.stripe_invoice_id} - {self.amount} {self.currency}'
