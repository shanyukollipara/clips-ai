import os
import json
import requests
from typing import List, Dict, Any
from django.conf import settings

class GrokAnalyzer:
    """AI-powered viral moment detection using Grok API"""
    
    def __init__(self):
        # Try Django settings first, then environment variable
        self.api_key = getattr(settings, 'GROK_API_KEY', None) or os.environ.get('GROK_API_KEY')
        self.api_url = getattr(settings, 'GROK_API_URL', None) or os.environ.get('GROK_API_URL', 'https://api.x.ai')
        self.model = "grok-3-mini"  # Using xAI Grok model
        
        if not self.api_key:
            raise ValueError("GROK_API_KEY not found in Django settings or environment variables")
            
        # Test connection during initialization
        self._test_connection()
    
    def _test_connection(self):
        """Test the Grok API connection"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a test assistant."
                },
                {
                    "role": "user",
                    "content": "Test connection. Reply with 'ok' only."
                }
            ],
            "temperature": 0,
            "max_tokens": 10
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            print("✅ Successfully connected to Grok API")
        except Exception as e:
            print(f"❌ Failed to connect to Grok API: {str(e)}")
            raise

    def extract_viral_moments(self, transcript_data: Dict, clip_duration: int) -> List[Dict]:
        """
        Extract viral moments from video transcript using Grok AI
        
        Args:
            transcript_data: Dictionary with transcript info
            clip_duration: Desired clip duration in seconds
            
        Returns:
            List of viral moments with timestamps, scores, and justifications
        """
        # Extract transcript text and timing info
        transcript_segments = transcript_data.get('transcript', [])
        if not transcript_segments:
            raise ValueError("No transcript segments found")
        
        print(f"📝 Analyzing transcript with {len(transcript_segments)} segments")
        print(f"⏱️ Target clip duration: {clip_duration}s")
        
        # Convert transcript to text with timestamps
        transcript_text = self._format_transcript_for_analysis(transcript_segments)
        print("✅ Formatted transcript for analysis")
        
        # Create Grok prompt for viral moment detection
        prompt = f"""
Analyze this YouTube video transcript and identify the TOP 5 most viral moments that would make great short clips.

VIDEO TRANSCRIPT WITH TIMESTAMPS:
{transcript_text}

CLIP REQUIREMENTS:
- Each clip should be exactly {clip_duration} seconds long
- Focus on moments with high engagement potential (humor, shock, emotion, valuable insights)
- Consider viral elements: hooks, punchlines, dramatic reveals, strong emotions, quotable moments

For each viral moment, provide:
1. START_TIME and END_TIME (in seconds) for a {clip_duration}-second clip
2. VIRALITY_SCORE (0.0 to 1.0 scale where 1.0 = extremely viral)
3. GRADE (A+, A, A-, B+, B, B-, C+, C, C-, D+, D, F)
4. JUSTIFICATION (why this moment is viral - specific reasons)
5. EMOTIONAL_KEYWORDS (3-5 words describing the emotion/hook)
6. URGENCY_INDICATORS (what makes people want to share immediately)

