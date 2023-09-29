import json
from channels.generic.websocket import AsyncWebsocketConsumer
from .models import Profile, User, Channel, Message
from channels.db import database_sync_to_async

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = f"chat_{self.room_name}"

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    @database_sync_to_async
    def create_and_get_profile(self, user_id, channel_id, message):
        user = User.objects.get(id=user_id)
        profile = Profile.objects.get(user=user)
        channel = Channel.objects.get(id=channel_id)
        Message.objects.create(channel=channel, profile=profile, content=message)
        profile_name = profile.profile_name
        return profile_name

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        user_id = text_data_json["user_id"]
        channel_id = text_data_json["channel_id"]
        message = text_data_json["message"]
        profile_name = await self.create_and_get_profile(user_id, channel_id, message)
        
        await self.channel_layer.group_send(
            self.room_group_name, {"type": "chat.message", "profile_name": profile_name, "message": message}
        )
    
    async def chat_message(self, event):
        profile_name = event["profile_name"]
        message = event["message"]

        await self.send(text_data=json.dumps({"profile_name": profile_name, "message": message}))