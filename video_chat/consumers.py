import json
from channels.generic.websocket import AsyncWebsocketConsumer
from .models import Profile, User, Channel, ChannelType, ChannelInfo, Message, Friendship, FriendRequestType
from .utils import find_current_profile, find_current_profile_with_username
from channels.db import database_sync_to_async

class ChatConsumer(AsyncWebsocketConsumer):
    """
    A class to handle WebSocket connections connected with text chates in channels.
    """

    async def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = f"chat_{self.room_name}"

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    @database_sync_to_async
    def create_and_get_profile(self, user_id: int, channel_id: int, message: str) -> Profile:
        """
        Makes async requests in database.

        Create a new record Message in data base and returns sender Profile.
        """
        
        profile = find_current_profile(user_id)
        channel = Channel.objects.get(id=channel_id)
        Message.objects.create(channel=channel, profile=profile, content=message)
        profile_name = profile.profile_name
        return profile_name

    async def receive(self, text_data):
        """
        Receives a data from the client through the Web Socket.

        Works with single particular type - chat.message.

        Calls the create_and_get_profile(self, user_id: int, channel_id: int, message: str) -> Profile
        and sends to group dictionary with keys: type of message, name of the sender profile, message body.
        """
        
        text_data_json = json.loads(text_data)
        user_id = text_data_json["user_id"]
        channel_id = text_data_json["channel_id"]
        message = text_data_json["message"]
        profile_name = await self.create_and_get_profile(user_id, channel_id, message)
        
        await self.channel_layer.group_send(
            self.room_group_name, {"type": "chat.message", "profile_name": profile_name, "message": message}
        )
    
    async def chat_message(self, event):
        """
        Processes the distribution of the recieve(self, text_data) method with type: chat.message.

        Sends to the client side JSON with following information: name of the sender profile, message body.
        """
            
        profile_name = event["profile_name"]
        message = event["message"]

        await self.send(text_data=json.dumps({"profile_name": profile_name, "message": message}))

class NotificationConsumer(AsyncWebsocketConsumer):
    """
    A class to handle WebSocket connections connected with notifications 
    about input messages from the channels.
    """

    async def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = f"notification_{self.room_name}"

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        """
        Receives a data from the client through the Web Socket.

        Works with different types.
        """
        
        text_data_json = json.loads(text_data)
        
        await self.channel_layer.group_send(
            self.room_group_name, text_data_json
        )
    
    async def notification_getmessage(self, event):
        """
        Processes the distribution of the recieve(self, text_data) method with type: notification.getmessage.

        Sends to the client side JSON with following information: name of the sender profile, 
        sender username, channel id which notification was taken from, message body.
        """
        
        sender_username = event["sender_username"]
        sender_profilename = event["sender_profilename"]
        message = event["message"]
        channel_id = event["channel_id"]
        #** db request.....

        await self.send(text_data=json.dumps({"type": 'message_notification',
                                              "sender_profilename": sender_profilename,
                                              "sender_username": sender_username,
                                              "channel_id": channel_id,
                                              "message": message
                                              }))
        
    @database_sync_to_async
    def create_notification_and_get_profile(self, sender_username: str) -> Profile:
        #** db request for notif
        return find_current_profile_with_username(sender_username)

        
    async def notification_incomingdialogcall(self, event):
        sender_username = event['sender_username']
        channel_id = event['channel_id']
        sender_profile = await self.create_notification_and_get_profile(sender_username)
        sender_profilename = sender_profile.profile_name

        await self.send(text_data=json.dumps({"type": 'incoming_dialog_call',
                                              "sender_username": sender_username,
                                              "sender_profilename": sender_profilename,
                                              "channel_id": channel_id
                                              }))
    
