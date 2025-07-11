from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.core.paginator import Paginator
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
import json
import threading
import time
import os

from .models import VideoProcessing, ViralClip
from .utils.processor import VideoProcessor

def index(request):
    """Main page with video processing form"""
    return render(request, 'core/index.html')

@require_http_methods(["POST"])
def process_video(request):
    """Handle video processing request"""
    try:
        data = json.loads(request.body)
        youtube_url = data.get('youtube_url')
        clip_duration = int(data.get('clip_duration', 30))
        
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
        
        # Start processing in background thread
        def process_in_background():
            try:
                video_processing.status = 'processing'
                video_processing.save()
                
                processor = VideoProcessor()
                result = processor.process_video(youtube_url, clip_duration)
                
                if result['success']:
                    # Save clips to database
                    for clip_data in result['clips']:
                        ViralClip.objects.create(
                            video_processing=video_processing,
                            start_timestamp=clip_data['start_timestamp'],
                            end_timestamp=clip_data['end_timestamp'],
                            justification=clip_data['justification'],
                            emotional_keywords=clip_data['emotional_keywords'],
                            urgency_indicators=clip_data['urgency_indicators'],
                            virality_score=clip_data['virality_score'],
                            clip_url=clip_data.get('clip_path'),  # Store local path as URL for now
                            preview_url=None  # No preview URL for local files
                        )
                    
                    video_processing.status = 'completed'
                else:
                    video_processing.status = 'failed'
                    video_processing.error_message = result.get('error', 'Unknown error')
                
                video_processing.save()
                
            except Exception as e:
                video_processing.status = 'failed'
                video_processing.error_message = str(e)
                video_processing.save()
        
        # Start background processing
        thread = threading.Thread(target=process_in_background)
        thread.daemon = True
        thread.start()
        
        return JsonResponse({
            'success': True,
            'processing_id': video_processing.id,
            'message': 'Video processing started'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except ValueError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Unexpected error: {str(e)}'
        }, status=500)

def processing_status(request, processing_id):
    """Get processing status"""
    try:
        video_processing = VideoProcessing.objects.get(id=processing_id)
        
        return JsonResponse({
            'success': True,
            'status': video_processing.status,
            'error_message': video_processing.error_message,
            'created_at': video_processing.created_at.isoformat(),
            'total_clips': video_processing.clips.count()
        })
        
    except ObjectDoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Processing job not found'
        }, status=404)

def results(request, processing_id):
    """Display processing results"""
    try:
        video_processing = VideoProcessing.objects.get(id=processing_id)
        clips = video_processing.clips.all()
        
        # Paginate clips
        paginator = Paginator(clips, 12)  # 12 clips per page
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'video_processing': video_processing,
            'clips': page_obj,
            'total_clips': clips.count(),
            'success_rate': (clips.filter(virality_score__gte=70).count() / clips.count() * 100) if clips.count() > 0 else 0
        }
        
        return render(request, 'core/results.html', context)
        
    except ObjectDoesNotExist:
        messages.error(request, 'Processing job not found')
        return redirect('index')

def clip_detail(request, clip_id):
    """Display individual clip details"""
    try:
        clip = ViralClip.objects.get(id=clip_id)
        
        context = {
            'clip': clip,
            'video_processing': clip.video_processing
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
            response['Content-Disposition'] = f'attachment; filename="{os.path.basename(clip.clip_url)}"'
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
    """Display processing history"""
    video_processings = VideoProcessing.objects.all().order_by('-created_at')
    
    # Paginate results
    paginator = Paginator(video_processings, 10)  # 10 items per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'video_processings': page_obj,
        'total_processed': VideoProcessing.objects.count(),
        'successful_processings': VideoProcessing.objects.filter(status='completed').count()
    }
    
    return render(request, 'core/history.html', context)
