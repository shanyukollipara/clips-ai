import os
import json
import requests
from typing import List, Dict
from django.conf import settings

class GeminiAnalyzer:
    """AI-powered viral moment detection using Google Gemini API (cheapest model)"""
    
    def __init__(self):
        self.api_key = getattr(settings, 'GEMINI_API_KEY', None) or os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in Django settings or environment variables")
        
        # Use Gemini 1.5 Pro (more reliable availability)
        self.api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent"
        self.model = "gemini-1.5-pro"
        
        print(f"🤖 Gemini Analyzer initialized with model: {self.model}")
    
    def extract_viral_moments(self, transcript_data: Dict, clip_duration: int) -> List[Dict]:
        """
        Extract viral moments from video transcript using Gemini AI
        
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
        
        # Create Gemini prompt for viral moment detection
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

IMPORTANT: Respond ONLY with valid JSON. Do not include any text before or after the JSON. Do not use markdown formatting.

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
        print("📋 Created Gemini analysis prompt")

        # Prepare request payload for Gemini
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.3,  # Lower temperature for more consistent JSON
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 3000,  # Increase token limit
            }
        }
        
        print(f"🤖 Calling Gemini API with model: {self.model}")
        if self.api_key:
            print(f"🔑 Using API key: {self.api_key[:10]}...")
        else:
            print("🔑 No API key found")
        
        try:
            response = requests.post(
                f"{self.api_url}?key={self.api_key}",
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=120  # Increase timeout to 2 minutes
            )
            print(f"📡 Gemini API response status: {response.status_code}")
            response.raise_for_status()
            
            result = response.json()
            if not result or 'candidates' not in result or not result['candidates']:
                raise ValueError("Invalid response format from Gemini API")
            
            # Extract text from Gemini response
            content = result['candidates'][0]['content']['parts'][0]['text']
            print("✅ Received Gemini API response")
            
            # Parse JSON response
            try:
                print("🔍 Parsing Gemini response as JSON")
                print(f"🔍 Raw content: {content[:1000]}...")  # Show first 1000 chars for debugging
                
                # Clean up the content first
                cleaned_content = content.strip()
                
                # Remove markdown code blocks if present
                if cleaned_content.startswith('```json'):
                    cleaned_content = cleaned_content[7:]  # Remove ```json
                if cleaned_content.endswith('```'):
                    cleaned_content = cleaned_content[:-3]  # Remove ```
                
                cleaned_content = cleaned_content.strip()
                
                parsed_content = json.loads(cleaned_content)
                viral_moments = parsed_content.get('viral_moments', [])
                print(f"✨ Found {len(viral_moments)} viral moments")
            except json.JSONDecodeError as e:
                print(f"⚠️ JSON parse failed: {str(e)}")
                print(f"🔍 Content that failed to parse: {content[:500]}...")
                
                # Try to extract and fix JSON using regex
                import re
                
                # First try to find a complete JSON block
                json_match = re.search(r'\{.*"viral_moments".*\}', content, re.DOTALL)
                if json_match:
                    try:
                        potential_json = json_match.group()
                        print(f"🔧 Attempting to parse extracted JSON: {potential_json[:200]}...")
                        parsed_content = json.loads(potential_json)
                        viral_moments = parsed_content.get('viral_moments', [])
                        print(f"✅ Successfully extracted {len(viral_moments)} viral moments from text")
                    except json.JSONDecodeError:
                        print("❌ Extracted JSON is still malformed, trying manual parsing")
                        viral_moments = self._parse_broken_json(content)
                else:
                    print("❌ No JSON structure found, trying manual parsing")
                    viral_moments = self._parse_broken_json(content)
            
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
            print(f"❌ Gemini API request failed: {str(e)}")
            raise Exception(f"Gemini API request failed: {str(e)}")
        except Exception as e:
            print(f"❌ Failed to analyze transcript with Gemini: {str(e)}")
            raise Exception(f"Failed to analyze transcript with Gemini: {str(e)}")
    
    def _format_transcript_for_analysis(self, transcript_segments: List[Dict]) -> str:
        """Format transcript segments into text with timestamps for AI analysis"""
        formatted_text = ""
        for i, segment in enumerate(transcript_segments):
            start_time = float(segment.get('start', 0))
            text = segment.get('text', '').strip()
            if text:
                formatted_text += f"[{start_time:.1f}s] {text}\n"
        
        return formatted_text
    
    def _validate_viral_moments(self, viral_moments: List[Dict], total_duration: float) -> List[Dict]:
        """Validate and clean up viral moments data"""
        validated = []
        
        for moment in viral_moments:
            try:
                start_time = float(moment.get('start_timestamp', 0))
                end_time = float(moment.get('end_timestamp', 30))
                
                # Ensure timestamps are within video bounds
                start_time = max(0, min(start_time, total_duration - 30))
                end_time = min(total_duration, start_time + 30)
                
                # Ensure score is valid
                score = float(moment.get('virality_score', 0.7))
                score = max(0.0, min(1.0, score))
                
                # Ensure required fields exist
                validated_moment = {
                    'start_timestamp': start_time,
                    'end_timestamp': end_time,
                    'virality_score': score,
                    'grade': moment.get('grade', self.convert_score_to_grade(score)),
                    'justification': moment.get('justification', 'Viral potential detected'),
                    'emotional_keywords': moment.get('emotional_keywords', ['engaging']),
                    'urgency_indicators': moment.get('urgency_indicators', ['interesting'])
                }
                
                validated.append(validated_moment)
                
            except (ValueError, TypeError) as e:
                print(f"⚠️ Skipping invalid moment: {str(e)}")
                continue
        
        # Sort by virality score descending
        validated.sort(key=lambda x: x['virality_score'], reverse=True)
        
        return validated[:5]  # Return top 5
    
    def convert_score_to_grade(self, score: float) -> str:
        """Convert numerical score to letter grade"""
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
    
    def _parse_broken_json(self, content: str) -> List[Dict]:
        """
        Manually parse broken JSON responses from Gemini API
        This handles cases where the JSON is malformed or truncated
        """
        viral_moments = []
        
        try:
            import re
            
            # Look for individual moment blocks in the content
            # Pattern to match moment objects even if JSON is broken
            moment_pattern = r'"start_timestamp":\s*([0-9.]+).*?"end_timestamp":\s*([0-9.]+).*?"virality_score":\s*([0-9.]+).*?"grade":\s*"([^"]*)".*?"justification":\s*"([^"]*)"'
            
            matches = re.findall(moment_pattern, content, re.DOTALL)
            
            print(f"🔍 Found {len(matches)} moment patterns in broken JSON")
            
            for match in matches:
                try:
                    start_time = float(match[0])
                    end_time = float(match[1])
                    score = float(match[2])
                    grade = match[3]
                    justification = match[4]
                    
                    # Extract keywords and indicators if present
                    keywords = []
                    indicators = []
                    
                    # Look for emotional_keywords array
                    keyword_pattern = r'"emotional_keywords":\s*\[(.*?)\]'
                    keyword_match = re.search(keyword_pattern, content)
                    if keyword_match:
                        keywords_str = keyword_match.group(1)
                        keywords = [k.strip(' "') for k in keywords_str.split(',') if k.strip()]
                    
                    # Look for urgency_indicators array
                    indicator_pattern = r'"urgency_indicators":\s*\[(.*?)\]'
                    indicator_match = re.search(indicator_pattern, content)
                    if indicator_match:
                        indicators_str = indicator_match.group(1)
                        indicators = [i.strip(' "') for i in indicators_str.split(',') if i.strip()]
                    
                    moment = {
                        'start_timestamp': start_time,
                        'end_timestamp': end_time,
                        'virality_score': score,
                        'grade': grade,
                        'justification': justification,
                        'emotional_keywords': keywords or ['engaging'],
                        'urgency_indicators': indicators or ['interesting']
                    }
                    
                    viral_moments.append(moment)
                    print(f"✅ Parsed moment: {start_time}s-{end_time}s, Score: {score}")
                    
                except (ValueError, IndexError) as e:
                    print(f"⚠️ Failed to parse moment: {str(e)}")
                    continue
            
            print(f"✅ Successfully parsed {len(viral_moments)} moments from broken JSON")
            
        except Exception as e:
            print(f"❌ Manual parsing failed: {str(e)}")
        
        return viral_moments 