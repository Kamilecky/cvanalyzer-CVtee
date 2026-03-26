"""
Management command: sync_stripe_prices

Pobiera wszystkie aktywne ceny ze Stripe i automatycznie przypisuje je do
modelu Plan po nazwie produktu (case-insensitive).

Użycie:
    python manage.py sync_stripe_prices          # podgląd + zapis
    python manage.py sync_stripe_prices --dry-run  # tylko podgląd, bez zapisu
"""

import stripe
from django.core.management.base import BaseCommand
from django.conf import settings

PLAN_NAME_ALIASES = {
    'free':       ['free', 'darmowy', 'starter'],
    'basic':      ['basic', 'podstawowy', 'base'],
    'premium':    ['premium', 'pro'],
    'enterprise': ['enterprise', 'business', 'unlimited', 'korporacyjny'],
}


def _slug_from_name(product_name: str) -> str | None:
    name_lower = product_name.lower()
    for slug, aliases in PLAN_NAME_ALIASES.items():
        if any(alias in name_lower for alias in aliases):
            return slug
    return None


class Command(BaseCommand):
    help = 'Synchronize Stripe Price IDs into Plan model and show env var values'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without saving anything',
        )

    def handle(self, *args, **options):
        from billing.models import Plan

        dry_run = options['dry_run']
        stripe.api_key = settings.STRIPE_SECRET_KEY

        if not stripe.api_key:
            self.stderr.write(self.style.ERROR('STRIPE_SECRET_KEY is not set!'))
            return

        self.stdout.write('Fetching prices from Stripe...\n')

        prices = stripe.Price.list(active=True, expand=['data.product'], limit=100)

        matched = {}   # slug → (price_id, product_name)
        unmatched = []

        for price in prices.auto_paging_iter():
            if price.get('type') != 'recurring':
                continue
            product = price.get('product')
            if not product or isinstance(product, str):
                continue
            product_name = product.get('name', '')
            slug = _slug_from_name(product_name)
            amount = price.get('unit_amount', 0)
            currency = price.get('currency', '').upper()
            interval = price.get('recurring', {}).get('interval', '')
            label = f'{product_name} — {amount / 100:.2f} {currency}/{interval}'

            if slug:
                matched[slug] = (price['id'], label)
                self.stdout.write(f'  MATCH  {slug:12s} ← {price["id"]}  ({label})')
            else:
                unmatched.append((price['id'], label))
                self.stdout.write(f'  SKIP   (no match)  {price["id"]}  ({label})')

        self.stdout.write('')

        if not matched:
            self.stderr.write(self.style.WARNING(
                'No prices matched. Check product names in Stripe dashboard.\n'
                'Expected names containing: free, basic, premium, enterprise (or aliases).'
            ))
            return

        # --- Update Plan model ---
        self.stdout.write('=== Plan.stripe_price_id updates ===')
        for slug, (price_id, label) in matched.items():
            plan = Plan.objects.filter(name=slug).first()
            if not plan:
                self.stdout.write(self.style.WARNING(f'  Plan "{slug}" not found in DB — skipping'))
                continue
            if plan.stripe_price_id == price_id:
                self.stdout.write(f'  {slug:12s} already set to {price_id}')
                continue
            old = plan.stripe_price_id or '(empty)'
            if not dry_run:
                plan.stripe_price_id = price_id
                plan.save(update_fields=['stripe_price_id'])
                self.stdout.write(self.style.SUCCESS(f'  {slug:12s} {old} → {price_id}  SAVED'))
            else:
                self.stdout.write(f'  {slug:12s} {old} → {price_id}  [DRY RUN]')

        # --- Print env vars to set on Railway ---
        self.stdout.write('\n=== Set these environment variables on Railway ===')
        env_map = {'basic': 'STRIPE_PRICE_BASIC', 'premium': 'STRIPE_PRICE_PREMIUM', 'enterprise': 'STRIPE_PRICE_ENTERPRISE'}
        for slug, env_var in env_map.items():
            if slug in matched:
                price_id, _ = matched[slug]
                self.stdout.write(self.style.SUCCESS(f'  {env_var}={price_id}'))
            else:
                self.stdout.write(self.style.WARNING(f'  {env_var}=??? (not found in Stripe)'))

        if dry_run:
            self.stdout.write(self.style.WARNING('\nDry run — nothing was saved.'))
        else:
            self.stdout.write(self.style.SUCCESS('\nDone. Plan.stripe_price_id fields updated.'))
