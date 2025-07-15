from google.cloud import storage
from django.conf import settings
import os
import json
import logging
from typing import Optional, BinaryIO

logger = logging.getLogger(__name__)

class GCSStorage:
    """Google Cloud Storage utility class"""
    
    def __init__(self):
        logger.debug("🔧 Initializing GCS Storage...")
        
        # Try to use environment variable first (for Railway deployment)
        credentials_json = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON')
        logger.debug(f"🔍 GOOGLE_APPLICATION_CREDENTIALS_JSON present: {bool(credentials_json)}")
        
        if credentials_json:
            try:
                logger.debug("🔍 Parsing GCS credentials from environment variable...")
                from google.oauth2 import service_account
                
                # Parse the JSON credentials from environment variable
                credentials_info = json.loads(credentials_json)
                logger.debug(f"✅ Successfully parsed GCS credentials JSON")
                
                # Validate required fields
                required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
                missing_fields = [field for field in required_fields if field not in credentials_info]
                
                if missing_fields:
                    logger.error(f"❌ Missing required fields in GCS credentials: {missing_fields}")
                    raise ValueError(f"Missing required fields in GCS credentials: {missing_fields}")
                
                credentials = service_account.Credentials.from_service_account_info(credentials_info)
                self.client = storage.Client(credentials=credentials)
                logger.info("✅ Using GCS credentials from environment variable")
                
            except json.JSONDecodeError as e:
                logger.error(f"❌ Invalid JSON in GOOGLE_APPLICATION_CREDENTIALS_JSON: {str(e)}")
                raise ValueError(f"Invalid JSON in GOOGLE_APPLICATION_CREDENTIALS_JSON: {str(e)}")
            except Exception as e:
                logger.error(f"❌ Failed to initialize GCS with environment credentials: {str(e)}")
                raise ValueError(f"Failed to initialize GCS with environment credentials: {str(e)}")
        else:
            # Fallback to service account key file (for local development)
            logger.debug("🔍 Trying to use service account key file...")
            key_path = os.path.join(settings.BASE_DIR, 'config', 'gcp-service-account.json')
            
            if not os.path.exists(key_path):
                logger.error(f"❌ GCP service account key file not found at {key_path}")
                logger.error("❌ No GOOGLE_APPLICATION_CREDENTIALS_JSON environment variable set")
                raise ValueError(f"GCP service account key file not found at {key_path} and no GOOGLE_APPLICATION_CREDENTIALS_JSON environment variable set")
                
            try:
                self.client = storage.Client.from_service_account_json(key_path)
                logger.info("✅ Using GCS credentials from service account file")
            except Exception as e:
                logger.error(f"❌ Failed to initialize GCS with service account file: {str(e)}")
                raise ValueError(f"Failed to initialize GCS with service account file: {str(e)}")
            
        try:
            self.bucket_name = 'clips-ai'
            logger.debug(f"🔍 Connecting to GCS bucket: {self.bucket_name}")
            self.bucket = self.client.bucket(self.bucket_name)
            
            # Verify bucket exists and we have access
            if not self.bucket.exists():
                logger.info(f"🔧 Creating new bucket: {self.bucket_name}")
                self.bucket = self.client.create_bucket(self.bucket_name)
                logger.info(f"✅ Created new bucket: {self.bucket_name}")
            else:
                logger.info(f"✅ Connected to existing bucket: {self.bucket_name}")
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize GCS bucket: {str(e)}")
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
            logger.debug(f"📤 Uploading {source_file} to GCS as {destination_blob_name}")
            blob = self.bucket.blob(destination_blob_name)
            
            # Upload the file
            blob.upload_from_filename(source_file)
            
            # Make the blob publicly readable
            blob.make_public()
            
            logger.info(f"✅ File {source_file} uploaded to {destination_blob_name}")
            return blob.public_url
        except Exception as e:
            logger.error(f"❌ Failed to upload {source_file}: {str(e)}")
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
        try:
            logger.debug(f"📤 Uploading data to GCS as {destination_blob_name}")
            blob = self.bucket.blob(destination_blob_name)
            
            # Upload the data
            blob.upload_from_file(file_data)
            
            # Make the blob publicly readable
            blob.make_public()
            
            logger.info(f"✅ Data uploaded to {destination_blob_name}")
            return blob.public_url
        except Exception as e:
            logger.error(f"❌ Failed to upload data to {destination_blob_name}: {str(e)}")
            raise
    
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
            logger.debug(f"📥 Downloading {source_blob_name} from GCS to {destination_file}")
            blob = self.bucket.blob(source_blob_name)
            os.makedirs(os.path.dirname(destination_file), exist_ok=True)
            blob.download_to_filename(destination_file)
            logger.info(f"✅ Blob {source_blob_name} downloaded to {destination_file}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to download {source_blob_name}: {str(e)}")
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
            logger.debug(f"🗑️ Deleting {blob_name} from GCS")
            blob = self.bucket.blob(blob_name)
            blob.delete()
            logger.info(f"🗑️ Deleted blob {blob_name}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to delete {blob_name}: {str(e)}")
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
            logger.debug(f"🔗 Getting public URL for {blob_name}")
            blob = self.bucket.blob(blob_name)
            if blob.exists():
                blob.make_public()
                return blob.public_url
            return None
        except Exception as e:
            logger.error(f"❌ Failed to get public URL for {blob_name}: {str(e)}")
            return None 