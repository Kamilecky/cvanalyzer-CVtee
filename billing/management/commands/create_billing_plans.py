"""
Management command: create_billing_plans

Tworzy lub aktualizuje plany billingowe w bazie danych.

Użycie:
    python manage.py create_billing_plans
"""

from django.core.management.base import BaseCommand


PLANS = [
    {
        'name':           'free',
        'display_name':   'Free',
        'stripe_price_id': '',
        'price_monthly':  0.00,
        'analysis_limit': 15,
        'order':          0,
        'is_active':      True,
        'features': {
            'basic_scoring': True, 'section_detection': True,
            'problem_detection': True, 'recommendations': False,
            'job_matching': True, 'pdf_export': False,
            'ai_rewriting': False, 'skill_gap': False,
            'benchmarking': False, 'career_advisor': False,
            'cv_versioning': False, 'recruitment': True,
            'candidate_ranking': True, 'red_flags': True,
            'interview_questions': False, 'market_benchmark': False,
            'requirement_scoring': False, 'candidate_intelligence': False,
            'priority_processing': False, 'sla_flag': False,
            'prompt_injection_scan': True, 'prompt_injection_defence': True,
            'hidden_prompt_injection_defence': False,
        },
    },
    {
        'name':           'basic',
        'display_name':   'Basic',
        'stripe_price_id': 'price_1TFJTSG1hKAqWyd8x6CBuvXM',
        'price_monthly':  79.00,
        'analysis_limit': 100,
        'order':          1,
        'is_active':      True,
        'features': {
            'basic_scoring': True, 'section_detection': True,
            'problem_detection': True, 'recommendations': True,
            'job_matching': True, 'pdf_export': False,
            'ai_rewriting': False, 'skill_gap': True,
            'benchmarking': False, 'career_advisor': False,
            'cv_versioning': True, 'recruitment': True,
            'candidate_ranking': True, 'red_flags': True,
            'interview_questions': False, 'market_benchmark': False,
            'requirement_scoring': False, 'candidate_intelligence': False,
            'priority_processing': False, 'sla_flag': False,
            'prompt_injection_scan': True, 'prompt_injection_defence': True,
            'hidden_prompt_injection_defence': False,
        },
    },
    {
        'name':           'premium',
        'display_name':   'Premium',
        'stripe_price_id': 'price_1TFJT3G1hKAqWyd807KxvltD',
        'price_monthly':  199.00,
        'analysis_limit': 300,
        'order':          2,
        'is_active':      True,
        'features': {
            'basic_scoring': True, 'section_detection': True,
            'problem_detection': True, 'recommendations': True,
            'job_matching': True, 'pdf_export': True,
            'ai_rewriting': False, 'skill_gap': True,
            'benchmarking': True, 'career_advisor': False,
            'cv_versioning': True, 'recruitment': True,
            'candidate_ranking': True, 'red_flags': True,
            'interview_questions': True, 'market_benchmark': True,
            'requirement_scoring': True, 'candidate_intelligence': True,
            'priority_processing': False, 'sla_flag': False,
            'prompt_injection_scan': True, 'prompt_injection_defence': True,
            'hidden_prompt_injection_defence': True,
        },
    },
    {
        'name':           'enterprise',
        'display_name':   'Enterprise',
        'stripe_price_id': 'price_1TFJSdG1hKAqWyd8mWE7460C',
        'price_monthly':  999.00,
        'analysis_limit': None,
        'order':          3,
        'is_active':      True,
        'features': {
            'basic_scoring': True, 'section_detection': True,
            'problem_detection': True, 'recommendations': True,
            'job_matching': True, 'pdf_export': True,
            'ai_rewriting': False, 'skill_gap': True,
            'benchmarking': True, 'career_advisor': False,
            'cv_versioning': True, 'recruitment': True,
            'candidate_ranking': True, 'red_flags': True,
            'interview_questions': True, 'market_benchmark': True,
            'requirement_scoring': True, 'candidate_intelligence': True,
            'priority_processing': True, 'sla_flag': True,
            'prompt_injection_scan': True, 'prompt_injection_defence': True,
            'hidden_prompt_injection_defence': True,
        },
    },
]


class Command(BaseCommand):
    help = 'Create or update billing plans with Stripe Price IDs'

    def handle(self, *args, **options):
        from billing.models import Plan

        for data in PLANS:
            plan, created = Plan.objects.update_or_create(
                name=data['name'],
                defaults={
                    'display_name':   data['display_name'],
                    'stripe_price_id': data['stripe_price_id'],
                    'price_monthly':  data['price_monthly'],
                    'analysis_limit': data['analysis_limit'],
                    'order':          data['order'],
                    'is_active':      data['is_active'],
                    'features':       data['features'],
                },
            )
            verb = 'Created' if created else 'Updated'
            pid  = data['stripe_price_id'] or '(no price — free plan)'
            self.stdout.write(self.style.SUCCESS(f'  {verb:8s} {plan.name:12s}  {pid}'))

        self.stdout.write(self.style.SUCCESS('\nAll plans ready.'))
