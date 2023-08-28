from django.urls import path
from video_chat.views import *

urlpatterns = [
    path('Home', index, name='WebChatHome'),
    path('return_profile_data/<int:_id>', return_profile_data),
    path('call_process', call_process)
]
