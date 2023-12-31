from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/chat/(?P<room_name>\w+)/$", consumers.ChatConsumer.as_asgi()),
    re_path(r"ws/service/friend-request/(?P<friend_username>\w+)/$", consumers.FriendRequestConsumer.as_asgi()),
    re_path(r"ws/service/notification/(?P<room_name>\w+)/$", consumers.NotificationConsumer.as_asgi())
]