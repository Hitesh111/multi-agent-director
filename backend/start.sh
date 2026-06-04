#!/bin/bash

# Start Telegram bot in the background
python manage.py runbot &

# Start Celery worker in the background (using solo pool to save memory)
celery -A config.celery worker -l info --pool=solo &

# Start Celery beat scheduler in the background
celery -A config.celery beat -l info &

# Start Gunicorn web server in the foreground
gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
