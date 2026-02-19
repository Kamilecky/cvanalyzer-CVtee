"""billing/views.py - Widoki systemu płatności Stripe."""

import logging
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.utils.translation import gettext as _
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import Plan
from .services.stripe_service import StripeService

logger = logging.getLogger(__name__)


def pricing_view(request):
    """Strona z cennikiem planów subskrypcyjnych."""
    plans = Plan.objects.filter(is_active=True)
    return render(request, 'billing/pricing.html', {'plans': plans})


@login_required
def checkout_view(request, plan_id):
    """Tworzy sesję Stripe Checkout i przekierowuje."""
    plan = Plan.objects.get(id=plan_id, is_active=True)

    if not plan.stripe_price_id:
        messages.error(request, _('This plan is not available for purchase.'))
        return redirect('pricing')

    success_url = request.build_absolute_uri('/billing/success/')
    cancel_url = request.build_absolute_uri('/billing/cancel/')

    try:
        session = StripeService.create_checkout_session(
            request.user, plan.stripe_price_id, success_url, cancel_url
        )
        return redirect(session.url)
    except Exception as e:
        logger.error(f"Checkout failed: {e}")
        messages.error(request, _('Could not initiate checkout. Please try again.'))
        return redirect('pricing')


@login_required
def checkout_success_view(request):
    """Strona sukcesu po zakupie subskrypcji."""
    return render(request, 'billing/checkout_success.html')


@login_required
def checkout_cancel_view(request):
    """Strona anulowania zakupu."""
    return render(request, 'billing/checkout_cancel.html')


@login_required
def subscription_view(request):
    """Strona zarządzania subskrypcją."""
    sub = getattr(request.user, 'subscription', None)
    return render(request, 'billing/subscription.html', {'subscription': sub})


@login_required
def billing_portal_view(request):
    """Przekierowuje do Stripe Billing Portal."""
    return_url = request.build_absolute_uri('/billing/subscription/')
    try:
        session = StripeService.create_billing_portal_session(request.user, return_url)
        return redirect(session.url)
    except Exception as e:
        logger.error(f"Billing portal failed: {e}")
        messages.error(request, _('Could not open billing portal. Please try again.'))
        return redirect('subscription')


ADMIN_EMAIL = 'kamil3c2@onet.pl'


@login_required
@require_POST
def reset_usage_view(request):
    """Resetuje licznik analiz do 0 — tylko dla admina."""
    if request.user.email != ADMIN_EMAIL:
        return HttpResponse(status=403)
    request.user.analyses_used_this_month = 0
    request.user.save(update_fields=['analyses_used_this_month'])
    messages.success(request, _('Usage counter has been reset to 0.'))
    return redirect('subscription')


@login_required
@require_POST
def change_plan_view(request):
    """Zmienia plan bez pobierania opłat — tylko dla admina."""
    if request.user.email != ADMIN_EMAIL:
        return HttpResponse(status=403)
    new_plan = request.POST.get('plan', '')
    valid_plans = [c[0] for c in request.user.PLAN_CHOICES]
    if new_plan not in valid_plans:
        messages.error(request, _('Invalid plan selected.'))
        return redirect('subscription')
    request.user.plan = new_plan
    request.user.save(update_fields=['plan'])
    messages.success(request, _('Plan changed to %(plan)s.') % {'plan': request.user.get_plan_display()})
    return redirect('subscription')


@csrf_exempt
@require_POST
def stripe_webhook_view(request):
    """Endpoint webhook Stripe."""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')

    event = StripeService.handle_webhook_event(payload, sig_header)
    if event is None:
        return HttpResponse(status=400)

    event_type = event['type']

    if event_type.startswith('customer.subscription.'):
        StripeService.process_subscription_event(event)
    elif event_type.startswith('invoice.'):
        StripeService.process_invoice_event(event)

    return HttpResponse(status=200)
