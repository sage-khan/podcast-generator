#!/usr/bin/env python
"""
Migration Validation Script for Django Deployments
-------------------------------------------------
This script validates database migrations by checking if all tables referenced in models
exist in the database. If inconsistencies are found, it fixes them by:

1. Identifying missing tables
2. Removing migration records for apps with missing tables 
3. Applying migrations with --fake for existing tables
4. Applying migrations normally for missing tables

Usage:
  python validate_migrations.py [--apply-fixes] [--app app_name]
"""

import argparse
import os
import sys
import django
from django.db import connection, ProgrammingError


def setup_django():
    """Initialize Django."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()


def check_table_exists(table_name):
    """Check if a table exists in the database."""
    with connection.cursor() as cursor:
        cursor.execute(
            'SELECT EXISTS(SELECT FROM information_schema.tables WHERE table_name=%s)',
            [table_name]
        )
        return cursor.fetchone()[0]


def get_model_tables():
    """Get all model tables that should exist."""
    from django.apps import apps
    tables = []
    for app_config in apps.get_app_configs():
        for model in app_config.get_models():
            tables.append(model._meta.db_table)
    return tables


def get_migration_records():
    """Get all migration records from the database."""
    with connection.cursor() as cursor:
        cursor.execute('SELECT app, name FROM django_migrations')
        return cursor.fetchall()


def delete_migration_records(app_name):
    """Delete migration records for an app."""
    with connection.cursor() as cursor:
        cursor.execute('DELETE FROM django_migrations WHERE app=%s', [app_name])
        print(f"✓ Deleted migration records for app: {app_name}")


def apply_migrations(app_name, fake=False):
    """Apply migrations for an app."""
    from django.core.management import call_command
    
    if fake:
        print(f"⚠ Applying migrations with --fake for {app_name}")
        call_command('migrate', app_name, fake=True)
    else:
        print(f"⚡ Applying migrations normally for {app_name}")
        call_command('migrate', app_name)


def validate_app_migrations(app_name, fix=False):
    """
    Validate migrations for a specific app.
    Returns True if all tables for this app exist.
    """
    from django.apps import apps
    
    print(f"\nValidating migrations for app: {app_name}")
    app_config = apps.get_app_config(app_name)
    all_tables_exist = True
    missing_tables = []
    existing_tables = []
    
    for model in app_config.get_models():
        table_name = model._meta.db_table
        table_exists = check_table_exists(table_name)
        
        if table_exists:
            print(f"  ✓ Table exists: {table_name}")
            existing_tables.append(table_name)
        else:
            print(f"  ✗ Table missing: {table_name}")
            missing_tables.append(table_name)
            all_tables_exist = False
    
    if not all_tables_exist and fix:
        print(f"\n⚠ Found missing tables for {app_name}. Fixing...")
        
        # Delete migration records for this app
        delete_migration_records(app_name)
        
        # Apply migrations with --fake if some tables exist
        if existing_tables:
            apply_migrations(app_name, fake=True)
        else:
            apply_migrations(app_name)
        
        # Verify if all tables exist now
        for table_name in missing_tables:
            if check_table_exists(table_name):
                print(f"  ✓ Successfully created table: {table_name}")
            else:
                print(f"  ✗ FAILED to create table: {table_name}")
                all_tables_exist = False
    
    return all_tables_exist


def main():
    parser = argparse.ArgumentParser(description='Validate and fix Django migrations.')
    parser.add_argument('--apply-fixes', action='store_true', help='Apply fixes for migration issues')
    parser.add_argument('--app', help='Validate only a specific app')
    args = parser.parse_args()
    
    setup_django()
    
    if args.app:
        apps_to_validate = [args.app]
    else:
        from django.apps import apps
        apps_to_validate = [
            app_config.label for app_config in apps.get_app_configs()
            if app_config.models_module is not None
        ]
    
    all_valid = True
    for app_name in apps_to_validate:
        try:
            app_valid = validate_app_migrations(app_name, fix=args.apply_fixes)
            if not app_valid:
                all_valid = False
        except Exception as e:
            print(f"Error validating {app_name}: {str(e)}")
            all_valid = False
    
    if all_valid:
        print("\n✓ All migrations are valid!")
        return 0
    else:
        if not args.apply_fixes:
            print("\n⚠ Migration issues found. Run with --apply-fixes to fix automatically.")
        else:
            print("\n⚠ Some migration issues could not be fixed automatically.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
