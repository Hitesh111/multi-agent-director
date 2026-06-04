#!/bin/bash
set -e

if [ "$1" = "web" ]; then
    python manage.py migrate --noinput
    python manage.py collectstatic --noinput --clear
    exec uvicorn config.asgi:application --host 0.0.0.0 --port 8000 --reload
elif [ "$1" = "worker" ]; then
    exec celery -A config.celery worker --loglevel=info
elif [ "$1" = "beat" ]; then
    exec celery -A config.celery beat --loglevel=info
elif [ "$1" = "flower" ]; then
    exec celery -A config.celery flower --port=5555
else
    exec "$@"
fi