class FriendRequestConsumer(AsyncWebsocketConsumer):
    """
    A class to handle WebSocket connections connected with friend requestes 
    and conforming notifications.
    """

    async def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["friend_username"]
        self.room_group_name = f"friend_request_{self.room_name}"

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        """
        Receives a data from the client through the Web Socket.

        Works with different types.
        """
        
        text_data_json = json.loads(text_data)
        
        await self.channel_layer.group_send(
            self.room_group_name, text_data_json
        )

    async def friendrequest_verif(self, event):
        """
        Processes the distribution of the recieve(self, text_data) method with type: friendrequest.verif.

        Makes the attribute "target" with username only for owner of this WebSocket connection.

        The owner of the WebSocket connection - user which can only take 
        friend requestes trough this connection.
        """
        
        self.target = event["target"]
        print(f"verified target - {self.target}")

    @database_sync_to_async
    def get_profiles_data(self, sender_username, friend_username):
        """
        Makes async requests in database.

        Finds and returns names of the profiles of friend request sender (sender_username)
        and friend request receiver (friend_username).
        """

        sender_profile = find_current_profile_with_username(sender_username)
        sender_profilename = sender_profile.profile_name

        friend_profile = find_current_profile_with_username(friend_username)
        friend_profilename = friend_profile.profile_name

        return {'sender_profilename': sender_profilename, 'friend_profilename': friend_profilename}
    
    @database_sync_to_async
    def permit_friend_request(self, sender_username, friend_username):
        """
        Makes async requests in database.

        This method is calling by friendrequest_permit(self, sender_username, friend_username)
        method.

        Finds two profiles through sender_username and friend_username
        then check the existence of friend request from sender to receiver
        and from receiver to sender, after that permits existing records
        in database.
        """

        sender_profile = find_current_profile_with_username(sender_username)
        friend_profile = find_current_profile_with_username(friend_username)

        straight_friendship = Friendship.objects.get(sender=sender_profile, receiver=friend_profile)

        try:
            reverse_friendship = Friendship.objects.get(sender=friend_profile, receiver=sender_profile)
        except Friendship.DoesNotExist:
            reverse_friendship = None

        permitted_status_type = FriendRequestType.objects.get(id=3)

        if (straight_friendship.status_type != permitted_status_type):
            straight_friendship.status_type = permitted_status_type
            straight_friendship.save()

            if (reverse_friendship):
                if (reverse_friendship.status_type != permitted_status_type):
                    reverse_friendship.status_type = permitted_status_type
                    reverse_friendship.save()
                else:
                    print(f'*SERVER RESPONSE: Error while permitting friend request \
                          from reverse_friendship: sender_username: {sender_username} \
                          friend_username: {friend_username}. \
                          reverse friendship request is already permitted')
                    
                    raise Exception("Already permitted by other user, check consumers.py")

            try:
                existing_channel = Channel.objects \
                    .filter(channel_infos__profile=sender_profile, channel_type=2) \
                    .get(channel_infos__profile=friend_profile)
                channel_id = existing_channel.id
            except Channel.DoesNotExist:
                new_channel_name = str(sender_username) + '____' + str(friend_username)
                DIALOG_TYPE = 2
                channel_dialog_type = ChannelType.objects.get(id=DIALOG_TYPE)
                new_channel = Channel.objects.create(channel_name=new_channel_name, channel_type=channel_dialog_type)
                ChannelInfo.objects.create(channel=new_channel, profile=sender_profile)
                ChannelInfo.objects.create(channel=new_channel, profile=friend_profile)
                channel_id = new_channel.id
                print(f'*SERVER RESPONSE: Channel was created: {new_channel}')

            print(f'*SERVER RESPONSE: Successfully permitted friend request \
                  from sender_username: {sender_username} to friend_username: {friend_username}')
            
            return {'status': 'success', 'channel_id': channel_id}
        else:
            print(f'*SERVER RESPONSE: Error while permitting friend request \
                          from straight_friendship: sender_username: {sender_username} \
                          friend_username: {friend_username}. \
                          straight friendship request is already permitted')
            
            raise Exception("Already permitted, check consumers.py")
        
    @database_sync_to_async
    def decline_friend_request(self, sender_username, friend_username):
        """
        Makes async requests in database.

        This method is calling by friendrequest_decline(self, sender_username, friend_username)
        method.

        Finds two profiles through sender_username and friend_username
        then check the existence of friend request from sender to receiver,
        after that declines existing record in database.
        """

        sender_profile = find_current_profile_with_username(sender_username)
        friend_profile = find_current_profile_with_username(friend_username)

        straight_friendship = Friendship.objects.get(sender=sender_profile, receiver=friend_profile)

        declined_status_type = FriendRequestType.objects.get(id=2)
        
        if (straight_friendship.status_type != declined_status_type):
            straight_friendship.status_type = declined_status_type
            straight_friendship.save()

            print(f'*SERVER RESPONSE: Successfully declined friend request \
                  from sender_username: {sender_username} to friend_username: {friend_username}')
            return 'success'
        else:
            print(f'*SERVER RESPONSE: Error while declining friend request \
                          from sender_username: {sender_username} to \
                          friend_username: {friend_username}')
            
            raise Exception("Already declined, check consumers.py")

    # Если получилось установить таргет - значит, это получатель запроса на добавление в друзья.
    # В противном случае возникнет управляемое исключение об отсутствии атрибута self.target
    async def friendrequest_sendrequest(self, event):
        """
        This method processes friend request from sender user to receiver user.

        Parses sender username and receiver username from the sent data from the client
        through the WebSocket connection.

        "target" attribute exists only for connection owner, so this method checkes
        it it called for the target.

        If it called for the receiver, then user will get message
        with friend request information.

        Other users will be passed.
        """

        sender_username = event["sender_username"]
        friend_username = event["friend_username"]

        try:
            if (self.target == friend_username):
                print(f"*SERVER RESPONSE: Sent request only to {self.target}")
                profiles_data = await self.get_profiles_data(sender_username, friend_username)
                sender_profilename = profiles_data['sender_profilename']
                friend_profilename = profiles_data['friend_profilename']

                await self.send(text_data=json.dumps({"type": 'request',
                                                      "sender_username": sender_username,
                                                      "sender_profilename": sender_profilename,
                                                      "friend_username": friend_username,
                                                      "friend_profilename": friend_profilename
                                                      }))
        except AttributeError:
            print(f'*SERVER RESPONSE: \
                  Deny request for none target: {sender_username}, when the target: {friend_username}')
    
    async def friendrequest_permit(self, event):
        """
        This method processes the confirmation of the friend request
        from sender user to receiver user.

        Parses sender username and receiver username from the sent data from the client
        through the WebSocket connection.

        After that premits friend request and sends different messages for receiver user
        and sender user.
        """

        sender_username = event["sender_username"]
        friend_username = event["friend_username"]
        
        sender_profilename = event['sender_profilename']
        friend_profilename = event['friend_profilename']

        isTarget = True

        try:
            if (self.target == friend_username):
                print('*SERVER RESPONSE: Processed confirmation only from target')
        except AttributeError:
            print(f'*SERVER RESPONSE: Deny processing in confirmation \
                  for none target: {sender_username}, when the target: {friend_username}')
            isTarget = False

        if (isTarget):

            try:
                response = await self.permit_friend_request(sender_username, friend_username)
                status = response['status']
                channel_id = response['channel_id']
            except:
                status = 'failure'
                channel_id = -1

            await self.send(text_data=json.dumps({"type": 'permitted',
                                                "status": status,
                                                "channel_id": channel_id,
                                                "sender_username": sender_username,
                                                "friend_username": friend_username,
                                                "sender_profilename": sender_profilename,
                                                "friend_profilename": friend_profilename
                                                }))
        else:
            print(f'*SERVER RESPONSE: \
                  Sending signal about successfull permitting friend request to none target: \
                  {sender_username}, when the receiver is {friend_username}')
            
            await self.send(text_data=json.dumps({"type": 'permitted',
                                                  "state": 'success',
                                                  'sender_username': sender_username
                                                }))
            
    async def friendrequest_readytorefresh(self, event):
        """
        This method is called after friend request confirmation.

        Sender user after receiving 'success' message from the confirmation
        sends through the WebSocket connection signal 
        that he is ready to refresh his friend list.

        This method is used because sender user should wait until
        permit_friend_request(self, sender_username, friend_username) method
        processed the database record.
        """

        sender_username = event["sender_username"]
        friend_username = event["friend_username"]

        print(f'*SERVER RESPONSE: Sending signal about ready state to parse new friend list data \
              for sender: {sender_username} from receiver: {friend_username}')

        isTarget = True

        try:
            if (self.target == friend_username):
                print('*SERVER RESPONSE: Processed readytorefresh only from target')
        except AttributeError:
            print(f'*SERVER RESPONSE: Deny processing in readytorefresh \
                  for none target: {sender_username}, when the target: {friend_username}')
            isTarget = False

        if (isTarget):
            await self.send(text_data=json.dumps({"type": "refreshready",
                                                  "state": "success",
                                                  "sender_username": sender_username
                                                  }))
    
    async def friendrequest_dataready(self, event):
        """
        This method is called after the friend request data in database changed.

        After receiver user got the signal from sender user through
        friendrequest_readytorefresh(self, event) method and
        the friend request record in database refreched
        this method will send signal to sender user about ready state of data.

        After this method called sender user on the client side will be able to parse
        new friend list data.
        """
        
        sender_username = event["sender_username"]
        friend_username = event["friend_username"]

        print(f'*SERVER RESPONSE: Sending signal about ready state of data for the new friend list \
              for sender: {sender_username} from receiver: {friend_username}')
        
        isTarget = True

        try:
            if (self.target == friend_username):
                print('*SERVER RESPONSE: Processed dataready only from target')
        except AttributeError:
            print(f'*SERVER RESPONSE: Deny processing in dataready \
                  for none target: {sender_username}, when the target: {friend_username}')
            isTarget = False

        if (not isTarget):
            await self.send(text_data=json.dumps({"type": 'data_ready',
                                                    # "status": status,
                                                    "sender_username": sender_username,
                                                    "friend_username": friend_username
                                                    }))
    
    async def friendrequest_decline(self, event):
        """
        This method processes the abolition of the friend request
        from sender user to receiver user.

        Parses sender username and receiver username from the sent data from the client
        through the WebSocket connection.

        After that declines friend request and sends different messages for receiver user
        and sender user.
        """

        sender_username = event["sender_username"]
        friend_username = event["friend_username"]
        
        sender_profilename = event['sender_profilename']
        friend_profilename = event['friend_profilename']
        
        isTarget = True

        try:
            if (self.target == friend_username):
                print('*SERVER RESPONSE: Processed abolition only from target')
        except AttributeError:
            print(f'*SERVER RESPONSE: Deny processing in abolition \
                  for none target: {sender_username}, when the target: {friend_username}')
            isTarget = False
        
        if (isTarget):
            
            try:
                status = await self.decline_friend_request(sender_username, friend_username)
            except:
                status = 'failure'

            await self.send(text_data=json.dumps({"type": 'declined',
                                                "status": status,
                                                "sender_username": sender_username,
                                                "friend_username": friend_username,
                                                "sender_profilename": sender_profilename,
                                                "friend_profilename": friend_profilename
                                                }))
        else:
            print('*SERVER RESPONSE: \
                  Sending signal about successfull declining friend request to non target')
            
            await self.send(text_data=json.dumps({"type": 'declined',
                                                  "state": 'success',
                                                  'sender_username': sender_username
                                                }))
