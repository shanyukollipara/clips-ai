# Force redeploy to ensure migrations run on Railway
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.core.paginator import Paginator
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.db import models
import json
import threading
import time
import os
import logging

from .models import VideoProcessing, ViralClip
from .utils.processor import VideoProcessor

# Set up logging
logger = logging.getLogger(__name__)

def index(request):
    """Main page with video processing form"""
    return render(request, 'core/index.html')

@csrf_exempt
@require_http_methods(["POST"])
def process_video(request):
    """Handle video processing request"""
    try:
        print("🎯 Received video processing request")
        data = json.loads(request.body)
        youtube_url = data.get('youtube_url')
        clip_duration = int(data.get('clip_duration', 30))
        
        print(f"📝 Processing URL: {youtube_url} with duration: {clip_duration}s")
        print(f"🔑 API Keys available: GEMINI={bool(os.getenv('GEMINI_API_KEY'))}, APIFY={bool(os.getenv('APIFY_API_KEY'))}")
        
        if not youtube_url:
            return JsonResponse({
                'success': False,
                'error': 'YouTube URL is required'
            }, status=400)
        
        # Validate clip duration
        if clip_duration < 5 or clip_duration > 60:
            return JsonResponse({
                'success': False,
                'error': 'Clip duration must be between 5 and 60 seconds'
            }, status=400)
        
        # Create video processing record
        video_processing = VideoProcessing.objects.create(
            youtube_url=youtube_url,
            clip_duration=clip_duration,
            status='pending'
        )
        
        print(f"✅ Created processing record ID: {video_processing.id}")
        
        # Start processing in background thread
        def process_in_background():
            try:
                print(f"🚀 Starting background processing for ID: {video_processing.id}")
                video_processing.status = 'processing'
                video_processing.save()
                
                processor = VideoProcessor()
                print("✨ VideoProcessor initialized")
                
                # Test Apify connection
                print("🔍 Testing Apify connection...")
                try:
                    from apify_client import ApifyClient
                    client = ApifyClient(os.getenv('APIFY_API_KEY'))
                    print("✅ Apify client created successfully")
                except Exception as e:
                    print(f"❌ Apify connection failed: {str(e)}")
                
                # Test Grok connection
                print("🤖 Testing Grok connection...")
                try:
                    import requests
                    headers = {
                        "Authorization": f"Bearer {os.getenv('GEMINI_API_KEY')}",
                        "Content-Type": "application/json"
                    }
                    print("✅ Grok headers configured")
                except Exception as e:
                    print(f"❌ Grok setup failed: {str(e)}")
                
                print("🎬 Starting video processing...")
                result = processor.process_video(youtube_url, clip_duration)
                print(f"📊 Processing result: {result}")
                
                if result['success']:
                    print(f"💾 Saving {len(result['clips'])} clips to database")
                    for clip_data in result['clips']:
                        ViralClip.objects.create(
                            video_processing=video_processing,
                            start_timestamp=clip_data['start_timestamp'],
                            end_timestamp=clip_data['end_timestamp'],
                            justification=clip_data['justification'],
                            emotional_keywords=', '.join(clip_data.get('emotional_keywords', [])),
                            urgency_indicators=', '.join(clip_data.get('urgency_indicators', [])),
                            virality_score=int(clip_data['virality_score'] * 100),
                            clip_url=clip_data.get('clip_path'),
                            preview_url=None
                        )
                    
                    video_processing.status = 'completed'
                    processing_stats = result.get('processing_stats', {})
                    video_processing.error_message = json.dumps({
                        'stats': processing_stats,
                        'video_info': result.get('video_info', {})
                    })
                    print("✅ Processing completed successfully")
                else:
                    video_processing.status = 'failed'
                    video_processing.error_message = result.get('error', 'Unknown error')
                    print(f"❌ Processing failed: {video_processing.error_message}")
                
                video_processing.save()
                
            except Exception as e:
                print(f"❌ Background thread error: {str(e)}")
                import traceback
                traceback.print_exc()
                video_processing.status = 'failed'
                video_processing.error_message = str(e)
                video_processing.save()
        
        print("🧵 Starting background thread...")
        thread = threading.Thread(target=process_in_background)
        thread.daemon = True
        thread.start()
        print("✅ Background thread started")
        
        return JsonResponse({
            'success': True,
            'processing_id': video_processing.id,
            'message': 'Video processing started! 🎬 Analyzing for viral moments...'
        })
        
    except json.JSONDecodeError:
        print("❌ Invalid JSON data received")
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except ValueError as e:
        print(f"❌ ValueError: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': f'Unexpected error: {str(e)}'
        }, status=500)

def processing_status(request, processing_id):
    """Get processing status with enhanced information"""
    try:
        video_processing = VideoProcessing.objects.get(id=processing_id)
        
        # Parse additional data if available
        additional_data = {}
        if video_processing.error_message and video_processing.status == 'completed':
            try:
                additional_data = json.loads(video_processing.error_message)
            except:
                pass
        
        return JsonResponse({
            'success': True,
            'status': video_processing.status,
            'error_message': video_processing.error_message if video_processing.status == 'failed' else None,
            'created_at': video_processing.created_at.isoformat(),
            'total_clips': video_processing.clips.count(),
            'processing_stats': additional_data.get('stats', {}),
            'video_info': additional_data.get('video_info', {})
        })
        
    except ObjectDoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Processing job not found'
        }, status=404)

