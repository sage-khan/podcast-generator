#!/bin/bash
set -e

# Create necessary media directories
mkdir -p /app/media/character_generation/output \
         /app/media/pose_generation/output \
         /app/media/model_training/output \
         /app/media/model_generation/output \
         /app/static \
         /app/staticfiles

# Wait for database to be ready
if [ -n "$DATABASE_URL" ]; then
    echo "Waiting for database..."
    python -c "
import time
import sys
import os
import psycopg2

retries = 30
while retries > 0:
    try:
        conn = psycopg2.connect(os.environ['DATABASE_URL'])
        conn.close()
        sys.exit(0)
    except psycopg2.OperationalError:
        retries -= 1
        print('Database not ready, waiting...')
        time.sleep(1)

print('Could not connect to database')
sys.exit(1)
"
fi

# Apply Django migrations and collect static files
echo "Applying Django migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput --verbosity 1
# Ensure permissions are correct on static files
echo "Setting permissions on static files..."
find /app/static -type d -exec chmod 755 {} \;
find /app/static -type f -exec chmod 644 {} \;
echo "Static files directory contents:"
ls -la /app/static

# Create superuser if it doesn't exist
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ] && [ -n "$DJANGO_SUPERUSER_EMAIL" ]; then
    echo "Ensuring superuser exists..."
    python manage.py shell <<EOF
from django.contrib.auth import get_user_model
User = get_user_model()
username = "$DJANGO_SUPERUSER_USERNAME"
if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(
        username="$DJANGO_SUPERUSER_USERNAME",
        email="$DJANGO_SUPERUSER_EMAIL",
        password="$DJANGO_SUPERUSER_PASSWORD"
    )
    print("Superuser created")
else:
    print("Superuser already exists")
EOF
fi

# Run setup script if it exists
if [ -f "deployment/setup_django.py" ]; then
    echo "Running setup script from deployment directory..."
    python deployment/setup_django.py
elif [ -f "setup_django.py" ]; then
    echo "Running setup script from root directory..."
    python setup_django.py
fi

# --- ADD DEBUG INFO ---
echo "----------------------------------------"
echo "ENTRYPOINT: Ready to exec Gunicorn"
echo "ENTRYPOINT: Running as user: $(whoami)"
echo "ENTRYPOINT: Working directory: $(pwd)"
echo "ENTRYPOINT: DJANGO_SETTINGS_MODULE is: [$DJANGO_SETTINGS_MODULE]"
echo "ENTRYPOINT: DATABASE_URL is: [$DATABASE_URL]" # Or check DB_HOST etc.
echo "ENTRYPOINT: Static files location:"
echo "ENTRYPOINT: STATIC_ROOT = $(python -c "import os; from django.conf import settings; print(settings.STATIC_ROOT)")"
echo "ENTRYPOINT: Static files directory exists: $(test -d /app/static && echo 'Yes' || echo 'No')"
echo "ENTRYPOINT: Static files count: $(find /app/static -type f | wc -l)"
echo "ENTRYPOINT: Running command: exec $@" # Show the exact command
echo "----------------------------------------"
sleep 3 # Brief pause to ensure logs might flush

# Execute the command passed to the script (Gunicorn command from compose file)
exec "$@"