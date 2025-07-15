#!/usr/bin/env python
"""
Check Railway environment variables and database configuration.
"""

import os
import sys

def check_environment():
    """Check all required environment variables"""
    print("🔍 Checking Railway environment variables...")
    
    # Check DATABASE_URL
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        print(f"✅ DATABASE_URL is set: {database_url[:50]}...")
    else:
        print("❌ DATABASE_URL is not set")
        return False
    
    # Check other required variables
    required_vars = [
        'DJANGO_SECRET_KEY',
        'GEMINI_API_KEY',
        'APIFY_API_KEY',
        'GOOGLE_APPLICATION_CREDENTIALS_JSON',
        'GCS_BUCKET_NAME'
    ]
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var} is set")
        else:
            print(f"⚠️ {var} is not set")
    
    # Check PORT
    port = os.getenv('PORT', '8000')
    print(f"🌐 PORT: {port}")
    
    # Check if we're on Railway
    railway_env = os.getenv('RAILWAY_ENVIRONMENT')
    if railway_env:
        print(f"🚂 Railway environment: {railway_env}")
    else:
        print("🏠 Not running on Railway")
    
    return True

if __name__ == '__main__':
    check_environment() 