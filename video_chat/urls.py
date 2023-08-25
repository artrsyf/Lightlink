from django.urls import path
from video_chat.views import *

urlpatterns = [
    path('Home', index, name='WebChatHome'),
]
