import os
import tempfile
from typing import List, Dict
from django.conf import settings

from .apify_client import ApifyClient
from .grok_analyzer import GrokAnalyzer
from .yt_downloader import YouTubeDownloader
from .rendi_clip_sender import FFmpegClipProcessor

class VideoProcessor:
    """Main processor for creating viral clips from YouTube videos"""
    
    def __init__(self):
        self.apify_client = ApifyClient()
        self.grok_analyzer = GrokAnalyzer()
        self.yt_downloader = YouTubeDownloader()
        self.ffmpeg_processor = FFmpegClipProcessor()
    
    def process_video(self, youtube_url: str, clip_duration: int) -> Dict:
        """
        Process a YouTube video to create viral clips
        
        Args:
            youtube_url: YouTube video URL
            clip_duration: Desired clip duration in seconds
            
        Returns:
            Dictionary containing processing results and clip data
        """
        video_file_path = None
        clip_files = []
        
        try:
            # Check if FFmpeg is available
            if not self.ffmpeg_processor.is_ffmpeg_available():
                raise Exception("FFmpeg is not installed or not available in PATH")
            
            # Step 1: Fetch transcript using Apify
            print("🎬 Fetching YouTube transcript...")
            transcript_data = self.apify_client.fetch_transcript(youtube_url)
            print(f"✅ Transcript fetched: {transcript_data.get('title', 'Unknown')} ({transcript_data.get('duration', 0)}s)")
            
            # Step 2: Extract viral moments using Grok AI
            print("🤖 Analyzing transcript for viral moments with Grok AI...")
            viral_moments = self.grok_analyzer.extract_viral_moments(transcript_data, clip_duration)
            print(f"✅ Found {len(viral_moments)} viral moments")
            
            # Step 3: Download the full video using yt-dlp
            print("📥 Downloading full video...")
            video_file_path = self.yt_downloader.download_video(youtube_url)
            print(f"✅ Video downloaded: {video_file_path}")
            
            # Step 4: Create clips for each viral moment using FFmpeg
            print("✂️ Creating viral clips...")
            clips_data = []
            
            for i, moment in enumerate(viral_moments):
                grade = moment.get('grade', self.grok_analyzer.convert_score_to_grade(moment['virality_score']))
                print(f"📹 Processing clip {i+1}/{len(viral_moments)} - Grade: {grade} (Score: {moment['virality_score']:.2f})")
                
                # Create clip using FFmpeg
                clip_result = self.ffmpeg_processor.create_clip(
                    input_path=video_file_path,
                    start_time=moment['start_timestamp'],
                    end_time=moment['end_timestamp'],
                    output_filename=f"viral_clip_{i+1}_{grade.replace('+', 'plus').replace('-', 'minus')}.mp4"
                )
                
                # Store clip file path for cleanup
                if clip_result.get('output_path'):
                    clip_files.append(clip_result['output_path'])
                
                # Combine clip data with enhanced metadata
                clip_data = {
                    'rank': i + 1,
                    'start_timestamp': moment['start_timestamp'],
                    'end_timestamp': moment['end_timestamp'],
                    'duration': moment['end_timestamp'] - moment['start_timestamp'],
                    'virality_score': moment['virality_score'],
                    'grade': grade,
                    'justification': moment.get('justification', 'Viral potential detected'),
                    'emotional_keywords': moment.get('emotional_keywords', []),
                    'urgency_indicators': moment.get('urgency_indicators', []),
                    'clip_path': clip_result.get('output_path'),
                    'clip_filename': clip_result.get('output_filename'),
                    'file_size': clip_result.get('file_size'),
                    'resolution': clip_result.get('resolution'),
                    'created_at': self._get_current_timestamp()
                }
                
                clips_data.append(clip_data)
                print(f"✅ Clip {i+1} created: {clip_data['grade']} - {clip_data['justification'][:50]}...")
            
            # Clips are already sorted by virality score from Grok analysis
            print(f"🎯 All {len(clips_data)} viral clips created successfully!")
            
            return {
                'success': True,
                'youtube_url': youtube_url,
                'clip_duration': clip_duration,
                'video_info': {
                    'title': transcript_data.get('title', 'Unknown'),
                    'duration': transcript_data.get('duration', 0),
                    'video_id': transcript_data.get('video_id', ''),
                    'transcript_length': len(transcript_data.get('transcript', []))
                },
                'clips': clips_data,
                'total_clips': len(clips_data),
                'processing_stats': {
                    'avg_virality_score': sum(clip['virality_score'] for clip in clips_data) / len(clips_data) if clips_data else 0,
                    'top_grade': clips_data[0]['grade'] if clips_data else 'N/A',
                    'grade_distribution': self._calculate_grade_distribution(clips_data)
                }
            }
            
        except Exception as e:
            print(f"❌ Processing failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'youtube_url': youtube_url,
                'clip_duration': clip_duration
            }
            
        finally:
            # Clean up downloaded video file
            if video_file_path and os.path.exists(video_file_path):
                print("🧹 Cleaning up downloaded video...")
                self.yt_downloader.cleanup_file(video_file_path)
            
            # Keep clip files for serving (don't clean them up)
            print(f"💾 Keeping {len(clip_files)} generated clips for download")
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def _calculate_grade_distribution(self, clips_data: List[Dict]) -> Dict[str, int]:
        """Calculate distribution of grades across clips"""
        distribution = {}
        for clip in clips_data:
            grade = clip.get('grade', 'Unknown')
            distribution[grade] = distribution.get(grade, 0) + 1
        return distribution
    
    def get_processing_status(self, processing_id: str) -> Dict:
        """
        Get the status of a processing job
        
        Args:
            processing_id: Processing job ID
            
        Returns:
            Dictionary containing processing status
        """
        # This would typically check a database or job queue
        # For now, return a simple status
        return {
            'processing_id': processing_id,
            'status': 'completed',
            'message': 'Processing completed successfully'
        } 