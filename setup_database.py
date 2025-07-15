#!/usr/bin/env python
"""
Database setup script for Railway PostgreSQL deployment.
This script ensures all database tables are created properly.
"""

import os
import sys
import django
from django.core.management import execute_from_command_line
from django.core.management.base import CommandError

def setup_database():
    """Set up the database with proper error handling"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clips_ai_project.settings')
    
    try:
        django.setup()
        print("🔧 Django setup completed")
        
        from django.db import connection
        from django.core.management import call_command
        
        # Test database connection
        print("🔍 Testing database connection...")
        with connection.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()
            print(f"✅ Connected to PostgreSQL: {version[0]}")
        
        # Show current database info
        print(f"📊 Database: {connection.settings_dict['NAME']}")
        print(f"🏠 Host: {connection.settings_dict['HOST']}")
        print(f"👤 User: {connection.settings_dict['USER']}")
        
        # Check existing tables
        table_names = connection.introspection.table_names()
        print(f"📋 Existing tables: {table_names}")
        
        # Run migrations
        print("🔄 Running migrations...")
        try:
            call_command('migrate', verbosity=2, interactive=False)
            print("✅ Migrations completed successfully")
        except Exception as e:
            print(f"❌ Migration error: {e}")
            print("🔄 Trying to run migrations with --fake-initial...")
            try:
                call_command('migrate', '--fake-initial', verbosity=2, interactive=False)
                print("✅ Migrations completed with --fake-initial")
            except Exception as e2:
                print(f"❌ Second migration attempt failed: {e2}")
                return False
        
        # Verify tables were created
        table_names = connection.introspection.table_names()
        print(f"📋 Tables after migration: {table_names}")
        
        required_tables = ['core_videoprocessing', 'core_viralclip']
        missing_tables = [table for table in required_tables if table not in table_names]
        
        if missing_tables:
            print(f"❌ Missing tables: {missing_tables}")
            
            # Try to create tables manually
            print("🔧 Attempting to create tables manually...")
            try:
                call_command('migrate', 'core', verbosity=2, interactive=False)
                print("✅ Core app migration completed")
                
                # Check again
                table_names = connection.introspection.table_names()
                missing_tables = [table for table in required_tables if table not in table_names]
                
                if missing_tables:
                    print(f"❌ Still missing tables: {missing_tables}")
                    return False
                else:
                    print("✅ All required tables created successfully")
                    
            except Exception as e:
                print(f"❌ Manual table creation failed: {e}")
                return False
        else:
            print("✅ All required tables exist")
        
        # Test table access
        print("🧪 Testing table access...")
        try:
            from core.models import VideoProcessing, ViralClip
            
            # Try to query each table
            video_count = VideoProcessing.objects.count()
            clip_count = ViralClip.objects.count()
            
            print(f"📊 VideoProcessing records: {video_count}")
            print(f"📊 ViralClip records: {clip_count}")
            print("✅ Database tables are accessible")
            
        except Exception as e:
            print(f"❌ Table access test failed: {e}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = setup_database()
    if not success:
        sys.exit(1)
    print("🎉 Database setup completed successfully!") 