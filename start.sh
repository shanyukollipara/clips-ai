#!/bin/bash
set -e

echo "🚀 Starting Clips AI deployment..."

echo "🔍 Checking environment..."
python check_railway_env.py

echo "🔧 Setting up database..."
python setup_database.py

echo "📦 Collecting static files..."
python manage.py collectstatic --noinput || echo "⚠️ Static files collection failed, continuing..."

echo "🌐 Starting Gunicorn server..."
exec gunicorn clips_ai_project.wsgi:application --bind 0.0.0.0:$PORT 