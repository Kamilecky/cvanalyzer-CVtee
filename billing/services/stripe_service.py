"""billing/services/stripe_service.py - Integracja z Stripe API."""

import logging
import stripe
from django.conf import settings

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY


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
        """Przetwarza webhook z Stripe."""
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except (ValueError, stripe.error.SignatureVerificationError) as e:
            logger.error(f"Stripe webhook error: {e}")
            return None
        return event

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

            Subscription.objects.update_or_create(
                stripe_subscription_id=data['id'],
                defaults={
                    'user': user,
                    'plan': plan,
                    'status': data['status'],
                    'cancel_at_period_end': data.get('cancel_at_period_end', False),
                },
            )

            if plan and data['status'] == 'active':
                user.plan = plan.name.lower()
                user.save(update_fields=['plan'])

        elif event_type == 'customer.subscription.deleted':
            sub_id = data['id']
            Subscription.objects.filter(stripe_subscription_id=sub_id).update(status='canceled')

            customer_id = data['customer']
            User.objects.filter(stripe_customer_id=customer_id).update(plan='free')

    @staticmethod
    def process_invoice_event(event):
        """Przetwarza eventy fakturowe z Stripe."""
        from billing.models import Invoice
        from accounts.models import User

        data = event['data']['object']
        customer_id = data['customer']

        try:
            user = User.objects.get(stripe_customer_id=customer_id)
        except User.DoesNotExist:
            return

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
