#!/usr/bin/env python
import os
import sys
import django
from django.core.management import execute_from_command_line

def main():
    """
    Run Django management commands for database setup and migrations
    """
    # Add the Django project root to Python path (adjust for being in a subdirectory)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)  # Go up one level from deployment/ to project root
    sys.path.append(project_root)

    # Set the Django settings module to the new modular structure path
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

    # Initialize Django
    django.setup()

    # Run makemigrations to create migrations
    print("Running makemigrations via setup_django.py...")
    execute_from_command_line(['manage.py', 'makemigrations'])

    # Run migrate to apply migrations
    print("Running migrations via setup_django.py...")
    execute_from_command_line(['manage.py', 'migrate'])

    print("Django setup (migrate only) completed successfully!")

if __name__ == "__main__":
    main()