Respond ONLY in valid JSON format:
{{
  "viral_moments": [
    {{
      "start_timestamp": 45.2,
      "end_timestamp": 75.2,
      "virality_score": 0.92,
      "grade": "A",
      "justification": "Unexpected plot twist with strong emotional reaction that creates shareable moment",
      "emotional_keywords": ["shocking", "unexpected", "emotional", "relatable"],
      "urgency_indicators": ["plot twist", "strong reaction", "quotable line"]
    }}
  ]
}}
"""
        print("📋 Created Grok analysis prompt")

        # Call Grok API
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert social media analyst who identifies viral video moments. You understand what makes content shareable and engaging across platforms like TikTok, Instagram Reels, and YouTube Shorts."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 2000
        }
        
        print(f"🤖 Calling Grok API with model: {self.model}")
        if self.api_key:
            print(f"🔑 Using API key: {self.api_key[:10]}...")
        else:
            print("🔑 No API key found")
        
        try:
            response = requests.post(
                f"{self.api_url}/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
            print(f"📡 Grok API response status: {response.status_code}")
            response.raise_for_status()
            
            result = response.json()
            if not result or 'choices' not in result or not result['choices']:
                raise ValueError("Invalid response format from Grok API")
            content = result['choices'][0]['message']['content']
            print("✅ Received Grok API response")
            
            # Parse JSON response
            try:
                print("🔍 Parsing Grok response as JSON")
                print(f"🔍 Raw content: {content[:1000]}...")  # Show first 1000 chars for debugging
                parsed_content = json.loads(content)
                viral_moments = parsed_content.get('viral_moments', [])
                print(f"✨ Found {len(viral_moments)} viral moments")
            except json.JSONDecodeError as e:
                print(f"⚠️ JSON parse failed: {str(e)}")
                print(f"🔍 Content that failed to parse: {content[:500]}...")
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    try:
                        parsed_content = json.loads(json_match.group())
                        viral_moments = parsed_content.get('viral_moments', [])
                        print(f"✅ Successfully extracted {len(viral_moments)} viral moments from text")
                    except json.JSONDecodeError:
                        print("❌ Even extracted JSON is malformed, creating fallback response")
                        viral_moments = []
                else:
                    print("❌ No JSON found in response, creating fallback response")
                    viral_moments = []
            # Always ensure at least one fallback viral moment if none found
            if not viral_moments:
                print("⚠️ No viral moments found, using fallback.")
                viral_moments = self._create_fallback_moments(transcript_data, clip_duration)
            print(f"✅ Returning {len(viral_moments)} viral moments (AI + fallback)")
            
            # Validate and clean up results
            validated_moments = self._validate_viral_moments(viral_moments, transcript_data.get('duration', 0))
            print(f"✅ Validated {len(validated_moments)} viral moments")
            
            # Print some sample data
            if validated_moments:
                sample = validated_moments[0]
                print("\n📊 Sample viral moment:")
                print(f"⏱️ Timestamp: {sample['start_timestamp']}s - {sample['end_timestamp']}s")
                print(f"📈 Score: {sample['virality_score']:.2f}")
                print(f"📝 Grade: {sample['grade']}")
                print(f"💡 Keywords: {', '.join(sample.get('emotional_keywords', []))}")
            
            return validated_moments
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Grok API request failed: {str(e)}")
            raise Exception(f"Grok API request failed: {str(e)}")
        except Exception as e:
            print(f"❌ Failed to analyze transcript with Grok: {str(e)}")
            raise Exception(f"Failed to analyze transcript with Grok: {str(e)}")
    
    def _format_transcript_for_analysis(self, transcript_segments: List[Dict]) -> str:
        """Format transcript segments with timestamps for AI analysis"""
        formatted_lines = []
        
        for segment in transcript_segments:
            if 'start' in segment and 'text' in segment:
                start_time = segment['start']
                text = segment['text'].strip()
                if text:
                    formatted_lines.append(f"[{start_time:.1f}s] {text}")
        
        return '\n'.join(formatted_lines)
    
    def _validate_viral_moments(self, viral_moments: List[Dict], video_duration: float) -> List[Dict]:
        """Validate and clean up viral moments data"""
        validated_moments = []
        
        for moment in viral_moments:
            # Ensure required fields exist
            if not all(key in moment for key in ['start_timestamp', 'end_timestamp', 'virality_score']):
                continue
            
            start_time = float(moment['start_timestamp'])
            end_time = float(moment['end_timestamp'])
            
            # Validate timestamp bounds
            if start_time < 0 or end_time > video_duration or start_time >= end_time:
                continue
            
            # Ensure virality score is in valid range
            virality_score = max(0.0, min(1.0, float(moment.get('virality_score', 0.5))))
            
            validated_moment = {
                'start_timestamp': start_time,
                'end_timestamp': end_time,
                'virality_score': virality_score,
                'grade': moment.get('grade', 'B'),
                'justification': moment.get('justification', 'Viral potential detected'),
                'emotional_keywords': moment.get('emotional_keywords', []),
                'urgency_indicators': moment.get('urgency_indicators', [])
            }
            
            validated_moments.append(validated_moment)
        
        # Sort by virality score (highest first)
        validated_moments.sort(key=lambda x: x['virality_score'], reverse=True)
        
        return validated_moments
    
    def score_virality(self, moment: Dict) -> float:
        """
        Legacy method for backward compatibility
        Returns the virality score for a moment
        """
        return moment.get('virality_score', 0.5)
    
    def convert_score_to_grade(self, score: float) -> str:
        """Convert numerical virality score to letter grade"""
        if score >= 0.97:
            return "A+"
        elif score >= 0.93:
            return "A"
        elif score >= 0.90:
            return "A-"
        elif score >= 0.87:
            return "B+"
        elif score >= 0.83:
            return "B"
        elif score >= 0.80:
            return "B-"
        elif score >= 0.77:
            return "C+"
        elif score >= 0.73:
            return "C"
        elif score >= 0.70:
            return "C-"
        elif score >= 0.65:
            return "D+"
        elif score >= 0.60:
            return "D"
        else:
            return "F"
    
    def _create_fallback_moments(self, transcript_data: Dict, clip_duration: int) -> List[Dict]:
        """Create fallback viral moments when AI analysis fails"""
        transcript_segments = transcript_data.get('transcript', [])
        if not transcript_segments:
            return []
        
        # Create some basic clips from the transcript
        moments = []
        total_duration = transcript_data.get('duration', 0)
        
        # Create 3 clips: beginning, middle, end
        for i, position in enumerate(['beginning', 'middle', 'end']):
            if position == 'beginning':
                start_time = max(0, 10)  # Start 10 seconds in
            elif position == 'middle':
                start_time = max(0, total_duration / 2 - clip_duration / 2)
            else:  # end
                start_time = max(0, total_duration - clip_duration - 10)
            
            end_time = min(total_duration, start_time + clip_duration)
            
            if end_time > start_time:
                moments.append({
                    'start_timestamp': start_time,
                    'end_timestamp': end_time,
                    'virality_score': 0.7 - (i * 0.1),  # Decreasing scores
                    'grade': 'B',
                    'justification': f'Fallback clip from {position} of video',
                    'emotional_keywords': ['engaging', 'content'],
                    'urgency_indicators': ['interesting', 'moment']
                })
        
        return moments 