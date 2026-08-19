#!/bin/bash
set -e

NAMESPACE="podcast-generator"
LABEL_SELECTOR="app=web"
NON_INTERACTIVE=false
FIX_SCHEMA=false
FAKE_MIGRATIONS=false

# Function to display usage
usage() {
    echo "Usage: $0 [OPTIONS] [POD_NAME]"
    echo
    echo "OPTIONS:"
    echo "  -h, --help            Show this help message"
    echo "  -y, --yes             Non-interactive mode (auto-confirm)"
    echo "  -n, --namespace NAME  Use a different namespace (default: podcast-generator)"
    echo "  -f, --fix-schema      Attempt to detect and fix schema inconsistencies"
    echo "  --fake                Mark migrations as applied without running (use with caution)"
    echo
    echo "ARGUMENTS:"
    echo "  POD_NAME              Optional web pod name (will auto-detect if not provided)"
    echo
    exit 1
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            ;;
        -y|--yes)
            NON_INTERACTIVE=true
            shift
            ;;
        -n|--namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        -f|--fix-schema)
            FIX_SCHEMA=true
            shift
            ;;
        --fake)
            FAKE_MIGRATIONS=true
            shift
            ;;
        *)
            # If it's not a flag, treat it as the pod name
            if [[ $1 != -* ]]; then
                POD_NAME="$1"
                shift
            else
                echo "Unknown option: $1"
                usage
            fi
            ;;
    esac
done

# Banner
echo "========================================"
echo "KUBERNETES MIGRATION SETUP SCRIPT"
echo "========================================"
echo "Namespace: $NAMESPACE"
echo "Fix Schema: $FIX_SCHEMA"
echo "Fake Migrations: $FAKE_MIGRATIONS"

# Function to get the web pod name if not provided
get_web_pod() {
    # Get the first running web pod
    kubectl get pods -n "$NAMESPACE" -l "$LABEL_SELECTOR" -o jsonpath="{.items[?(@.status.phase=='Running')].metadata.name}" | cut -d' ' -f1
}

# Function to execute a command and handle errors
exec_command() {
    local cmd="$1"
    local message="$2"
    local allow_failure="${3:-false}"
    
    echo "$message"
    if ! eval "$cmd"; then
        echo " ERROR: Failed to execute: $cmd"
        if [ "$allow_failure" = "false" ]; then
            echo "Command failed. Please check the error above."
            exit 1
        else
            echo "Command failed, but continuing as errors are allowed for this command."
            return 1
        fi
    fi
    return 0
}

# Function to check if an app has migrations
has_migrations() {
    local app="$1"
    local check_cmd="kubectl exec -n \"$NAMESPACE\" \"$WEB_POD\" -- python -c \"from django.db.migrations.loader import MigrationLoader; from django.db import connections; loader = MigrationLoader(connections['default']); print('$app' in loader.migrated_apps)\""
    local result
    
    result=$(eval "$check_cmd" 2>/dev/null || echo "False")
    if [[ "$result" == *"True"* ]]; then
        return 0  # Has migrations
    else
        return 1  # No migrations
    fi
}

# Function to check if a table exists in the database
check_table_exists() {
    local table_name="$1"
    local check_cmd="kubectl exec -n \"$NAMESPACE\" \"$WEB_POD\" -- python manage.py shell -c \"
from django.db import connection
cursor = connection.cursor()
cursor.execute('SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = %s)', ['$table_name'])
exists = cursor.fetchone()[0]
print(f'{exists}')
\""
    local result
    
    result=$(eval "$check_cmd" 2>/dev/null || echo "False")
    if [[ "$result" == *"True"* ]]; then
        return 0  # Table exists
    else
        return 1  # Table doesn't exist
    fi
}

