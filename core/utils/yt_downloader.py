import yt_dlp
import os
from django.conf import settings
from typing import Dict, Optional
from .gcs_storage import GCSStorage

class YouTubeDownloader:
    """Utility for downloading YouTube videos using yt-dlp"""
    
    def __init__(self):
        self.media_root = getattr(settings, 'MEDIA_ROOT', 'media')
        self.downloads_dir = os.path.join(self.media_root, 'downloads')
        os.makedirs(self.downloads_dir, exist_ok=True)
        self.gcs = GCSStorage()
    
    def download_video(self, youtube_url: str, output_path: Optional[str] = None) -> str:
        """
        Download a YouTube video and upload to GCS
        
        Args:
            youtube_url: YouTube video URL
            output_path: Optional custom output path
            
        Returns:
            GCS URL of the uploaded video
        """
        if not output_path:
            # Get video info first to use title in filename
            info = self.get_video_info(youtube_url)
            video_id = youtube_url.split('v=')[-1]
            safe_title = ''.join(c for c in info.get('title', video_id) if c.isalnum() or c in ' -_')[:50]
            filename = f"{safe_title}_{video_id}.mp4"
            output_path = os.path.join(self.downloads_dir, filename)
        
        # Configure yt-dlp options
        ydl_opts = {
            'format': 'best[height<=720]',  # Download best quality up to 720p
            'outtmpl': output_path,
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'merge_output_format': 'mp4',
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4'
            }]
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                print(f"📥 Downloading video: {youtube_url}")
                # Download the video
                ydl.download([youtube_url])
                print(f"✅ Download completed: {output_path}")
                
                # Verify the file was downloaded
                if os.path.exists(output_path):
                    # Upload to GCS
                    gcs_path = f"downloads/{os.path.basename(output_path)}"
                    gcs_url = self.gcs.upload_file(output_path, gcs_path)
                    
                    # Clean up local file
                    os.remove(output_path)
                    print(f"🧹 Cleaned up local file: {output_path}")
                    
                    return gcs_url
                else:
                    raise Exception("Video download completed but file not found")
                    
        except Exception as e:
            # Clean up partial download if it exists
            if os.path.exists(output_path):
                os.remove(output_path)
            raise Exception(f"Failed to download video: {str(e)}")
    
    def get_video_info(self, youtube_url: str) -> Dict:
        """
        Get video information without downloading
        
        Args:
            youtube_url: YouTube video URL
            
        Returns:
            Dictionary containing video metadata
        """
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(youtube_url, download=False)
                
                if info is None:
                    raise Exception("Failed to extract video information")
                
                return {
                    'title': info.get('title'),
                    'duration': info.get('duration'),
                    'uploader': info.get('uploader'),
                    'view_count': info.get('view_count'),
                    'like_count': info.get('like_count'),
                    'description': info.get('description'),
                    'thumbnail': info.get('thumbnail'),
                    'webpage_url': info.get('webpage_url'),
                }
                
        except Exception as e:
            raise Exception(f"Failed to get video info: {str(e)}")
    
    def cleanup_file(self, file_path: str) -> bool:
        """
        Clean up a downloaded video file from both local and GCS storage
        
        Args:
            file_path: Path to the file to delete
            
        Returns:
            True if file was deleted successfully
        """
        success = True
        
        # Clean up local file if it exists
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"🧹 Cleaned up local file: {file_path}")
        except Exception as e:
            print(f"⚠️ Failed to cleanup local file {file_path}: {str(e)}")
            success = False
            
        # Clean up GCS file
        try:
            gcs_path = f"downloads/{os.path.basename(file_path)}"
            if not self.gcs.delete_file(gcs_path):
                success = False
        except Exception as e:
            print(f"⚠️ Failed to cleanup GCS file {gcs_path}: {str(e)}")
            success = False
            
        return success 