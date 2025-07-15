#!/usr/bin/env python
import os
import django
import sys
from django.core.management import execute_from_command_line

if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clips_ai_project.settings')
    django.setup()
    
    from django.db import connection
    from django.core.management.color import no_style
    
    try:
        # Test database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        print("✅ Database connection successful")
        
        # Check if tables exist
        table_names = connection.introspection.table_names()
        print(f"📊 Existing tables: {table_names}")
        
        # Check for core app tables
        core_tables = [t for t in table_names if t.startswith('core_')]
        print(f"🔍 Core app tables: {core_tables}")
        
        if 'core_videoprocessing' not in table_names:
            print("❌ core_videoprocessing table missing. Running migrations...")
            try:
                execute_from_command_line(['manage.py', 'migrate', '--noinput'])
                print("✅ Migrations completed successfully")
            except Exception as e:
                print(f"❌ Migration failed: {e}")
                # Try to run migrations for core app specifically
                try:
                    execute_from_command_line(['manage.py', 'migrate', 'core', '--noinput'])
                    print("✅ Core app migrations completed")
                except Exception as e2:
                    print(f"❌ Core app migration failed: {e2}")
                    sys.exit(1)
        else:
            print("✅ All required tables exist")
            
    except Exception as e:
        print(f"❌ Database check failed: {e}")
        sys.exit(1) 