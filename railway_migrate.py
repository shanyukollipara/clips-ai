#!/usr/bin/env python
"""
Migration script for Railway deployment.
This script runs database migrations before starting the server.
"""

import os
import sys
import django
from django.core.management import execute_from_command_line

if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clips_ai_project.settings')
    django.setup()
    
    print("🔄 Running database migrations...")
    execute_from_command_line(['manage.py', 'migrate'])
    print("✅ Database migrations completed!") 