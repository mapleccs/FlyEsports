"""
Asynchronous task processing infrastructure.

This module provides the task queue system for FlyEsports backend,
built on Celery for distributed task processing.
"""

from .celery_app import celery_app

__all__ = ['celery_app']