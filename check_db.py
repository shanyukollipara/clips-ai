#!/usr/bin/env python
import os
import django
from django.core.management import execute_from_command_line

if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clips_ai_project.settings')
    django.setup()
    
    from django.db import connection
    from django.core.management.color import no_style
    
    # Check if tables exist
    table_names = connection.introspection.table_names()
    print(f"📊 Existing tables: {table_names}")
    
    if 'core_videoprocessing' not in table_names:
        print("❌ Database tables missing. Running migrations...")
        execute_from_command_line(['manage.py', 'migrate', '--noinput'])
        print("✅ Migrations completed")
    else:
        print("✅ Database tables exist") 