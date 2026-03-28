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

_HARDCODED_PRICE_MAP = {
    'price_1TFsjVG1hKAqWyd8xI23jwNT': 'basic',
    'price_1TFslDG1hKAqWyd8OaPaX9Tj': 'premium',
    'price_1TFslsG1hKAqWyd8iZgiQzXR': 'enterprise',
}


def _price_id_to_plan_slug(price_id: str) -> str | None:
    """Map a Stripe price_id → plan slug.

    Resolution order:
      1. Hardcoded map (always reliable, no DB/env dependency)
      2. Plan.stripe_price_id in the database (for dynamically added plans)
    Returns None when price_id is unknown.
    """
    from billing.models import Plan

    slug = _HARDCODED_PRICE_MAP.get(price_id)
    if slug:
        return slug

    plan_obj = Plan.objects.filter(stripe_price_id=price_id).first()
    if plan_obj:
        return plan_obj.name.lower()

    logger.error(
        f"_price_id_to_plan_slug: unknown price_id={price_id!r} — "
        "add it to _HARDCODED_PRICE_MAP in stripe_service.py"
    )
    return None



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
    def sync_subscription_for_user(user):
        """
        Pobiera aktywną subskrypcję ze Stripe i aktualizuje user.plan + Subscription.
        Zwraca (plan_slug, changed: bool) lub rzuca wyjątek przy błędzie Stripe.
        """
        from billing.models import Subscription, Plan

        subs = stripe.Subscription.list(
            customer=user.stripe_customer_id,
            status='active',
            limit=1,
            expand=['data.items.data.price'],
        )

        if not subs.data:
            # Brak aktywnej subskrypcji — sprawdź czy jest incomplete (timing issue)
            all_subs = stripe.Subscription.list(
                customer=user.stripe_customer_id,
                limit=1,
                expand=['data.items.data.price'],
            )
            if all_subs.data and all_subs.data[0]['status'] in ('incomplete', 'trialing'):
                # Subskrypcja istnieje ale jeszcze nie active — nie downgrade'uj
                logger.warning(
                    f"sync: {user.email} subscription status={all_subs.data[0]['status']!r} "
                    "— keeping current plan to avoid timing-race downgrade"
                )
                return user.plan, False
            # Naprawdę brak subskrypcji — cofnij do free
            Subscription.objects.filter(user=user).update(status='canceled')
            old = user.plan
            user.plan = 'free'
            user.save(update_fields=['plan'])
            logger.info(f"sync: {user.email} {old} → free (no active sub)")
            return 'free', old != 'free'

        stripe_sub = subs.data[0]
        price_id = stripe_sub['items']['data'][0]['price']['id']

        price_ids = getattr(settings, 'STRIPE_PRICE_IDS', {})
        plan_slug = _price_id_to_plan_slug(price_id)
        if not plan_slug:
            logger.error(
                f"sync_subscription_for_user: cannot map price_id={price_id!r} "
                f"for user {user.email} — keeping current plan={user.plan!r}"
            )
            return user.plan, False

        plan_obj = Plan.objects.filter(name=plan_slug).first()
        Subscription.objects.update_or_create(
            stripe_subscription_id=stripe_sub['id'],
            defaults={
                'user': user,
                'plan': plan_obj,
                'status': stripe_sub['status'],
                'cancel_at_period_end': stripe_sub.get('cancel_at_period_end', False),
            },
        )

        old = user.plan
        user.plan = plan_slug
        user.save(update_fields=['plan'])
        logger.info(f"sync: {user.email} {old} → {plan_slug}")
        return plan_slug, old != plan_slug

    @staticmethod
    def sync_from_checkout_session(user, session_id):
        """
        Używa session_id z success_url (?session_id=cs_...) żeby natychmiast
        zaktualizować plan — odczytuje subskrypcję BEZPOŚREDNIO z sesji,
        nie z listy (list() może zwrócić starą subskrypcję jeśli nowa jest
        jeszcze w statusie incomplete w chwili przekierowania).
        """
        from billing.models import Subscription, Plan

        session = stripe.checkout.Session.retrieve(
            session_id,
            expand=['subscription', 'subscription.items.data.price'],
        )

        # Linkuj stripe_customer_id jeśli nie było
        customer_id = session.get('customer')
        if customer_id and not user.stripe_customer_id:
            user.stripe_customer_id = customer_id
            user.save(update_fields=['stripe_customer_id'])
            logger.info(f"sync_from_checkout: linked customer {customer_id} to {user.email}")

        # Użyj subskrypcji z tej konkretnej sesji
        stripe_sub = session.get('subscription')

        if not stripe_sub:
            logger.error(f"sync_from_checkout: no subscription in session {session_id}")
            return user.plan, False

        # Jeśli Stripe zwrócił samo ID (string) — pobierz obiekt bezpośrednio
        if isinstance(stripe_sub, str):
            logger.info(f"sync_from_checkout: retrieving subscription {stripe_sub} directly")
            stripe_sub = stripe.Subscription.retrieve(
                stripe_sub,
                expand=['items.data.price'],
            )

        try:
            price_id = stripe_sub['items']['data'][0]['price']['id']
        except (KeyError, IndexError, TypeError):
            logger.error(f"sync_from_checkout: cannot extract price_id from session {session_id}")
            return user.plan, False

        plan_slug = _price_id_to_plan_slug(price_id)
        if not plan_slug:
            logger.error(
                f"sync_from_checkout: unknown price_id={price_id!r} for {user.email} "
                "— run 'python manage.py sync_stripe_prices'"
            )
            return user.plan, False

        # Zapisz nowy plan NAJPIERW — przed jakimikolwiek wywołaniami Stripe
        # które mogą rzucić wyjątek i zostawić plan jako free.
        plan_obj = Plan.objects.filter(name=plan_slug).first()
        old = user.plan
        user.plan = plan_slug
        user.save(update_fields=['plan'])
        logger.info(f"sync_from_checkout: {user.email} {old} → {plan_slug} (price={price_id})")

        Subscription.objects.update_or_create(
            stripe_subscription_id=stripe_sub['id'],
            defaults={
                'user': user,
                'plan': plan_obj,
                'status': stripe_sub.get('status', 'active'),
                'cancel_at_period_end': stripe_sub.get('cancel_at_period_end', False),
            },
        )

        # Anuluj stare subskrypcje (dotyczy zmiany planu, nie zakupu od free)
        if user.stripe_customer_id:
            try:
                old_subs = stripe.Subscription.list(
                    customer=user.stripe_customer_id,
                    status='active',
                    limit=10,
                )
                for old_sub in old_subs.data:
                    if old_sub['id'] != stripe_sub['id']:
                        stripe.Subscription.cancel(old_sub['id'])
                        Subscription.objects.filter(stripe_subscription_id=old_sub['id']).update(status='canceled')
                        logger.info(f"sync_from_checkout: canceled old subscription {old_sub['id']} for {user.email}")
            except Exception as e:
                logger.error(f"sync_from_checkout: error canceling old subs for {user.email}: {e}")

        return plan_slug, old != plan_slug

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
                # Aktualizuj plan gdy:
                # 1. To jest bieżąca subskrypcja użytkownika (current_sub), LUB
                # 2. user.plan == 'free' — użytkownik właśnie zmienił plan (stara sub
                #    została skasowana → free), teraz nowa sub nadaje właściwy plan.
                current_sub = getattr(user, 'subscription', None)
                is_current = (current_sub is None or current_sub.stripe_subscription_id == data['id'])
                if is_current or user.plan == 'free':
                    user.plan = plan_slug
                    user.save(update_fields=['plan'])
                    logger.info(f"Subscription updated for {user.email}: plan={plan_slug}, status=active")
                else:
                    logger.info(
                        f"Skipped plan update for {user.email}: webhook for sub {data['id']!r} "
                        f"({plan_slug}), current sub is {current_sub.stripe_subscription_id!r} "
                        f"({getattr(current_sub.plan, 'name', '?')})"
                    )

        elif event_type == 'customer.subscription.deleted':
            sub_id = data['id']
            Subscription.objects.filter(stripe_subscription_id=sub_id).update(status='canceled')

            customer_id = data['customer']
            # Zawsze wróć do free po usunięciu subskrypcji.
            # Jeśli użytkownik kupił nowy plan, webhook customer.subscription.created/updated
            # nada właściwy plan zaraz po tym (reguła: free → nowy plan bez blokad).
            updated = User.objects.filter(stripe_customer_id=customer_id).update(plan='free')
            logger.info(f"Subscription {sub_id!r} deleted → free dla customer {customer_id} ({updated} user(s))")

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
            if not plan_slug:
                logger.error(
                    f"invoice.paid: cannot map price_id={price_id!r} for {user.email} "
                    "— run 'python manage.py sync_stripe_prices'"
                )
                return
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

            # Activate user's plan — only if this invoice belongs to the current subscription.
            # Prevents old Basic invoice webhooks from downgrading after an upgrade to Premium+.
            current_sub = getattr(user, 'subscription', None)
            is_current = (
                current_sub is None
                or subscription_id is None
                or current_sub.stripe_subscription_id == subscription_id
            )
            if is_current:
                previous_plan = user.plan
                user.plan = plan_slug
                user.save(update_fields=['plan'])
                logger.info(f"invoice.paid: {user.email} plan={plan_slug} (was {previous_plan})")
                _send_activation_email(user, plan_slug)
            else:
                logger.info(
                    f"invoice.paid: skipped plan update for {user.email} — "
                    f"invoice for old sub {subscription_id!r} ({plan_slug}), "
                    f"current sub is {current_sub.stripe_subscription_id!r}"
                )

        elif event_type == 'invoice.payment_failed':
            subscription_id = data.get('subscription')
            if subscription_id:
                Subscription.objects.filter(
                    stripe_subscription_id=subscription_id
                ).update(status='past_due')
            logger.warning(f"invoice.payment_failed for {user.email} — subscription marked past_due")
