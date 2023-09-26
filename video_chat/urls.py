from django.urls import path
from video_chat.views import *

urlpatterns = [
    path('Home', index, name='WebChatHome'),
    path('channel/<int:channel_id>', channel),
    path('return_profile_data/<int:_id>', return_profile_data),
    path('call_process', call_process),
    path('get_token/', get_token),
    path('get_user_data/', get_user_data),
    path('get_agora_sdk_data', get_agora_sdk_data),
    path('get_member/', get_member),
    path('add-friend/', friendRequest, name='friend-request')
]
