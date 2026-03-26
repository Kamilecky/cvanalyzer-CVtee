"""billing/views.py - Widoki systemu płatności Stripe."""

import json
import logging
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.utils.translation import gettext as _
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings

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


@login_required
@require_POST
def reset_usage_view(request):
    """Resetuje licznik analiz do 0 — tylko dla superusera."""
    if not request.user.is_superuser:
        return HttpResponse(status=403)
    request.user.analyses_used_this_month = 0
    request.user.save(update_fields=['analyses_used_this_month'])
    messages.success(request, _('Usage counter has been reset to 0.'))
    return redirect('subscription')


@login_required
@require_POST
def change_plan_view(request):
    """Zmienia plan bez pobierania opłat — tylko dla superusera."""
    if not request.user.is_superuser:
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


@login_required
@require_POST
def create_checkout_session_api(request):
    """JSON API: POST {"plan": "basic"} → {"url": "https://checkout.stripe.com/..."}"""
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    plan_slug = body.get('plan', '').lower()
    price_ids = getattr(settings, 'STRIPE_PRICE_IDS', {})
    price_id = price_ids.get(plan_slug)

    if not price_id or price_id.startswith('price_') and '_ID' in price_id:
        # Fallback: look up Plan model by name slug
        plan_obj = Plan.objects.filter(name=plan_slug, is_active=True).first()
        if plan_obj and plan_obj.stripe_price_id:
            price_id = plan_obj.stripe_price_id
        else:
            return JsonResponse({'error': f'Unknown or unconfigured plan: {plan_slug}'}, status=400)

    success_url = request.build_absolute_uri('/billing/success/')
    cancel_url = request.build_absolute_uri('/billing/cancel/')

    try:
        session = StripeService.create_checkout_session(
            request.user, price_id, success_url, cancel_url
        )
        return JsonResponse({'url': session.url})
    except Exception as e:
        logger.error(f"create_checkout_session_api error: {e}")
        return JsonResponse({'error': 'Could not create checkout session'}, status=500)


@csrf_exempt
@require_POST
def stripe_webhook_view(request):
    """Endpoint webhook Stripe — handles all subscription lifecycle events."""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')

    event = StripeService.handle_webhook_event(payload, sig_header)
    if event is None:
        return HttpResponse(status=400)

    event_type = event['type']
    logger.info(f"Stripe webhook received: {event_type} (id={event.get('id', '-')})")

    handlers = {
        'checkout.session.completed':        StripeService.process_checkout_completed,
        'customer.subscription.created':     StripeService.process_subscription_event,
        'customer.subscription.updated':     StripeService.process_subscription_event,
        'customer.subscription.deleted':     StripeService.process_subscription_event,
        'invoice.paid':                      StripeService.process_invoice_event,
        'invoice.payment_failed':            StripeService.process_invoice_event,
        'invoice.finalized':                 StripeService.process_invoice_event,
    }

    handler = handlers.get(event_type)
    if handler:
        try:
            handler(event)
        except Exception as e:
            logger.error(f"Webhook handler error for {event_type}: {e}", exc_info=True)
            # Return 200 so Stripe doesn't retry on logic errors; return 500 only on infra failures
            return HttpResponse(status=200)

    return HttpResponse(status=200)
