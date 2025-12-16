"""
Celery Worker Service package.

This service lives inside the same repo as the backend to reuse the
existing configuration (`app.config.settings`) and task definitions
(`app.tasks.*`). It exposes a tiny FastAPI app for health checks and
starts a Celery worker process using the same REDIS_URL from settings.
"""
