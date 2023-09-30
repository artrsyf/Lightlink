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

class FriendRequestConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["friend_username"]
        self.room_group_name = f"friend_request_{self.room_name}"

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)


    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        
        await self.channel_layer.group_send(
            self.room_group_name, text_data_json
        )

    # Метод для верификации таргета запроса
    async def friendrequest_verif(self, event):
        self.target = event["target"]
        print(f"verified target - {self.target}")

    @database_sync_to_async
    def get_profiles_data(self, sender_username, friend_username):
        sender_user = User.objects.get(username=sender_username)
        sender_profile = Profile.objects.get(user = sender_user)
        sender_profilename = sender_profile.profile_name

        friend_user = User.objects.get(username=friend_username)
        friend_profile = Profile.objects.get(user=friend_user)
        friend_profilename = friend_profile.profile_name

        return {'sender_profilename': sender_profilename, 'friend_profilename': friend_profilename}

    # Если получилось установить таргет - значит, это получатель запроса на добавление в друзья.
    # В противном случае возникнет управляемое исключение об отсутствии атрибута self.target
    async def friendrequest_sendrequest(self, event):
        sender_username = event["sender_username"]
        friend_username = event["friend_username"]
        try:
            if (self.target == friend_username):
                print(f"Sent request only to {self.target}")
                profiles_data = await self.get_profiles_data(sender_username, friend_username)
                sender_profilename = profiles_data['sender_profilename']
                friend_profilename = profiles_data['friend_profilename']

                await self.send(text_data=json.dumps({"sender_username": sender_username,
                                                      "sender_profilename": sender_profilename,
                                                      "friend_username": friend_username,
                                                      "friend_profilename": friend_profilename
                                                      }))
        except AttributeError:
            print(f'Deny request for none target: {sender_username}, when the target: {friend_username}')
