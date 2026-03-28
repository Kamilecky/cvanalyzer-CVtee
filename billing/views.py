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

    success_url = request.build_absolute_uri('/billing/success/') + '?session_id={CHECKOUT_SESSION_ID}'
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
    """Strona sukcesu — natychmiast synchronizuje plan ze Stripe."""
    session_id = request.GET.get('session_id', '')
    plan_slug = None

    if session_id and request.user.is_authenticated:
        try:
            plan_slug, _ = StripeService.sync_from_checkout_session(request.user, session_id)
            logger.info(f"checkout_success: plan synced to {plan_slug} for {request.user.email}")
        except Exception as e:
            logger.error(f"checkout_success sync error: {e}")
            # Webhook będzie fallbackiem — nie blokuj strony sukcesu

    return render(request, 'billing/checkout_success.html', {'synced_plan': plan_slug})


@login_required
def checkout_cancel_view(request):
    """Strona anulowania zakupu."""
    return render(request, 'billing/checkout_cancel.html')


@login_required
def subscription_view(request):
    """Strona zarządzania subskrypcją."""
    from recruitment.models import JobPosition
    sub = getattr(request.user, 'subscription', None)
    if sub and sub.status != 'active':
        sub = None
    active_job_positions = JobPosition.objects.filter(user=request.user, is_active=True).count()
    return render(request, 'billing/subscription.html', {
        'subscription': sub,
        'active_job_positions': active_job_positions,
    })


@login_required
@require_POST
def cancel_subscription_view(request):
    """Anuluje aktywną subskrypcję i wraca do planu free."""
    user = request.user
    if user.stripe_customer_id:
        try:
            import stripe as stripe_lib
            active_subs = stripe_lib.Subscription.list(
                customer=user.stripe_customer_id,
                status='active',
                limit=10,
            )
            for sub in active_subs.data:
                stripe_lib.Subscription.cancel(sub['id'])
            from .models import Subscription
            Subscription.objects.filter(user=user).update(status='canceled')
        except Exception as e:
            logger.error(f"cancel_subscription error for {user.email}: {e}")
            messages.error(request, _('Could not cancel subscription. Please try again.'))
            return redirect('subscription')

    user.plan = 'free'
    user.save(update_fields=['plan'])
    messages.success(request, _('Your subscription has been canceled. You are now on the Free plan.'))
    return redirect('subscription')


@login_required
def billing_portal_view(request):
    """Przekierowuje do Stripe Billing Portal. Po powrocie plan zostaje zsynchronizowany."""
    return_url = request.build_absolute_uri('/billing/portal-return/')
    try:
        session = StripeService.create_billing_portal_session(request.user, return_url)
        return redirect(session.url)
    except Exception as e:
        logger.error(f"Billing portal failed: {e}")
        messages.error(request, _('Could not open billing portal. Please try again.'))
        return redirect('subscription')


@login_required
def portal_return_view(request):
    """Powrót ze Stripe Billing Portal — synchronizuje plan i przekierowuje na subscription."""
    if request.user.stripe_customer_id:
        try:
            plan_slug, changed = StripeService.sync_subscription_for_user(request.user)
            if changed:
                messages.success(
                    request,
                    _('Plan updated to %(plan)s.') % {'plan': plan_slug.title()}
                )
        except Exception as e:
            logger.error(f"portal_return sync error for {request.user.email}: {e}")
    return redirect('subscription')


@login_required
@require_POST
def sync_subscription_view(request):
    """Synchronizuje plan użytkownika bezpośrednio ze Stripe API."""
    user = request.user

    if not user.stripe_customer_id:
        messages.error(request, _('No Stripe customer linked to this account.'))
        return redirect('subscription')

    try:
        plan_slug, changed = StripeService.sync_subscription_for_user(user)
        if plan_slug == 'free':
            messages.warning(request, _('No active Stripe subscription found. Plan reset to Free.'))
        else:
            messages.success(
                request,
                _('Subscription synced! Your plan is now: %(plan)s.') % {'plan': plan_slug.title()}
            )
    except Exception as e:
        logger.error(f"sync_subscription error for {user.email}: {e}")
        messages.error(request, _('Could not sync subscription. Please try again.'))

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


