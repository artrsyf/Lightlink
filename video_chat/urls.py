from django.urls import path
from video_chat.views import *

urlpatterns = [
    path('Home', index, name='WebChatHome'),
    path('channel/<int:channel_id>', channel),
    path('return_profile_data/<int:_id>', return_profile_data),
    path('get_token/', get_token),
    path('get_user_data/', get_user_data),
    path('get_agora_sdk_data', get_agora_sdk_data),
    path('get_member/', get_member),
    path('add-friend/', friendRequest, name='friend-request'),
    path('get-member-friends/<int:user_id>', getMemberFriends),
    path('get-member-channels-ids/<int:user_id>', getMemberChannelsIds),
    path('get-channel-last-message-info/<int:channel_id>', getChannelLastMessageInfo),
    path('get-member-private-messages-list/<int:user_id>', getMemberPrivateMessagesList),
    path('get-channel-data/<int:channel_id>', getChannelData),
    path('get-channel-meta/<int:channel_id>', getChannelMeta),
    path('edit-profile', editProfile),
    path('get-member-notifications/<int:user_id>', getMemberNotifications)
]
