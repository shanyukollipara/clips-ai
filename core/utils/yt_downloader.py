import yt_dlp
import os
import logging
from django.conf import settings
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class YouTubeDownloader:
    """Utility for downloading YouTube videos using yt-dlp"""
    
    def __init__(self):
        self.media_root = getattr(settings, 'MEDIA_ROOT', 'media')
        self.downloads_dir = os.path.join(self.media_root, 'downloads')
        os.makedirs(self.downloads_dir, exist_ok=True)
        
        # Try to initialize GCS storage, but don't fail if it's not available
        self.gcs = None
        self.use_gcs = False
        
        try:
            from .gcs_storage import GCSStorage
            self.gcs = GCSStorage()
            self.use_gcs = True
            logger.info("✅ GCS storage initialized - files will be uploaded to cloud")
        except Exception as e:
            logger.warning(f"⚠️ GCS storage not available: {str(e)}")
            logger.info("📁 Using local file storage only")
    
    def download_video(self, youtube_url: str, output_path: Optional[str] = None) -> str:
        """
        Download a YouTube video and optionally upload to GCS
        
        Args:
            youtube_url: YouTube video URL
            output_path: Optional custom output path
            
        Returns:
            Local file path or GCS URL of the video
        """
        if not output_path:
            # Get video info first to use title in filename
            info = self.get_video_info(youtube_url)
            video_id = youtube_url.split('v=')[-1].split('&')[0]  # Handle URL parameters
            safe_title = ''.join(c for c in info.get('title', video_id) if c.isalnum() or c in ' -_')[:50]
            filename = f"{safe_title}_{video_id}.mp4"
            output_path = os.path.join(self.downloads_dir, filename)
        
        # Ensure the output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Configure yt-dlp options
        ydl_opts = {
            'format': 'best[height<=720]',  # Download best quality up to 720p
            'outtmpl': output_path,
            'quiet': False,  # Enable output to see what's happening
            'no_warnings': False,  # Show warnings to debug
            'extract_flat': False,
            'merge_output_format': 'mp4',
            'socket_timeout': 60,  # Increase socket timeout
            'retries': 5,  # Increase retry attempts
            'fragment_retries': 5,  # Retry failed fragments
            'skip_unavailable_fragments': True,
            'keep_fragments': False,
            'abort_on_unavailable_fragments': False,
            'ignoreerrors': False,  # Don't ignore errors so we can see them
            'no_check_certificates': True,
            'prefer_insecure': True,
            # Add headers to bypass 403 errors
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            },
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4'
            }]
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.info(f"📥 Downloading video: {youtube_url}")
                logger.info(f"🎯 Expected output path: {output_path}")
                
                # Download the video
                ydl.download([youtube_url])
                logger.info(f"✅ Download completed")
                
                # Check if the exact file exists
                if os.path.exists(output_path):
                    file_size = os.path.getsize(output_path)
                    logger.info(f"📊 Downloaded file size: {file_size / (1024*1024):.1f} MB")
                    final_path = output_path
                else:
                    # Sometimes yt-dlp creates files with slightly different names
                    # Look for any MP4 files in the downloads directory that match the video ID
                    logger.warning(f"⚠️ Expected file not found: {output_path}")
                    logger.info("🔍 Searching for downloaded file...")
                    
                    downloaded_files = []
                    for file in os.listdir(self.downloads_dir):
                        if file.endswith('.mp4') and video_id in file:
                            full_path = os.path.join(self.downloads_dir, file)
                            downloaded_files.append(full_path)
                            logger.info(f"📁 Found potential file: {full_path}")
                    
                    if downloaded_files:
                        # Use the most recently created file
                        final_path = max(downloaded_files, key=os.path.getctime)
                        logger.info(f"✅ Using downloaded file: {final_path}")
                        file_size = os.path.getsize(final_path)
                        logger.info(f"📊 Downloaded file size: {file_size / (1024*1024):.1f} MB")
                    else:
                        raise Exception("Video download completed but no file found")
                
                # Upload to GCS if available
                if self.use_gcs and self.gcs:
                    try:
                        gcs_path = f"downloads/{os.path.basename(final_path)}"
                        gcs_url = self.gcs.upload_file(final_path, gcs_path)
                        
                        # Clean up local file after successful upload
                        os.remove(final_path)
                        logger.info(f"🧹 Cleaned up local file after GCS upload: {final_path}")
                        
                        return gcs_url
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to upload to GCS: {str(e)}")
                        logger.info("📁 Falling back to local file storage")
                
                # Return local file path if GCS is not available or failed
                logger.info(f"📁 Using local file: {final_path}")
                return final_path
                    
        except Exception as e:
            logger.warning(f"⚠️ First download attempt failed: {str(e)}")
            
            # Try fallback format options
            fallback_formats = [
                'best[height<=480]',  # Lower quality
                'worst[ext=mp4]',     # Worst quality MP4
                'best[ext=mp4]',      # Best MP4
                'best',               # Any best format
            ]
            
            for format_selector in fallback_formats:
                try:
                    logger.info(f"🔄 Trying fallback format: {format_selector}")
                    
                    # Update format and try again
                    ydl_opts['format'] = format_selector
                    
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([youtube_url])
                        
                        # Check if the exact file exists
                        if os.path.exists(output_path):
                            file_size = os.path.getsize(output_path)
                            logger.info(f"✅ Fallback download successful: {file_size / (1024*1024):.1f} MB")
                            final_path = output_path
                        else:
                            # Look for any MP4 files that match the video ID
                            logger.info("🔍 Searching for fallback downloaded file...")
                            
                            downloaded_files = []
                            for file in os.listdir(self.downloads_dir):
                                if file.endswith('.mp4') and video_id in file:
                                    full_path = os.path.join(self.downloads_dir, file)
                                    downloaded_files.append(full_path)
                                    logger.info(f"📁 Found potential fallback file: {full_path}")
                            
                            if downloaded_files:
                                # Use the most recently created file
                                final_path = max(downloaded_files, key=os.path.getctime)
                                logger.info(f"✅ Using fallback downloaded file: {final_path}")
                                file_size = os.path.getsize(final_path)
                                logger.info(f"📊 Fallback file size: {file_size / (1024*1024):.1f} MB")
                            else:
                                raise Exception("Fallback download completed but no file found")
                        
                        # Upload to GCS if available
                        if self.use_gcs and self.gcs:
                            try:
                                gcs_path = f"downloads/{os.path.basename(final_path)}"
                                gcs_url = self.gcs.upload_file(final_path, gcs_path)
                                
                                # Clean up local file after successful upload
                                os.remove(final_path)
                                logger.info(f"🧹 Cleaned up local file after GCS upload: {final_path}")
                                
                                return gcs_url
                            except Exception as e:
                                logger.warning(f"⚠️ Failed to upload to GCS: {str(e)}")
                                logger.info("📁 Falling back to local file storage")
                        
                        # Return local file path if GCS is not available or failed
                        logger.info(f"📁 Using local file: {final_path}")
                        return final_path
                
                except Exception as fallback_error:
                    logger.warning(f"⚠️ Fallback format {format_selector} failed: {str(fallback_error)}")
                    continue
            
            # Clean up partial download if it exists
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                    logger.debug(f"🧹 Cleaned up partial download: {output_path}")
                except:
                    pass
            raise Exception(f"All download attempts failed. Last error: {str(e)}")
    
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
            logger.debug(f"🔍 Getting video info for: {youtube_url}")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(youtube_url, download=False)
                
                if info is None:
                    raise Exception("Failed to extract video information")
                
                video_info = {
                    'title': info.get('title'),
                    'duration': info.get('duration'),
                    'uploader': info.get('uploader'),
                    'view_count': info.get('view_count'),
                    'like_count': info.get('like_count'),
                    'description': info.get('description'),
                    'thumbnail': info.get('thumbnail'),
                    'webpage_url': info.get('webpage_url'),
                }
                
                logger.debug(f"✅ Video info retrieved: {video_info.get('title')} ({video_info.get('duration')}s)")
                return video_info
                
        except Exception as e:
            logger.error(f"❌ Failed to get video info: {str(e)}")
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
                logger.info(f"🧹 Cleaned up local file: {file_path}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to cleanup local file {file_path}: {str(e)}")
            success = False
            
        # Clean up GCS file if GCS is available
        if self.use_gcs and self.gcs:
            try:
                gcs_path = f"downloads/{os.path.basename(file_path)}"
                if not self.gcs.delete_file(gcs_path):
                    success = False
            except Exception as e:
                logger.warning(f"⚠️ Failed to cleanup GCS file {gcs_path}: {str(e)}")
                success = False
        
        return success 