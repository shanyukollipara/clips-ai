from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.index, name='index'),
    path('process/', views.process_video, name='process_video'),
    path('status/<int:processing_id>/', views.processing_status, name='processing_status'),
    path('results/<int:processing_id>/', views.results, name='results'),
    path('clip/<int:clip_id>/', views.clip_detail, name='clip_detail'),
    path('clip/<int:clip_id>/download/', views.download_clip, name='download_clip'),
    path('history/', views.history, name='history'),
] 