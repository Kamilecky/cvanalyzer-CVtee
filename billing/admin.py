"""billing/admin.py - Konfiguracja panelu admin dla modeli billing."""

from django.contrib import admin
from .models import Plan, Subscription, UsageRecord, Invoice


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'display_name', 'price_monthly', 'analysis_limit', 'is_active', 'order']
    list_editable = ['order', 'is_active']


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'plan', 'status', 'cancel_at_period_end', 'created_at']
    list_filter = ['status', 'plan']
    search_fields = ['user__email']


@admin.register(UsageRecord)
class UsageRecordAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'created_at']
    list_filter = ['action', 'created_at']
    search_fields = ['user__email']


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['stripe_invoice_id', 'user', 'amount', 'currency', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['user__email', 'stripe_invoice_id']
