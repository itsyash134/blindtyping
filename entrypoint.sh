#!/bin/sh
set -e

echo "Setting DJANGO_SETTINGS_MODULE..."
export DJANGO_SETTINGS_MODULE=typingcomp.settings

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Creating superuser if not exists..."
python manage.py shell << 'EOF'
import os
from django.contrib.auth import get_user_model

User = get_user_model()

username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "TypingHead")
email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "typinghead@gmail.com")
password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "admin@123")

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
    print("Superuser created")
else:
    print("Superuser already exists")
EOF

echo "Starting server..."
exec gunicorn typingcomp.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 120