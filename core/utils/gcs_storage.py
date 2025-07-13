from google.cloud import storage
from django.conf import settings
import os
from typing import Optional, BinaryIO

class GCSStorage:
    """Google Cloud Storage utility class"""
    
    def __init__(self):
        # Try to use environment variable first (for Railway deployment)
        credentials_json = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON')
        if credentials_json:
            import json
            from google.oauth2 import service_account
            
            # Parse the JSON credentials from environment variable
            credentials_info = json.loads(credentials_json)
            credentials = service_account.Credentials.from_service_account_info(credentials_info)
            self.client = storage.Client(credentials=credentials)
            print("✅ Using GCS credentials from environment variable")
        else:
            # Fallback to service account key file (for local development)
            key_path = os.path.join(settings.BASE_DIR, 'config', 'gcp-service-account.json')
            if not os.path.exists(key_path):
                raise ValueError(f"GCP service account key file not found at {key_path} and no GOOGLE_APPLICATION_CREDENTIALS_JSON environment variable set")
                
            self.client = storage.Client.from_service_account_json(key_path)
            print("✅ Using GCS credentials from service account file")
            
        try:
            self.bucket_name = 'clips-ai'
            self.bucket = self.client.bucket(self.bucket_name)
            
            # Verify bucket exists and we have access
            if not self.bucket.exists():
                self.bucket = self.client.create_bucket(self.bucket_name)
                print(f"✅ Created new bucket: {self.bucket_name}")
            else:
                print(f"✅ Connected to existing bucket: {self.bucket_name}")
                
        except Exception as e:
            raise ValueError(f"Failed to initialize GCS client: {str(e)}")
        
    def upload_file(self, source_file: str, destination_blob_name: str) -> str:
        """
        Upload a file to Google Cloud Storage
        
        Args:
            source_file: Path to the local file to upload
            destination_blob_name: Name to give the file in GCS
            
        Returns:
            Public URL of the uploaded file
        """
        try:
            blob = self.bucket.blob(destination_blob_name)
            
            # Upload the file
            blob.upload_from_filename(source_file)
            
            # Make the blob publicly readable
            blob.make_public()
            
            print(f"✅ File {source_file} uploaded to {destination_blob_name}")
            return blob.public_url
        except Exception as e:
            print(f"❌ Failed to upload {source_file}: {str(e)}")
            raise
    
    def upload_from_memory(self, file_data: BinaryIO, destination_blob_name: str) -> str:
        """
        Upload data from memory to Google Cloud Storage
        
        Args:
            file_data: File-like object containing the data
            destination_blob_name: Name to give the file in GCS
            
        Returns:
            Public URL of the uploaded file
        """
        blob = self.bucket.blob(destination_blob_name)
        
        # Upload the data
        blob.upload_from_file(file_data)
        
        # Make the blob publicly readable
        blob.make_public()
        
        print(f"✅ Data uploaded to {destination_blob_name}")
        return blob.public_url
    
    def download_file(self, source_blob_name: str, destination_file: str) -> bool:
        """
        Download a file from Google Cloud Storage
        
        Args:
            source_blob_name: Name of the file in GCS
            destination_file: Local path where to save the file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            blob = self.bucket.blob(source_blob_name)
            os.makedirs(os.path.dirname(destination_file), exist_ok=True)
            blob.download_to_filename(destination_file)
            print(f"✅ Blob {source_blob_name} downloaded to {destination_file}")
            return True
        except Exception as e:
            print(f"❌ Failed to download {source_blob_name}: {str(e)}")
            return False
    
    def delete_file(self, blob_name: str) -> bool:
        """
        Delete a file from Google Cloud Storage
        
        Args:
            blob_name: Name of the file to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            blob = self.bucket.blob(blob_name)
            blob.delete()
            print(f"🗑️ Deleted blob {blob_name}")
            return True
        except Exception as e:
            print(f"❌ Failed to delete {blob_name}: {str(e)}")
            return False
    
    def get_public_url(self, blob_name: str) -> Optional[str]:
        """
        Get the public URL for a file
        
        Args:
            blob_name: Name of the file in GCS
            
        Returns:
            Public URL if file exists, None otherwise
        """
        try:
            blob = self.bucket.blob(blob_name)
            if blob.exists():
                blob.make_public()
                return blob.public_url
            return None
        except Exception:
            return None 