#!/bin/bash
set -e

echo "🚀 Starting Clips AI deployment..."

echo "🔍 Checking database status..."
python check_db.py

echo "📊 Running database migrations..."
python manage.py migrate --noinput

echo "🔄 Checking if tables were created..."
python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clips_ai_project.settings')
django.setup()
from django.db import connection
tables = connection.introspection.table_names()
print(f'📋 Tables in database: {tables}')
if 'core_videoprocessing' in tables:
    print('✅ core_videoprocessing table exists')
else:
    print('❌ core_videoprocessing table missing - running migrations again')
    import subprocess
    subprocess.run(['python', 'manage.py', 'migrate', '--noinput'])
"

echo "📦 Collecting static files..."
python manage.py collectstatic --noinput || echo "⚠️ Static files collection failed, continuing..."

echo "🌐 Starting Gunicorn server..."
exec gunicorn clips_ai_project.wsgi:application --bind 0.0.0.0:$PORT 