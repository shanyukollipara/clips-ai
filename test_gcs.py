from google.cloud import storage
import os

def test_gcs_connection():
    try:
        # Initialize the client with service account
        key_path = os.path.join('config', 'gcp-service-account.json')
        client = storage.Client.from_service_account_json(key_path)
        
        # Get the bucket
        bucket_name = 'clips-ai'
        bucket = client.bucket(bucket_name)
        
        # Test if bucket exists
        if bucket.exists():
            print(f"✅ Successfully connected to bucket: {bucket_name}")
            
            # Try to create a test file
            blob = bucket.blob('test.txt')
            blob.upload_from_string('Hello from Clips AI!')
            print("✅ Successfully uploaded test file")
            
            # Make it public and get URL
            blob.make_public()
            print(f"✅ Public URL: {blob.public_url}")
            
            # Clean up
            blob.delete()
            print("✅ Successfully cleaned up test file")
        else:
            print(f"❌ Bucket {bucket_name} does not exist")
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    test_gcs_connection() 