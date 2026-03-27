"""billing/webhook_handler.py

Production-ready Stripe webhook handler.
Single source of truth for subscription state changes.

Rules:
  - Plan is updated ONLY on invoice.payment_succeeded
  - checkout.session.completed does NOT touch user.plan
  - customer.subscription.updated syncs metadata only
  - customer.subscription.deleted downgrades to free
  - Every event is processed at most once (idempotency via StripeWebhookEvent)
"""

import logging

import stripe
from django.conf import settings
from django.db import transaction

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Price → plan slug map (single source of truth)
# ---------------------------------------------------------------------------

_PRICE_TO_PLAN = {
    'price_1TFXopG1hKAqWyd8acz7fkRX': 'basic',
    'price_1TFXpRG1hKAqWyd8PVsqyYVM': 'premium',
    'price_1TFXpwG1hKAqWyd893ZswyqO': 'enterprise',
}


def _price_to_plan(price_id: str) -> str | None:
    """Map Stripe price_id → internal plan slug. Returns None if unknown."""
    from billing.models import Plan
    slug = _PRICE_TO_PLAN.get(price_id)
    if slug:
        return slug
    plan = Plan.objects.filter(stripe_price_id=price_id).first()
    return plan.name.lower() if plan else None


# ---------------------------------------------------------------------------
# Signature verification
# ---------------------------------------------------------------------------

def verify_and_parse(payload: bytes, sig_header: str) -> stripe.Event | None:
    """
    Verify Stripe webhook signature and return parsed event.
    - payload must be raw bytes (request.body), never parsed JSON
    - sig_header is the Stripe-Signature HTTP header
    Returns None on failure (caller must return HTTP 400).
    """
    # Ensure stripe.api_key is set (required by stripe-python >= 5)
    stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')

    secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', '')
    if not secret:
        logger.error('webhook: STRIPE_WEBHOOK_SECRET not configured in settings')
        return None

    if not sig_header:
        logger.warning('webhook: missing Stripe-Signature header')
        return None

    if not isinstance(payload, bytes):
        logger.error('webhook: payload must be raw bytes — do not parse before verification')
        return None

    try:
        # construct_event verifies signature AND parses JSON internally
        return stripe.Webhook.construct_event(payload, sig_header, secret)
    except stripe.error.SignatureVerificationError as e:
        logger.warning(f'webhook: signature verification failed — {e}')
        return None
    except ValueError as e:
        # Invalid payload (not valid JSON after signature check)
        logger.error(f'webhook: invalid payload — {e}')
        return None
    except Exception as e:
        logger.error(f'webhook: unexpected error — {e}', exc_info=True)
        return None


# ---------------------------------------------------------------------------
# Idempotency guard
# ---------------------------------------------------------------------------

def _already_processed(event_id: str) -> bool:
    from billing.models import StripeWebhookEvent
    return StripeWebhookEvent.objects.filter(event_id=event_id).exists()


