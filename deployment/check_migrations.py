#!/usr/bin/env python
import os
import sys
import django
from django.core.management import call_command
import logging

def main():
    """
    Check if all migrations have been applied properly
    This script can be run both in Docker container and locally
    """
    # Add the Django project root to Python path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)  # Go up one level from deployment/ to project root
    sys.path.append(project_root)

    # Set the Django settings module
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    
    # Initialize Django
    django.setup()
    
    print("Checking migration status...")
    
    print("\nMigration status by app:")
    print("=" * 60)
    
    # Show migration lists for each app
    print("\n📊 image_generation app:")
    call_command('showmigrations', 'image_generation', verbosity=1)
    
    print("\n📊 model_training app:")
    call_command('showmigrations', 'model_training', verbosity=1)
    
    # Show legacy migrations for reference
    print("\n📊 django_character_ai.char_generator app (legacy):")
    try:
        call_command('showmigrations', 'char_generator', verbosity=1)
    except Exception as e:
        print(f"  - App not found in INSTALLED_APPS or other error: {str(e)}")
    
    print("\n✅ Migration check complete")
    print("\nNOTE: To check the migrations correctly in Docker:")
    print("  docker compose exec web python manage.py showmigrations")
    print("\nTo run migrations:")
    print("  docker compose exec web python manage.py migrate")

if __name__ == "__main__":
    main()
