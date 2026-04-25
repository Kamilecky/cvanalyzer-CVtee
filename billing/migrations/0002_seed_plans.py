"""billing/migrations/0002_seed_plans.py

Data migration — tworzy lub aktualizuje 4 plany billingowe z przypisanymi
Stripe Price IDs. Uruchamia się automatycznie przy `python manage.py migrate`.
"""

from django.db import migrations


PLANS = [
    {
        'name':            'free',
        'display_name':    'Free',
        'stripe_price_id': '',
        'price_monthly':   0.00,
        'analysis_limit':  15,
        'order':           0,
        'is_active':       True,
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
        'name':            'basic',
        'display_name':    'Basic',
        'stripe_price_id': 'price_1TFJTSG1hKAqWyd8x6CBuvXM',
        'price_monthly':   79.00,
        'analysis_limit':  100,
        'order':           1,
        'is_active':       True,
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
        'name':            'premium',
        'display_name':    'Premium',
        'stripe_price_id': 'price_1TFJT3G1hKAqWyd807KxvltD',
        'price_monthly':   199.00,
        'analysis_limit':  300,
        'order':           2,
        'is_active':       True,
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
        'name':            'enterprise',
        'display_name':    'Enterprise',
        'stripe_price_id': 'price_1TFJSdG1hKAqWyd8mWE7460C',
        'price_monthly':   999.00,
        'analysis_limit':  None,
        'order':           3,
        'is_active':       True,
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


def seed_plans(apps, schema_editor):
    Plan = apps.get_model('billing', 'Plan')
    for data in PLANS:
        Plan.objects.update_or_create(
            name=data['name'],
            defaults={k: v for k, v in data.items() if k != 'name'},
        )


def unseed_plans(apps, schema_editor):
    Plan = apps.get_model('billing', 'Plan')
    Plan.objects.filter(name__in=['free', 'basic', 'premium', 'enterprise']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_plans, reverse_code=unseed_plans),
    ]
