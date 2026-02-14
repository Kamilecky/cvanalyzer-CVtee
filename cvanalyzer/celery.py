"""
cvanalyzer/celery.py - Konfiguracja aplikacji Celery.

Inicjalizuje Celery z ustawieniami Django i automatycznie
odkrywa zadania (tasks) we wszystkich zainstalowanych aplikacjach.
"""

import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cvanalyzer.settings')

app = Celery('cvanalyzer')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
