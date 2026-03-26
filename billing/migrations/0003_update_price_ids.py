"""billing/migrations/0003_update_price_ids.py

Aktualizuje Stripe Price IDs dla planów Basic, Premium i Enterprise.
Uruchamia się automatycznie przy `python manage.py migrate`.
"""

from django.db import migrations


PRICE_IDS = {
    'basic':      'price_1TFJTSG1hKAqWyd8x6CBuvXM',
    'premium':    'price_1TFJT3G1hKAqWyd807KxvltD',
    'enterprise': 'price_1TFJSdG1hKAqWyd8mWE7460C',
}


def update_price_ids(apps, schema_editor):
    Plan = apps.get_model('billing', 'Plan')
    for name, price_id in PRICE_IDS.items():
        Plan.objects.filter(name=name).update(stripe_price_id=price_id)


def revert_price_ids(apps, schema_editor):
    Plan = apps.get_model('billing', 'Plan')
    for name in PRICE_IDS:
        Plan.objects.filter(name=name).update(stripe_price_id='')


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0002_seed_plans'),
    ]

    operations = [
        migrations.RunPython(update_price_ids, reverse_code=revert_price_ids),
    ]