# Stripe Price IDs — hardcoded as single source of truth
STRIPE_PRICE_IDS = {
    'basic':      'price_1TFsjVG1hKAqWyd8xI23jwNT',
    'premium':    'price_1TFslDG1hKAqWyd8OaPaX9Tj',
    'enterprise': 'price_1TFslsG1hKAqWyd8iZgiQzXR',
}


@login_required
@require_POST
def create_checkout_session_api(request):
    """JSON API: POST {"plan": "basic"} → {"url": "https://checkout.stripe.com/..."}"""
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    if request.user.plan != 'free':
        return JsonResponse(
            {'error': 'You already have an active subscription. Cancel your current plan first to purchase a new one.'},
            status=403,
        )

    plan_slug = body.get('plan', '').lower()
    price_id = STRIPE_PRICE_IDS.get(plan_slug)

    if not price_id:
        return JsonResponse({'error': f'Unknown plan: {plan_slug}'}, status=400)

    success_url = request.build_absolute_uri('/billing/success/') + '?session_id={CHECKOUT_SESSION_ID}'
    cancel_url  = request.build_absolute_uri('/billing/cancel/')

    try:
        session = StripeService.create_checkout_session(
            request.user, price_id, success_url, cancel_url
        )
        logger.info(f"Checkout session: user={request.user.email} plan={plan_slug} price={price_id}")
        return JsonResponse({'url': session.url})
    except Exception as e:
        logger.error(f"create_checkout_session_api error for {plan_slug}: {e}")
        return JsonResponse({'error': 'Could not create checkout session'}, status=500)


@csrf_exempt
def stripe_webhook_api_view(request):
    """
    Production Stripe webhook — /api/stripe/webhook/

    - No authentication, no CSRF, no DRF
    - Raw body bytes passed directly to Stripe verification
    - Returns 400 ONLY on signature verification failure
    - Returns 200 for all successfully verified events (even on logic errors)
    """
    if request.method != 'POST':
        return HttpResponse(status=405)

    from django.conf import settings as django_settings
    import stripe as stripe_lib
    from billing.webhook_handler import dispatch

    # --- Step 1: raw body (bytes) — never decode before verification ---
    payload = request.body

    # --- Step 2: Stripe-Signature header ---
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    # --- DEBUG LOGS (temporary) ---
    webhook_secret = getattr(django_settings, 'STRIPE_WEBHOOK_SECRET', None)
    logger.debug(f'[webhook-debug] STRIPE_WEBHOOK_SECRET set: {bool(webhook_secret)}')
    logger.debug(f'[webhook-debug] payload type: {type(payload)} len={len(payload)}')
    logger.debug(f'[webhook-debug] Stripe-Signature: {sig_header!r}')

    if not sig_header:
        logger.warning('webhook: missing HTTP_STRIPE_SIGNATURE header')
        return HttpResponse('Missing Stripe-Signature header', status=400)

    if not webhook_secret:
        logger.error('webhook: STRIPE_WEBHOOK_SECRET not set in settings')
        return HttpResponse('Webhook secret not configured', status=400)

    # --- Step 3: verify signature and parse — NO json.loads before this ---
    stripe_lib.api_key = getattr(django_settings, 'STRIPE_SECRET_KEY', '')
    try:
        event = stripe_lib.Webhook.construct_event(payload, sig_header, webhook_secret)
    except stripe_lib.error.SignatureVerificationError as e:
        logger.warning(f'webhook: signature verification failed — {e}')
        return HttpResponse('Webhook signature verification failed', status=400)
    except ValueError as e:
        logger.error(f'webhook: invalid payload — {e}')
        return HttpResponse('Invalid payload', status=400)

    # --- Step 4: process verified event ---
    logger.info(f'webhook: verified event_id={event["id"]!r} type={event["type"]!r}')

    try:
        dispatch(event)
    except Exception as e:
        logger.error(f'webhook: dispatch error — {e}', exc_info=True)

    return HttpResponse(status=200)


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