def results(request, processing_id):
    """Display processing results with viral ranking"""
    try:
        video_processing = VideoProcessing.objects.get(id=processing_id)
        clips = video_processing.clips.all().order_by('-virality_score')  # Order by virality score
        
        # Paginate clips
        paginator = Paginator(clips, 12)  # 12 clips per page
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        # Parse additional processing data
        additional_data = {}
        if video_processing.error_message and video_processing.status == 'completed':
            try:
                additional_data = json.loads(video_processing.error_message)
            except:
                pass
        
        # Calculate analytics
        total_clips = clips.count()
        if total_clips > 0:
            avg_score = clips.aggregate(avg_score=models.Avg('virality_score'))['avg_score'] or 0
            top_clips = clips.filter(virality_score__gte=80).count()  # A-grade clips
            success_rate = (top_clips / total_clips * 100) if total_clips > 0 else 0
        else:
            avg_score = 0
            top_clips = 0
            success_rate = 0
        
        context = {
            'video_processing': video_processing,
            'clips': page_obj,
            'total_clips': total_clips,
            'success_rate': success_rate,
            'avg_virality_score': avg_score,
            'top_clips_count': top_clips,
            'processing_stats': additional_data.get('stats', {}),
            'video_info': additional_data.get('video_info', {}),
            'grade_distribution': calculate_grade_distribution_from_clips(clips)
        }
        
        return render(request, 'core/results.html', context)
        
    except ObjectDoesNotExist:
        messages.error(request, 'Processing job not found')
        return redirect('index')

def calculate_grade_distribution_from_clips(clips):
    """Calculate grade distribution from clip virality scores"""
    distribution = {}
    for clip in clips:
        score = clip.virality_score / 100.0  # Convert back to 0-1 scale
        if score >= 0.97:
            grade = "A+"
        elif score >= 0.93:
            grade = "A"
        elif score >= 0.90:
            grade = "A-"
        elif score >= 0.87:
            grade = "B+"
        elif score >= 0.83:
            grade = "B"
        elif score >= 0.80:
            grade = "B-"
        elif score >= 0.77:
            grade = "C+"
        elif score >= 0.73:
            grade = "C"
        elif score >= 0.70:
            grade = "C-"
        elif score >= 0.65:
            grade = "D+"
        elif score >= 0.60:
            grade = "D"
        else:
            grade = "F"
        
        distribution[grade] = distribution.get(grade, 0) + 1
    
    return distribution

def clip_detail(request, clip_id):
    """Display individual clip details with viral analysis"""
    try:
        clip = ViralClip.objects.get(id=clip_id)
        
        # Convert virality score to grade
        score = clip.virality_score / 100.0
        if score >= 0.97:
            grade = "A+"
        elif score >= 0.93:
            grade = "A"
        elif score >= 0.90:
            grade = "A-"
        elif score >= 0.87:
            grade = "B+"
        elif score >= 0.83:
            grade = "B"
        elif score >= 0.80:
            grade = "B-"
        elif score >= 0.77:
            grade = "C+"
        elif score >= 0.73:
            grade = "C"
        elif score >= 0.70:
            grade = "C-"
        elif score >= 0.65:
            grade = "D+"
        elif score >= 0.60:
            grade = "D"
        else:
            grade = "F"
        
        # Parse keywords and indicators
        emotional_keywords = clip.emotional_keywords.split(', ') if clip.emotional_keywords else []
        urgency_indicators = clip.urgency_indicators.split(', ') if clip.urgency_indicators else []
        
        context = {
            'clip': clip,
            'video_processing': clip.video_processing,
            'grade': grade,
            'emotional_keywords': emotional_keywords,
            'urgency_indicators': urgency_indicators,
            'duration': clip.end_timestamp - clip.start_timestamp
        }
        
        return render(request, 'core/clip_detail.html', context)
        
    except ObjectDoesNotExist:
        messages.error(request, 'Clip not found')
        return redirect('index')

def download_clip(request, clip_id):
    """Download a clip file"""
    try:
        clip = ViralClip.objects.get(id=clip_id)
        
        if not clip.clip_url or not os.path.exists(clip.clip_url):
            return JsonResponse({
                'success': False,
                'error': 'Clip file not found'
            }, status=404)
        
        # Serve the file
        with open(clip.clip_url, 'rb') as f:
            response = HttpResponse(f.read(), content_type='video/mp4')
            filename = f"viral_clip_{clip.virality_score}_{clip.id}.mp4"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
            
    except ObjectDoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Clip not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Download failed: {str(e)}'
        }, status=500)

def history(request):
    """Display processing history with enhanced stats"""
    # Get all video processings and annotate with best clip score
    video_processings = VideoProcessing.objects.annotate(
        best_score=models.Max('clips__virality_score'),
        clip_count=models.Count('clips')
    ).order_by('-best_score', '-created_at')
    
    # Paginate results
    paginator = Paginator(video_processings, 10)  # 10 items per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Calculate overall statistics
    total_processed = VideoProcessing.objects.count()
    successful_processings = VideoProcessing.objects.filter(status='completed').count()
    total_clips = ViralClip.objects.count()
    avg_clips_per_video = total_clips / successful_processings if successful_processings > 0 else 0
    
    # Get top performing clips
    top_clips = ViralClip.objects.order_by('-virality_score')[:5]
    
    context = {
        'video_processings': page_obj,
        'total_processed': total_processed,
        'successful_processings': successful_processings,
        'total_clips_generated': total_clips,
        'avg_clips_per_video': round(avg_clips_per_video, 1),
        'success_percentage': (successful_processings / total_processed * 100) if total_processed > 0 else 0,
        'top_clips': top_clips
    }
    
    return render(request, 'core/history.html', context)
