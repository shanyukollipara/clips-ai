# Railway Deployment Guide for Clips AI

## Prerequisites
1. Railway account
2. GitHub repository with your code
3. Google Cloud Storage bucket and service account

## Environment Variables to Set in Railway

### Required Variables:
```
DJANGO_SECRET_KEY=your-secret-key-here
APIFY_API_KEY=your-apify-api-key
GROK_API_KEY=your-grok-api-key
GOOGLE_APPLICATION_CREDENTIALS_JSON={"type":"service_account","project_id":"clips-ai",...}
GCS_BUCKET_NAME=clips-ai
```

### Optional Variables:
```
DEBUG=False
ALLOWED_HOSTS=your-railway-domain.railway.app
```

## Steps to Deploy:

1. **Connect Repository**: Connect your GitHub repository to Railway
2. **Set Environment Variables**: Add all the required environment variables above
3. **Install FFmpeg**: Railway should automatically install FFmpeg via Nixpacks
4. **Deploy**: Railway will automatically build and deploy

## Getting Google Cloud Credentials JSON:
1. Go to Google Cloud Console
2. Navigate to IAM & Admin > Service Accounts
3. Find your service account
4. Click "Keys" tab
5. Create new key (JSON format)
6. Copy the entire JSON content and paste it as `GOOGLE_APPLICATION_CREDENTIALS_JSON`

## Troubleshooting:
- If FFmpeg is not available, check Railway logs
- If GCS fails, verify the JSON credentials are properly formatted
- If imports fail, check that all dependencies are in requirements.txt

## Test the Deployment:
1. Visit your Railway URL
2. Submit a YouTube URL
3. Check that clips are created and downloadable 