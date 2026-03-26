"""
Management command: set_plan_prices

Bezpośrednio przypisuje Stripe Price ID do każdego planu w bazie danych.

Użycie:
    python manage.py set_plan_prices --basic=price_xxx --premium=price_yyy --enterprise=price_zzz

    # Tylko podgląd aktualnego stanu:
    python manage.py set_plan_prices --list
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Directly assign Stripe Price IDs to plans in the database'

    def add_arguments(self, parser):
        parser.add_argument('--basic',      type=str, help='Stripe Price ID for Basic plan')
        parser.add_argument('--premium',    type=str, help='Stripe Price ID for Premium plan')
        parser.add_argument('--enterprise', type=str, help='Stripe Price ID for Enterprise plan')
        parser.add_argument('--list',       action='store_true', help='Show current price ID mapping')

    def handle(self, *args, **options):
        from billing.models import Plan

        if options['list'] or not any([options['basic'], options['premium'], options['enterprise']]):
            self.stdout.write('\n=== Current Plan → Price ID mapping ===\n')
            for plan in Plan.objects.all().order_by('order'):
                pid = plan.stripe_price_id or '(not set)'
                status = self.style.SUCCESS(pid) if plan.stripe_price_id else self.style.ERROR(pid)
                self.stdout.write(f'  {plan.name:12s}  {status}')
            self.stdout.write('')
            return

        mapping = {
            'basic':      options.get('basic'),
            'premium':    options.get('premium'),
            'enterprise': options.get('enterprise'),
        }

        for slug, price_id in mapping.items():
            if not price_id:
                continue
            plan = Plan.objects.filter(name=slug).first()
            if not plan:
                self.stdout.write(self.style.WARNING(f'  Plan "{slug}" not found in DB — skipping'))
                continue
            plan.stripe_price_id = price_id
            plan.save(update_fields=['stripe_price_id'])
            self.stdout.write(self.style.SUCCESS(f'  {slug:12s} → {price_id}  SAVED'))

        self.stdout.write(self.style.SUCCESS('\nDone.'))
