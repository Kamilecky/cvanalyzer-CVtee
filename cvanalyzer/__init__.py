"""
cvanalyzer/__init__.py - Import aplikacji Celery przy starcie Django.
"""

from .celery import app as celery_app

__all__ = ('celery_app',)
