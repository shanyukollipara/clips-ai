import os
from typing import Dict
from apify_client import ApifyClient as BaseApifyClient
from django.conf import settings

class ApifyClient:
    """Client for fetching YouTube transcripts using Apify"""
    
    def __init__(self):
        # Try Django settings first, then environment variable
        self.api_key = getattr(settings, 'APIFY_API_KEY', None) or os.getenv('APIFY_API_KEY')
        if not self.api_key:
            raise ValueError("APIFY_API_KEY not found in Django settings or environment variables")
        
        self.actor_id = getattr(settings, 'APIFY_ACTOR_ID', None) or os.getenv('APIFY_ACTOR_ID', 'faVsWy9VTSNVIhWpR')
        print(f"🔑 Initializing Apify client with key: {self.api_key[:10]}...")
        self.client = BaseApifyClient(self.api_key)
    
    def fetch_transcript(self, youtube_url: str) -> Dict:
        """
        Fetch transcript for a YouTube video
        
        Args:
            youtube_url: YouTube video URL
            
        Returns:
            Dictionary containing transcript data
        """
        try:
            print(f"📝 Fetching transcript for URL: {youtube_url}")
            print(f"🎭 Using Apify Actor ID: {self.actor_id}")
            
            # Start the actor and wait for it to finish
            # Try different possible input parameter names
            run_input = {
                'videoUrl': youtube_url,
                'url': youtube_url,
                'video_url': youtube_url,
                'youtube_url': youtube_url
            }
            run = self.client.actor(self.actor_id).call(run_input=run_input)
            if not run:
                raise ValueError("Apify actor run failed - no response received")
            print(f"✅ Apify actor run completed with ID: {run.get('id', 'unknown')}")
            
            # Fetch the actor run dataset
            dataset_items = self.client.dataset(run["defaultDatasetId"]).list_items().items
            print(f"📊 Retrieved {len(dataset_items)} items from dataset")
            
            if not dataset_items:
                raise ValueError("No transcript data found")
            
            # Get the first item which contains our transcript
            transcript_data = dataset_items[0]
            print(f"🔍 Raw transcript data keys: {list(transcript_data.keys())}")
            print(f"🔍 Transcript data sample: {str(transcript_data)[:500]}...")
            # Handle different possible transcript data formats
            transcript_segments = []
            if 'transcript' in transcript_data:
                transcript_segments = transcript_data.get('transcript', [])
            elif 'data' in transcript_data:
                raw_data = transcript_data.get('data', [])
                for item in raw_data:
                    if 'text' in item and 'start' in item:
                        transcript_segments.append({
                            'start': float(item['start']),
                            'text': item['text']
                        })
            # Try to extract duration if not present
            duration = transcript_data.get('duration', 0)
            if not duration and transcript_segments:
                try:
                    last_segment = transcript_segments[-1]
                    duration = float(last_segment['start']) + 10  # Add 10s buffer
                except Exception as e:
                    print(f"⚠️ Could not extract duration from transcript: {e}")
                    duration = 0
            print(f"✨ Successfully extracted transcript with {len(transcript_segments)} segments and duration {duration}s")
            return {
                'title': transcript_data.get('title', 'Unknown'),
                'duration': duration,
                'video_id': transcript_data.get('id', ''),
                'transcript': transcript_segments
            }
            
        except Exception as e:
            print(f"❌ Apify transcript fetch failed: {str(e)}")
            import traceback
            traceback.print_exc()
            raise Exception(f"Failed to fetch transcript: {str(e)}") 