def _mark_processed(event_id: str, event_type: str) -> None:
    from billing.models import StripeWebhookEvent
    StripeWebhookEvent.objects.get_or_create(
        event_id=event_id,
        defaults={'event_type': event_type},
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _user_by_customer(customer_id: str):
    from accounts.models import User
    return User.objects.filter(stripe_customer_id=customer_id).first()


def _user_by_subscription(subscription_id: str):
    from billing.models import Subscription
    sub = Subscription.objects.filter(stripe_subscription_id=subscription_id).select_related('user').first()
    return sub.user if sub else None


# ---------------------------------------------------------------------------
# Event handlers
# ---------------------------------------------------------------------------

def _handle_invoice_payment_succeeded(data: dict) -> str:
    """
    ONLY place where user.plan is updated from Stripe events.
    Extracts price_id from invoice lines, maps to plan slug, updates DB.
    """
    from billing.models import Subscription, Plan
    from accounts.models import User

    customer_id = data.get('customer')
    subscription_id = data.get('subscription')

    if not customer_id or not subscription_id:
        return 'skip: no customer or subscription on invoice'

    # Extract price_id from first invoice line
    lines = data.get('lines', {}).get('data', [])
    price_id = lines[0]['price']['id'] if lines and lines[0].get('price') else None
    if not price_id:
        return 'skip: no price_id on invoice lines'

    plan_slug = _price_to_plan(price_id)
    if not plan_slug:
        return f'skip: unknown price_id={price_id!r}'

    user = _user_by_customer(customer_id)
    if not user:
        return f'skip: no user for customer={customer_id}'

    plan_obj = Plan.objects.filter(name=plan_slug).first()

    with transaction.atomic():
        Subscription.objects.update_or_create(
            stripe_subscription_id=subscription_id,
            defaults={
                'user': user,
                'plan': plan_obj,
                'current_price_id': price_id,
                'status': 'active',
                'cancel_at_period_end': False,
            },
        )
        user.plan = plan_slug
        user.save(update_fields=['plan'])

    return f'ok: {user.email} → {plan_slug}'


def _handle_invoice_payment_failed(data: dict) -> str:
    """Mark subscription as past_due. Do not downgrade plan yet."""
    from billing.models import Subscription

    subscription_id = data.get('subscription')
    if not subscription_id:
        return 'skip: no subscription_id'

    updated = Subscription.objects.filter(
        stripe_subscription_id=subscription_id,
    ).update(status='past_due')

    customer_id = data.get('customer')
    user = _user_by_customer(customer_id) if customer_id else None
    email = user.email if user else customer_id

    return f'ok: marked past_due for {email} (rows={updated})'


def _handle_subscription_updated(data: dict) -> str:
    """
    Sync subscription metadata only (status, cancel_at_period_end, current_price_id).
    Does NOT override user.plan — plan is set exclusively by invoice.payment_succeeded.
    """
    from billing.models import Subscription

    sub_id = data.get('id')
    if not sub_id:
        return 'skip: no subscription id'

    items = data.get('items', {}).get('data', [])
    price_id = items[0]['price']['id'] if items and items[0].get('price') else ''
    status = data.get('status', '')
    cancel_at_period_end = data.get('cancel_at_period_end', False)

    updated = Subscription.objects.filter(
        stripe_subscription_id=sub_id,
    ).update(
        status=status,
        cancel_at_period_end=cancel_at_period_end,
        current_price_id=price_id,
    )

    return f'ok: metadata synced for sub={sub_id!r} status={status!r} (rows={updated})'


def _handle_subscription_deleted(data: dict) -> str:
    """Downgrade user to free and mark subscription canceled."""
    from billing.models import Subscription

    sub_id = data.get('id')
    customer_id = data.get('customer')

    if sub_id:
        Subscription.objects.filter(stripe_subscription_id=sub_id).update(status='canceled')

    if customer_id:
        from accounts.models import User
        updated = User.objects.filter(stripe_customer_id=customer_id).update(plan='free')
        return f'ok: {customer_id} → free (rows={updated})'

    return 'skip: no customer_id'


def _handle_checkout_session_completed(data: dict) -> str:
    """
    Link stripe_customer_id to user if not already set.
    Does NOT update user.plan — plan is set by invoice.payment_succeeded.
    """
    from accounts.models import User

    customer_id = data.get('customer')
    client_reference_id = data.get('client_reference_id')
    metadata = data.get('metadata') or {}
    user_id = metadata.get('user_id') or client_reference_id

    if not customer_id:
        return 'skip: no customer_id'

    if user_id:
        updated = User.objects.filter(id=user_id, stripe_customer_id='').update(
            stripe_customer_id=customer_id,
        )
        if updated:
            return f'ok: linked customer={customer_id} to user_id={user_id}'

    # Fallback: link by existing stripe_customer_id match (already linked)
    exists = User.objects.filter(stripe_customer_id=customer_id).exists()
    if exists:
        return f'ok: customer={customer_id} already linked'

    return f'skip: could not link customer={customer_id}'


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

_HANDLERS = {
    'invoice.payment_succeeded':       _handle_invoice_payment_succeeded,
    'invoice.payment_failed':          _handle_invoice_payment_failed,
    'customer.subscription.updated':   _handle_subscription_updated,
    'customer.subscription.deleted':   _handle_subscription_deleted,
    'checkout.session.completed':      _handle_checkout_session_completed,
}


def dispatch(event: stripe.Event) -> None:
    """
    Dispatch a verified Stripe event to the appropriate handler.
    Guards against duplicate processing.
    Logs event_id, event_type, and result.
    """
    event_id = event['id']
    event_type = event['type']

    if _already_processed(event_id):
        logger.info(f'webhook: skip duplicate event_id={event_id!r} type={event_type!r}')
        return

    handler = _HANDLERS.get(event_type)
    if handler is None:
        logger.info(f'webhook: unhandled event_type={event_type!r} event_id={event_id!r}')
        _mark_processed(event_id, event_type)
        return

    try:
        result = handler(event['data']['object'])
        _mark_processed(event_id, event_type)
        logger.info(f'webhook: event_id={event_id!r} type={event_type!r} result={result!r}')
    except Exception as e:
        logger.error(
            f'webhook: error processing event_id={event_id!r} type={event_type!r} — {e}',
            exc_info=True,
        )
        # Do not mark as processed — allow Stripe to retry
        raise
