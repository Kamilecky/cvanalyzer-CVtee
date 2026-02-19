"""Data migration: update PLAN_CHOICES (remove pro, add basic/enterprise) and migrate pro→basic."""

from django.db import migrations, models


def migrate_pro_to_basic(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    updated = User.objects.filter(plan='pro').update(plan='basic')
    if updated:
        print(f'\n  Migrated {updated} user(s) from pro -> basic')


def migrate_basic_to_pro(apps, schema_editor):
    """Reverse: basic -> pro (for rollback)."""
    User = apps.get_model('accounts', 'User')
    User.objects.filter(plan='basic').update(plan='pro')


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='plan',
            field=models.CharField(
                choices=[
                    ('free', 'Free'),
                    ('basic', 'Basic'),
                    ('premium', 'Premium'),
                    ('enterprise', 'Enterprise'),
                ],
                default='free',
                max_length=20,
            ),
        ),
        migrations.RunPython(migrate_pro_to_basic, migrate_basic_to_pro),
    ]
