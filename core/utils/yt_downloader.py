import yt_dlp
import os
from django.conf import settings
from typing import Dict, Optional
import tempfile

class YouTubeDownloader:
    """Utility for downloading YouTube videos using yt-dlp"""
    
    def __init__(self):
        self.temp_dir = tempfile.gettempdir()
    
    def download_video(self, youtube_url: str, output_path: Optional[str] = None) -> str:
        """
        Download a YouTube video to a local file
        
        Args:
            youtube_url: YouTube video URL
            output_path: Optional custom output path
            
        Returns:
            Path to the downloaded video file
        """
        if not output_path:
            # Generate a temporary filename
            import uuid
            filename = f"video_{uuid.uuid4().hex[:8]}.mp4"
            output_path = os.path.join(self.temp_dir, filename)
        
        # Configure yt-dlp options
        ydl_opts = {
            'format': 'best[height<=720]',  # Download best quality up to 720p
            'outtmpl': output_path,
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Download the video
                ydl.download([youtube_url])
                
                # Verify the file was downloaded
                if os.path.exists(output_path):
                    return output_path
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
        Clean up a downloaded video file
        
        Args:
            file_path: Path to the file to delete
            
        Returns:
            True if file was deleted successfully
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception:
            return False 