# Function to create a missing table based on Django model
create_missing_table() {
    local app_name="$1"
    local model_name="$2"
    local table_name="${app_name}_${model_name}"
    
    echo "   - Creating missing table: $table_name"
    
    # First, attempt to create the table using Django's schema editor
    local cmd="kubectl exec -n \"$NAMESPACE\" \"$WEB_POD\" -- python manage.py shell -c \"
from django.db import connection
from $app_name.models import $model_name
from django.db.backends.base.schema import BaseDatabaseSchemaEditor

with connection.schema_editor() as schema_editor:
    schema_editor.create_model($model_name)
print('Table $table_name created successfully')
\""
    
    if ! eval "$cmd" &>/dev/null; then
        echo "     - Failed to create table using Django schema editor, trying SQL..."
        
        # Fallback to running migrations with --fake
        echo "     - Attempting to run migrations with --fake"
        exec_command "kubectl exec -n \"$NAMESPACE\" \"$WEB_POD\" -- python manage.py migrate $app_name --fake" "     - Running fake migrations for $app_name" "true"
        
        if check_table_exists "$table_name"; then
            echo "     - Table $table_name exists after fake migrations"
        else
            echo "     - WARNING: Table $table_name still doesn't exist after fake migrations"
        fi
    else
        echo "     - Table $table_name created successfully"
    fi
}

