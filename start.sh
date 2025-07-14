#!/bin/bash
set -e

echo "🚀 Starting Clips AI deployment..."

echo "🔍 Checking database status..."
python check_db.py

echo "📊 Running database migrations (if needed)..."
python manage.py migrate --noinput || echo "⚠️ Migrations may have already been applied"

echo "📦 Collecting static files..."
python manage.py collectstatic --noinput || echo "⚠️ Static files collection failed, continuing..."

echo "🌐 Starting Gunicorn server..."
exec gunicorn clips_ai_project.wsgi:application --bind 0.0.0.0:$PORT 