#!/bin/bash
set -e

# Script to rebuild Docker containers and run migrations
echo "========================================"
echo "SETUP SCRIPT FOR MIGRATIONS"
echo "========================================"

# Get the directory of the script and navigate to project root
cd "$(dirname "$0")/.."
echo "Working directory: $(pwd)"

# Docker compose down and up
echo "1. Restarting Docker containers with rebuild..."
docker compose down
docker compose up -d --build
echo "✅ Docker containers restarted"

# Wait a bit for containers to be fully up
echo "2. Waiting for containers to initialize..."
sleep 10
echo "✅ Continuing with migrations"

# Run migrations FIRST to ensure tables exist, especially on a fresh DB
echo "3. Running initial migrations for all apps..."

# Run makemigrations for all
echo "   - Creating migrations for all apps..."
docker compose exec web python manage.py makemigrations
    
# Run migrate for all
echo "   - Applying all migrations..."
docker compose exec web python manage.py migrate
echo "✅ Initial migrations applied"

# NOW, run the validation script to detect and fix any inconsistencies
echo "4. Validating database migration state..."
echo "   - Checking for migration inconsistencies..."
docker compose exec web python deployment/validate_migrations.py --apply-fixes
echo "✅ Migration validation complete"

# Run app-specific migrations (might be redundant but safe to keep)
echo "5. Running app-specific migrations..."

echo "   - audio_generation migrations..."
docker compose exec web python manage.py makemigrations audio_generation
docker compose exec web python manage.py migrate audio_generation

echo "   - video_generation migrations..."
docker compose exec web python manage.py makemigrations video_generation
docker compose exec web python manage.py migrate video_generation

echo "   - image_generation migrations..."
docker compose exec web python manage.py makemigrations image_generation
docker compose exec web python manage.py migrate image_generation

echo "   - model_training migrations..."
docker compose exec web python manage.py makemigrations model_training
docker compose exec web python manage.py migrate model_training

echo "   - podcast_generator migrations..."
docker compose exec web python manage.py makemigrations podcast_generator
docker compose exec web python manage.py migrate podcast_generator

# Final validation to confirm all is well
echo "6. Final migration validation check..."
docker compose exec web python deployment/validate_migrations.py
echo "✅ Final validation complete"

echo "========================================"
echo "✅ All migrations complete!"
echo "========================================"

# 7. Test the audio generation API
#echo "7. Testing audio_generation API..."
#echo "   To test, run the following command:"
# echo "   python3 scripts/test_audio_generation_api.py --base-url \"https://example.com\" --username \"admin\" --password \"admin1234\""

# 8. Test podcast generation with voice cloning
#echo "8. Testing podcast generation with voice cloning..."
#echo "   To test, run the following command:"
#echo "   python3 scripts/podcast_gen_test.py \\"
#echo "     --topic \"Conversation about AI\" \\"
#echo "     --speaker-count 2 \\"
#echo "     --speaker1-name \"Austin\" \\"
#echo "     --speaker2-name \"Dan\" \\"
#echo "     --speaker1-audio \"https://aicc.nyc3.cdn.digitaloceanspaces.com/avatars/austin/audio/R8_WQTHN3AP.wav\" \\"
#echo "     --speaker2-audio \"https://aicc.nyc3.cdn.digitaloceanspaces.com/avatars/dan/audio/R8_PG11N1PZ.wav\" \\"
#echo "     --check-voice-clone \\"
#echo "     --api-mode \\"
#echo "     --base-url \"https://example.com\" \\"
#echo "     --username \"admin\" \\"
#echo "     --password \"admin1234\""
#echo "========================================"