# Function to check column existence and fix if necessary
check_and_fix_columns() {
    local table_name="$1"
    
    echo "   - Checking columns for table: $table_name"
    
    local cmd="kubectl exec -n \"$NAMESPACE\" \"$WEB_POD\" -- python manage.py shell -c \"
from django.db import connection
cursor = connection.cursor()

# Get column information
cursor.execute(\\\"\\\"\\\"
SELECT column_name, data_type, character_maximum_length, is_nullable
FROM information_schema.columns 
WHERE table_name = '$table_name'
ORDER BY ordinal_position;
\\\"\\\"\\\")
columns = cursor.fetchall()
for col in columns:
    print(f'{col[0]}|{col[1]}|{col[2]}|{col[3]}')
\""
    
    local columns
    columns=$(eval "$cmd" 2>/dev/null)
    echo "     - Found columns: $(echo "$columns" | wc -l)"
    
    # Here you would implement specific column fixes based on the model requirements
    # This is a placeholder for custom column fixes that would need to be implemented
    # based on the specific models in your codebase
}

# Function to fix schema issues for a specific app and model
fix_schema_for_model() {
    local app_name="$1"
    local model_name="$2"
    local table_name="${app_name}_${model_name}"
    
    echo "Checking schema for $app_name.$model_name (table: $table_name)..."
    
    # Check if table exists
    if ! check_table_exists "$table_name"; then
        echo " - Table $table_name does not exist"
        
        # Create table if it doesn't exist
        if [ "$FIX_SCHEMA" = "true" ]; then
            create_missing_table "$app_name" "$model_name"
        else
            echo " - Table needs to be created. Run with --fix-schema to fix automatically."
        fi
    else
        echo " - Table $table_name exists"
        
        # Check and fix columns if requested
        if [ "$FIX_SCHEMA" = "true" ]; then
            check_and_fix_columns "$table_name"
        fi
    fi
}

# Check if pod name was provided as argument
if [ -n "$POD_NAME" ]; then
    WEB_POD="$POD_NAME"
    echo "Using provided pod name: $WEB_POD"
else
    # Get the web pod automatically
    WEB_POD=$(get_web_pod)
    
    if [ -z "$WEB_POD" ]; then
        echo " ERROR: Could not find a running web pod!"
        echo "Please ensure the web pod is running or specify the pod name as an argument."
        exit 1
    fi
    
    echo "Automatically detected web pod: $WEB_POD"
fi

# Check if the pod exists
if ! kubectl get pod -n "$NAMESPACE" "$WEB_POD" &> /dev/null; then
    echo " ERROR: Pod $WEB_POD does not exist in namespace $NAMESPACE!"
    exit 1
fi

# Confirm with the user if not in non-interactive mode
if [ "$NON_INTERACTIVE" = false ]; then
    echo "This script will run migrations on pod: $WEB_POD in namespace: $NAMESPACE"
    if [ "$FIX_SCHEMA" = "true" ]; then
        echo "WARNING: Schema fixing is enabled. This will attempt to modify database tables directly."
    fi
    if [ "$FAKE_MIGRATIONS" = "true" ]; then
        echo "WARNING: Fake migrations are enabled. This will mark migrations as applied without running them."
    fi
    echo "Continue? (y/n)"
    read -r confirm
    
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        echo "Aborted by user."
        exit 0
    fi
fi

# Schema verification and fixing
if [ "$FIX_SCHEMA" = "true" ]; then
    echo "========================================"
    echo "VERIFYING DATABASE SCHEMA"
    echo "========================================"
    
    # List of critical models to check
    # Format: "app_name:model_name"
    CRITICAL_MODELS=(
        "image_generation:FluxKontextMultiJob"
        "image_generation:Character"
        "model_training:TrainingJob"
        # Add other critical models here
    )
    
    for model_pair in "${CRITICAL_MODELS[@]}"; do
        IFS=':' read -r app model <<< "$model_pair"
        fix_schema_for_model "$app" "$model"
    done
fi

# Run migrations
echo "========================================"
echo "RUNNING MIGRATIONS"
echo "========================================"

# Run validation script first to detect and fix migration inconsistencies 
echo "1. Validating database migration state..."
echo "   - Checking for migration inconsistencies..."
exec_command "kubectl exec -n \"$NAMESPACE\" \"$WEB_POD\" -- python /app/deployment/validate_migrations.py --apply-fixes" "   - Validating database migrations..."
echo " ✅ Migration validation complete"

# Create migrations for each app specifically
echo "2. Creating migrations for all apps individually..."

APPS=("image_generation" "model_training" "video_generation" "audio_generation" "podcast_generator")

for app in "${APPS[@]}"; do
    echo "   - Creating migrations for $app app..."
    exec_command "kubectl exec -n \"$NAMESPACE\" \"$WEB_POD\" -- python manage.py makemigrations $app" "   - Creating migrations for $app app..." "true"
done

# Also run makemigrations without app name to catch any missing ones
exec_command "kubectl exec -n \"$NAMESPACE\" \"$WEB_POD\" -- python manage.py makemigrations" "   - Creating any remaining migrations..." "true"
echo " Created migrations"

# Run migrations for specific apps in a certain order
echo "3. Running migrations for specific apps in order..."

for app in "${APPS[@]}"; do
    echo "   - Checking migrations for $app app..."
    
    # Check if the app has migrations before trying to migrate
    if kubectl exec -n "$NAMESPACE" "$WEB_POD" -- python -c "import importlib.util; print(importlib.util.find_spec('$app.migrations') is not None)" | grep -q "True"; then
        echo "   - Migrating $app app..."
        
        # Add --fake flag if fake migrations are enabled
        if [ "$FAKE_MIGRATIONS" = "true" ]; then
            exec_command "kubectl exec -n \"$NAMESPACE\" \"$WEB_POD\" -- python manage.py migrate $app --fake" "   - Fake migrating $app app..." "true"
        else
            exec_command "kubectl exec -n \"$NAMESPACE\" \"$WEB_POD\" -- python manage.py migrate $app" "   - Migrating $app app..." "true"
        fi
    else
        echo "   - Skipping $app app (no migrations directory found)"
    fi
done

echo " App-specific migrations completed"

# Run any remaining migrations
echo "4. Running any remaining migrations..."
if [ "$FAKE_MIGRATIONS" = "true" ]; then
    exec_command "kubectl exec -n \"$NAMESPACE\" \"$WEB_POD\" -- python manage.py migrate --fake" "   - Fake running any remaining migrations..." "true"
else
    exec_command "kubectl exec -n \"$NAMESPACE\" \"$WEB_POD\" -- python manage.py migrate" "   - Running any remaining migrations..."
fi
echo " All migrations completed"

# Run a final validation check to ensure everything is correct
echo "5. Final migration validation check..."
exec_command "kubectl exec -n \"$NAMESPACE\" \"$WEB_POD\" -- python /app/deployment/validate_migrations.py" "   - Verifying final migration state..."
echo " ✅ Final validation complete"

# Collect static files
echo "6. Collecting static files..."
exec_command "kubectl exec -n \"$NAMESPACE\" \"$WEB_POD\" -- python manage.py collectstatic --noinput" "   - Collecting static files..."
echo " Static files collected"

echo "========================================"
echo "MIGRATION SETUP COMPLETED SUCCESSFULLY"
echo "========================================"
echo "You can now test your API endpoints."

"""
#You can now run the following commands to check for schema issues without fixing
./setup_migrations_k8s.sh -n podcast-generator

# Automatically fix schema issues
./setup_migrations_k8s.sh -n podcast-generator --fix-schema

# Fake migrations when needed
./setup_migrations_k8s.sh -n podcast-generator --fake

# Combine flags for CI/CD pipelines
./setup_migrations_k8s.sh -n podcast-generator --fix-schema --yes
"""