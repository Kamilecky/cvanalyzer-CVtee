"""billing/services/stripe_service.py - Integracja z Stripe API."""

import logging
import threading
import requests as http_requests
import stripe
from django.conf import settings

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _price_id_to_plan_slug(price_id: str) -> str:
    """Map a Stripe price_id → plan slug using STRIPE_PRICE_IDS from settings."""
    price_ids = getattr(settings, 'STRIPE_PRICE_IDS', {})
    for slug, pid in price_ids.items():
        if pid == price_id:
            return slug
    return 'basic'   # safe default



def _send_activation_email(user, plan_name: str):
    """Send subscription activation confirmation via Mailgun HTTP API."""
    from django.template.loader import render_to_string
    from django.utils.html import strip_tags

    api_key = getattr(settings, 'MAILGUN_API_KEY', '')
    api_url = getattr(settings, 'MAILGUN_API_URL', '')
    if not api_key or not api_url:
        logger.warning("Mailgun not configured — skipping activation email")
        return

    def _send():
        try:
            subject = f"CVeeto — Your {plan_name.title()} subscription is active!"
            html_message = render_to_string('accounts/email/subscription_activated_email.html', {
                'user': user,
                'plan_name': plan_name.title(),
            })
            resp = http_requests.post(
                api_url,
                auth=("api", api_key),
                data={
                    "from": settings.DEFAULT_FROM_EMAIL,
                    "to": [user.email],
                    "subject": subject,
                    "text": strip_tags(html_message),
                    "html": html_message,
                },
                timeout=10,
            )
            resp.raise_for_status()
            logger.info(f"Activation email sent to {user.email}: {resp.status_code}")
        except Exception as e:
            logger.error(f"Activation email failed for {user.email}: {e}")

    threading.Thread(target=_send, daemon=True).start()


# ---------------------------------------------------------------------------
# StripeService
# ---------------------------------------------------------------------------

