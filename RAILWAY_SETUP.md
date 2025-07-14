# 🚂 Railway PostgreSQL Setup Guide

## Step 1: Add PostgreSQL to Your Railway Project

1. **Go to your Railway project dashboard**
2. **Click the "+" button** (usually in the top-left or sidebar)
3. **Look for "Database" or "Add Service"** in the menu
4. **Select "PostgreSQL"** from the options
5. **Railway will provision a PostgreSQL database** and show connection details

## Step 2: Get Your Database URL

1. **Click on the new PostgreSQL service** in your project
2. **Go to the "Variables" tab**
3. **Copy the `DATABASE_URL`** (it looks like: `postgresql://user:pass@host:port/db`)

## Step 3: Set Environment Variables

In your Railway project settings, make sure these variables are set:

```
DATABASE_URL=postgresql://user:pass@host:port/db  (auto-set by PostgreSQL service)
DJANGO_SECRET_KEY=your-secret-key-here
APIFY_API_KEY=your-apify-key
GROK_API_KEY=your-grok-key
GOOGLE_APPLICATION_CREDENTIALS_JSON={"type":"service_account",...}
DEBUG=False
```

## Step 4: Deploy

Your app should now:
- ✅ Use PostgreSQL (persistent database)
- ✅ Run migrations automatically
- ✅ Keep data between deploys

## Alternative: If You Can't Add PostgreSQL

If you don't see PostgreSQL option in Railway:

1. **Check your Railway plan** - some features require paid plans
2. **Try the Railway CLI**:
   ```bash
   railway add postgresql
   ```
3. **Or contact Railway support**

## What This Fixes

- ❌ **Before**: SQLite database gets wiped on every deploy
- ✅ **After**: PostgreSQL persists data permanently
- ✅ **Migrations work properly**
- ✅ **No more "no such table" errors** 