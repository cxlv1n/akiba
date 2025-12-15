#!/bin/bash

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Run migrations
echo "Running migrations..."
python manage.py migrate

# Start Gunicorn
echo "Starting Gunicorn..."
exec gunicorn auto_site.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --threads 2 --access-logfile - --error-logfile - --timeout 30 --keep-alive 2