class StripeService:
    """Serwis do obsługi operacji Stripe."""

    @staticmethod
    def get_or_create_customer(user):
        """Pobiera lub tworzy klienta Stripe dla użytkownika."""
        if user.stripe_customer_id:
            try:
                return stripe.Customer.retrieve(user.stripe_customer_id)
            except stripe.error.InvalidRequestError:
                pass

        customer = stripe.Customer.create(
            email=user.email,
            name=user.username,
            metadata={'user_id': str(user.id)},
        )
        user.stripe_customer_id = customer.id
        user.save(update_fields=['stripe_customer_id'])
        return customer

    @staticmethod
    def create_checkout_session(user, price_id, success_url, cancel_url):
        """Tworzy sesję Stripe Checkout do zakupu subskrypcji."""
        customer = StripeService.get_or_create_customer(user)

        session = stripe.checkout.Session.create(
            customer=customer.id,
            payment_method_types=['card'],
            line_items=[{'price': price_id, 'quantity': 1}],
            mode='subscription',
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={'user_id': str(user.id)},
        )
        return session

    @staticmethod
    def create_billing_portal_session(user, return_url):
        """Tworzy sesję Stripe Billing Portal do zarządzania subskrypcją."""
        customer = StripeService.get_or_create_customer(user)
        session = stripe.billing_portal.Session.create(
            customer=customer.id,
            return_url=return_url,
        )
        return session

    @staticmethod
    def handle_webhook_event(payload, sig_header):
        """Weryfikuje podpis i parsuje webhook z Stripe."""
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except (ValueError, stripe.error.SignatureVerificationError) as e:
            logger.error(f"Stripe webhook signature error: {e}")
            return None
        return event

    # ------------------------------------------------------------------
    # checkout.session.completed
    # ------------------------------------------------------------------

    @staticmethod
    def process_checkout_completed(event):
        """Handles checkout.session.completed — links customer_id to user."""
        from accounts.models import User

        data = event['data']['object']
        customer_id = data.get('customer')
        customer_email = data.get('customer_details', {}).get('email') or data.get('customer_email')
        subscription_id = data.get('subscription')
        user_id = data.get('metadata', {}).get('user_id')

        # Resolve user: prefer metadata user_id, fall back to email lookup
        user = None
        if user_id:
            user = User.objects.filter(id=user_id).first()
        if not user and customer_email:
            user = User.objects.filter(email=customer_email).first()

        if not user:
            logger.warning(f"checkout.session.completed: no user found (customer={customer_id})")
            return

        # Attach Stripe customer ID if not yet set
        if customer_id and not user.stripe_customer_id:
            user.stripe_customer_id = customer_id
            user.save(update_fields=['stripe_customer_id'])
            logger.info(f"Attached Stripe customer {customer_id} to user {user.email}")

        # Store subscription ID on Subscription record (will be fully populated by invoice.paid)
        if subscription_id:
            from billing.models import Subscription
            Subscription.objects.update_or_create(
                stripe_subscription_id=subscription_id,
                defaults={'user': user, 'status': 'incomplete'},
            )

        logger.info(f"checkout.session.completed processed for {user.email}")

    # ------------------------------------------------------------------
    # customer.subscription.*
    # ------------------------------------------------------------------

    @staticmethod
    def process_subscription_event(event):
        """Przetwarza eventy subskrypcyjne z Stripe."""
        from billing.models import Subscription, Plan
        from accounts.models import User

        data = event['data']['object']
        event_type = event['type']

        if event_type in ('customer.subscription.created', 'customer.subscription.updated'):
            customer_id = data['customer']
            try:
                user = User.objects.get(stripe_customer_id=customer_id)
            except User.DoesNotExist:
                logger.warning(f"No user found for Stripe customer {customer_id}")
                return

            price_id = data['items']['data'][0]['price']['id'] if data['items']['data'] else ''
            plan = Plan.objects.filter(stripe_price_id=price_id).first()

            sub, created = Subscription.objects.update_or_create(
                stripe_subscription_id=data['id'],
                defaults={
                    'user': user,
                    'plan': plan,
                    'status': data['status'],
                    'cancel_at_period_end': data.get('cancel_at_period_end', False),
                },
            )

            if plan and data['status'] == 'active':
                plan_slug = plan.name.lower()
                user.plan = plan_slug
                user.save(update_fields=['plan'])
                logger.info(f"Subscription updated for {user.email}: plan={plan_slug}, status=active")

        elif event_type == 'customer.subscription.deleted':
            sub_id = data['id']
            Subscription.objects.filter(stripe_subscription_id=sub_id).update(status='canceled')

            customer_id = data['customer']
            updated = User.objects.filter(stripe_customer_id=customer_id).update(plan='free')
            logger.info(f"Subscription canceled for customer {customer_id} ({updated} user(s) → free)")

    # ------------------------------------------------------------------
    # invoice.*
    # ------------------------------------------------------------------

    @staticmethod
    def process_invoice_event(event):
        """Przetwarza eventy fakturowe z Stripe."""
        from billing.models import Invoice, Subscription, Plan
        from accounts.models import User

        data = event['data']['object']
        event_type = event['type']
        customer_id = data.get('customer')

        try:
            user = User.objects.get(stripe_customer_id=customer_id)
        except User.DoesNotExist:
            logger.warning(f"invoice event: no user for customer {customer_id}")
            return

        # Persist invoice record
        Invoice.objects.update_or_create(
            stripe_invoice_id=data['id'],
            defaults={
                'user': user,
                'amount': (data.get('amount_paid', 0) or 0) / 100,
                'currency': data.get('currency', 'usd'),
                'status': data.get('status', 'open'),
                'invoice_url': data.get('hosted_invoice_url', ''),
            },
        )

        if event_type == 'invoice.paid':
            # Extract price_id from subscription line items
            subscription_id = data.get('subscription')
            price_id = ''
            for line in data.get('lines', {}).get('data', []):
                price_id = line.get('price', {}).get('id', '')
                if price_id:
                    break

            plan_slug = _price_id_to_plan_slug(price_id)
            plan = Plan.objects.filter(name=plan_slug).first()

            # Update or create Subscription record
            if subscription_id:
                Subscription.objects.update_or_create(
                    stripe_subscription_id=subscription_id,
                    defaults={
                        'user': user,
                        'plan': plan,
                        'status': 'active',
                    },
                )

            # Activate user's plan
            previous_plan = user.plan
            user.plan = plan_slug
            user.save(update_fields=['plan'])
            logger.info(f"invoice.paid: {user.email} plan={plan_slug} (was {previous_plan})")

            # Post-payment side effects (fire-and-forget)
            _send_activation_email(user, plan_slug)

        elif event_type == 'invoice.payment_failed':
            subscription_id = data.get('subscription')
            if subscription_id:
                Subscription.objects.filter(
                    stripe_subscription_id=subscription_id
                ).update(status='past_due')
            logger.warning(f"invoice.payment_failed for {user.email} — subscription marked past_due")
