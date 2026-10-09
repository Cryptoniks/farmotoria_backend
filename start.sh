#!/bin/bash
# Apply database migrations
python manage.py migrate --noinput

# Start gunicorn
exec gunicorn farmotoria_backend.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --threads 2 --timeout 120
