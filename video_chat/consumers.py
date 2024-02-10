import json
from channels.generic.websocket import AsyncWebsocketConsumer, WebsocketConsumer
from .models import Profile, User, Channel, ChannelType, ChannelInfo, \
    Message, Friendship, FriendRequestType, Notification, NotificationType, NotificationStatus
from .utils import Queries, clearCache
from channels.db import database_sync_to_async
from django.db.models import Q
from pyforkurento import client
from asgiref.sync import async_to_sync, sync_to_async
import asyncio
import random

import redis
import environ



import websocket

def customProcessOffer(ep_id, session_id, session_desc_offer):
    kurento_conn = websocket.WebSocket()
    kurento_conn.connect("ws://lightlink_kurento:8888/kurento")
    payload = {
        "jsonrpc": "2.0",
        "id": random.randint(1, 100_000),
        "method": "invoke",
        "params": {
            "object": f"{ep_id}",
            "operation": "processOffer",
            "operationParams":{
                "offer": session_desc_offer
            },
            "sessionId": f"{session_id}"
        }
    }
    kurento_conn.send(json.dumps(payload))
    return kurento_conn.recv()

def printLocalDescr(ep_id, session_id):
    kurento_conn = websocket.WebSocket()
    kurento_conn.connect("ws://lightlink_kurento:8888/kurento")
    payload = {
        "jsonrpc": "2.0",
        "id": random.randint(1, 100_000),
        "method": "invoke",
        "params": {
            "object": f"{ep_id}",
            "operation": "getRemoteSessionDescriptor",
            "sessionId": f"{session_id}"
        }
    }
    kurento_conn.send(json.dumps(payload))
    print(kurento_conn.recv())

env = environ.Env()
environ.Env().read_env("../lightlink/")

redis_adapter = redis.Redis(host=env("REDIS_HOST"),
                            port=env("REDIS_PORT"),
                            db=0,
                            decode_responses=True)


kurento_client = None

class VideoConferenceConsumer(WebsocketConsumer):
    rooms_data = {}
    users = []

    def connect(self):
        global kurento_client
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = f"conf_{self.room_name}"
        self.user_id = self.scope["user"].id
        VideoConferenceConsumer.users.append(self.user_id)

        async_to_sync(self.channel_layer.group_add)(self.room_group_name, self.channel_name)
        self.accept()

        if kurento_client is None:
            kurento_client = client.KurentoClient("ws://lightlink_kurento:8888/kurento") # make through .env
            print("Successfully created Kurento Client")
        
        if self.room_name not in VideoConferenceConsumer.rooms_data:
            VideoConferenceConsumer.rooms_data[self.room_name] = {}
        self.room_data = VideoConferenceConsumer.rooms_data[self.room_name]

        if "media_pipeline" not in self.room_data:
            self.room_data["media_pipeline"] = kurento_client.create_media_pipeline()
            self.room_data["web_rtc_endpoints"] = {}
            print(f"Created Media Pipeline for room-{self.room_name}")
        self.media_pipeline = self.room_data["media_pipeline"]

        self.all_endpoints = self.room_data["web_rtc_endpoints"]
        self.send_endpoint = self.media_pipeline.add_endpoint("WebRtcEndpoint")
        self.all_endpoints[self.send_endpoint.elem_id] = self.send_endpoint
        self.receive_endpoints = {}
        print(f"Create SendEndPoint in room-{self.room_name} for user-{self.user_id}")

        

        new_user_distribution_data = {"type": "video_conference.handleNewUserJoined",
         "new_user_id": self.user_id,
         "new_user_source_endpoint_id": self.send_endpoint.elem_id
        }
        print(new_user_distribution_data)
        async_to_sync(self.channel_layer.group_send)(self.room_group_name, new_user_distribution_data)
    
    def disconnect(self, close_code):
        # VideoConferenceConsumer.users.remove(self.user_id)
        # print(f"diconn for user-{self.user_id}")
        # send_end_point_id = self.send_endpoint.elem_id
        # self.send_endpoint._release()
        # del self.all_endpoints[send_end_point_id]
        # del self.send_endpoint
        async_to_sync(self.channel_layer.group_discard)(self.room_group_name, self.channel_name)    
    
    def receive(self, text_data):
        text_data_json = json.loads(text_data)
        
        if text_data_json["type"] == 'video_conference.handleNewUserJoined' or text_data_json["type"] == 'video_conference.handleExistingUsersMedia':
            async_to_sync(self.channel_layer.group_send)(
                self.room_group_name, text_data_json
            )
        else:
            async_to_sync(self.channel_layer.send)(self.channel_name, text_data_json)

    def video_conference_handleIceCandidate(self, event):
        handle_type = event["endpoint_type"]
        ice_candidate = event["candidate"]
        if handle_type == "sendEndPoint":
            self.send_endpoint.add_ice_candidate(ice_candidate)
        elif handle_type == "receiveEndPoint":
            remote_user_id = int(event["remote_user_id"])
            if self.user_id == remote_user_id: return
            self.receive_endpoints[remote_user_id].add_ice_candidate(ice_candidate)
        else:
            print(f"Unrecognized handle_type in video_conference_handleIceCandidate: {handle_type}")
            return
    
    def sendIceCandidate(self, response):
        ice_candidate = response["payload"]["candidate"]
        triggered_endpoint_id = response['subscriber']
        if self.send_endpoint.elem_id == triggered_endpoint_id:
            on_ice_candidate_data = {"type": "handleIceCandidate",
                                     "endpoint_type": "sendEndPoint",
                                     "candidate": ice_candidate
                                    }
            self.send(text_data=json.dumps(on_ice_candidate_data))
        else:
            for remote_user_id, receive_endpoint in self.receive_endpoints.items():
                if receive_endpoint.elem_id == triggered_endpoint_id:
                    on_ice_candidate_data = {"type": "handleIceCandidate",
                                             "endpoint_type": "receiveEndPoint",
                                             "remote_user_id": remote_user_id,
                                             "candidate": ice_candidate
                                            }
                    self.send(text_data=json.dumps(on_ice_candidate_data))
                    break
            else:
                print("fuck")
                # if self.user_id == 1:
                #     print(f"/// Stats for user 1!!! local: {self.send_endpoint.elem_id};;; remote: {self.receive_endpoints[0].elem_id}...")
                # else:
                #     print(f"/// Stats for user 2!!! local: {self.send_endpoint.elem_id};;; remote: {self.receive_endpoints[1].elem_id}...")
    
    def video_conference_handleSdpOffer(self, event):
        handle_type = event["endpoint_type"]
        win_incoming_sdp_offer = event["sdp_offer"]
        unix_incoming_sdp_offer = win_incoming_sdp_offer.replace("\r\n", "\n")
        if handle_type == "sendEndPoint":
            print("Got: ", unix_incoming_sdp_offer)
            print("Info before sdp process: ", printLocalDescr(self.send_endpoint.elem_id, self.send_endpoint.session_id))
            # outcoming_sdp_answer = self.send_endpoint.process_offer(unix_incoming_sdp_offer)
            outcoming_sdp_answer = customProcessOffer(self.send_endpoint.elem_id, self.send_endpoint.session_id, unix_incoming_sdp_offer)
            outcoming_sdp_answer = json.loads(outcoming_sdp_answer)["result"]["value"]
            print(f"Holu - {self.send_endpoint}")
            print(outcoming_sdp_answer)
            sdp_answer_data = {"type": "handleSdpAnswer",
                               "endpoint_type": handle_type,
                               "sdp_anwer": outcoming_sdp_answer
                               }
            # Sending SDP Answer
            print("Info after sdp process: ", printLocalDescr(self.send_endpoint.elem_id, self.send_endpoint.session_id))
            self.send(text_data=json.dumps(sdp_answer_data))
            self.send_endpoint.add_event_listener("OnIceCandidate", self.sendIceCandidate)
            self.send_endpoint.gather_ice_candidates()
            print(f"ICESSS with endpoint id: {self.send_endpoint.elem_id} for user-{self.user_id}")
            
        elif handle_type == "receiveEndPoint":
            remote_user_id = int(event["remote_user_id"])
            if remote_user_id == self.user_id: return
            print("offer")
            outcoming_sdp_answer = self.receive_endpoints[remote_user_id].process_offer(unix_incoming_sdp_offer)
            sdp_answer_data = {"type": "handleSdpAnswer",
                               "endpoint_type": handle_type,
                               "remote_user_id": remote_user_id,
                               "sdp_anwer": outcoming_sdp_answer
                               }
            # Sending SDP Answer
            self.send(text_data=json.dumps(sdp_answer_data))
            self.receive_endpoints[remote_user_id].add_event_listener("OnIceCandidate", self.sendIceCandidate)
            self.receive_endpoints[remote_user_id].gather_ice_candidates()
            print(f"ICESSS with endpoint id: {self.receive_endpoints[remote_user_id].elem_id} for user-{self.user_id}")
        else:
            print(f"Unrecognized handle_type in video_conference_handleSdpOffer: {handle_type}")
            return
    
    def video_conference_handleNewUserJoined(self, event):
        new_user_id = event["new_user_id"]
        print(f"Delete it, should be true: {type(new_user_id) == int}")
        if self.user_id == new_user_id:
            return
        
        self.receive_endpoints[new_user_id] = self.media_pipeline.add_endpoint("WebRtcEndpoint")
        self.all_endpoints[self.receive_endpoints[new_user_id].elem_id] = self.receive_endpoints[new_user_id]
        new_user_source_endpoint_id = event["new_user_source_endpoint_id"]
        new_user_source_endpoint = self.all_endpoints[new_user_source_endpoint_id]
        new_user_source_endpoint.connect(self.receive_endpoints[new_user_id])

        # Starting connection for new receive endpoint
        self.send(text_data=json.dumps({
			"type": "waitingForOffer",
			"payload_type": "receiveEndPoint",
            "remote_user_id": new_user_id
   		}))

        # Sending existing source endpoints of each participant
        new_user_acknowledgement_data = {"type": "video_conference.handleExistingUsersMedia",
         "new_user_id": new_user_id,
         "existing_user_id": self.user_id,
         "existing_user_source_endpoint_id": self.send_endpoint.elem_id
        }
        async_to_sync(self.channel_layer.group_send)(self.room_group_name, new_user_acknowledgement_data)

    def video_conference_handleExistingUsersMedia(self, event):
        new_user_id = event["new_user_id"]
        print(f"Delete it, should be true: {type(new_user_id) == int}")
        if self.user_id != new_user_id:
            return
        
        existing_user_id = event["existing_user_id"]
        self.receive_endpoints[existing_user_id] = self.media_pipeline.add_endpoint("WebRtcEndpoint")
        self.all_endpoints[self.receive_endpoints[existing_user_id].elem_id] = self.receive_endpoints[existing_user_id]
        existing_user_source_endpoint_id = event["existing_user_source_endpoint_id"]
        existing_user_source_endpoint = self.all_endpoints[existing_user_source_endpoint_id]
        existing_user_source_endpoint.connect(self.receive_endpoints[existing_user_id])

        # Starting connection for new receive endpoint
        self.send(text_data=json.dumps({
			"type": "waitingForOffer",
			"payload_type": "receiveEndPoint",
            "remote_user_id": existing_user_id
   		}))


cli = None
pipeline = None
go_remote = False
candidates = []
endPoints = set()
class MediaConsumer(WebsocketConsumer):
    def connect(self):
        global endPoints
        global cli, pipeline
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = f"media_{self.room_name}"

        async_to_sync(self.channel_layer.group_add)(self.room_group_name, self.channel_name)
        self.user_id = self.scope["user"].id
        new_user_data = {"type": "media.new_user", "user_id": self.user_id}
        async_to_sync(self.channel_layer.group_send)(self.room_group_name, new_user_data)

        self.accept()

        if cli is None:
            cli = client.KurentoClient("ws://lightlink_kurento:8888/kurento")
            print("create cli")

        if pipeline is None:
            pipeline = cli.create_media_pipeline()
            endPoints = set()
            print("create media pipeline")

        self.remote_rtc = None
        self.rtc = pipeline.add_endpoint("WebRtcEndpoint")
        endPoints.add(self.rtc)
        print(f"create endpoint for user: {self.user_id}")
        # self.rtc.connect()

    def media_new_user(self, event):
        global endPoints
        if self.user_id != int(event["user_id"]):
            print(f"sent new user event about user - {event['user_id']} to user_{self.user_id}")
            print('Got endpoints: ', len(endPoints))
            endPoints = list(endPoints)
            endPoints[0].connect(endPoints[1])
            endPoints[1].connect(endPoints[0])
            endPoints = set(endPoints)
            self.send(text_data=json.dumps({"id": "newUser", "user_id": event["user_id"]}))

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(self.room_group_name, self.channel_name)

    def sendICE(self, resp):
        ice = resp["payload"]["candidate"]
        print('Got ice')
        print(resp['subscriber'])
        print(self.rtc.elem_id)
        print(resp['subscriber'] == self.rtc.elem_id)
        text_data = {"type": "media.flood_ice", "payload": ice}
        async_to_sync(self.channel_layer.group_send)(self.room_group_name, text_data)

    def media_flood_ice(self, event):
        ice = event["payload"]
        print(f"Sent new ice on client of user_{self.user_id}")
        self.send(text_data=json.dumps({"id": "iceCandidate", "payload": ice}))

    def media_send_answer(self, event):
        if self.user_id == int(event["to_user_id"]):
            print(f"Sent sdp answer from remote_{event['from_user_id']} to local_{event['to_user_id']}")
            self.send(text_data=json.dumps({
                "id": "sdpAnswer",
                "local_user_id": event["to_user_id"],
                "remote_user_id": event["from_user_id"],
                "payload": event["payload"]
            }))

    def media_process_answer(self, event):
        offer = event["payload"]
        from_user_id = event["from_user_id"]
        to_user_id = event["to_user_id"]

        if self.user_id == int(to_user_id):
            if from_user_id == to_user_id:
                kms_sdp = self.rtc.process_offer(offer)
                print('1', kms_sdp)
                self.rtc.add_event_listener("OnIceCandidate", self.sendICE)
                self.rtc.gather_ice_candidates()
            else:
                print("create remote endpoint for", self.user_id)
                self.remote_rtc = pipeline.add_endpoint("WebRtcEndpoint")
                self.remote_rtc.connect()
                kms_sdp = self.remote_rtc.process_offer(offer)
                for i in candidates:
                    if int(i["to_user_id"]) == self.user_id and int(i["from_user_id"]) != self.user_id:
                        self.remote_rtc.add_ice_candidate(i["candidate"])
                        print("remote ice")
                    else: print("Shit happens")
                print('2', kms_sdp)
                self.remote_rtc.add_event_listener("OnIceCandidate", self.sendICE)
                self.remote_rtc.gather_ice_candidates()
                print(self.remote_rtc)

            text_data = {
                "type": 'media.send_answer',
                "id": "sdpAnswer",
                "from_user_id": to_user_id,
                "to_user_id": from_user_id,
                "payload": kms_sdp
            }
            print(f"Making answer from remote_{to_user_id} to local_{from_user_id}")
            async_to_sync(self.channel_layer.group_send)(self.room_group_name, text_data)

    def receive(self, text_data):
        global candidates
        data = json.loads(text_data)
        action = data["id"]
        print(data)

        if action == "processOffer":
            text_data = {
                "type": "media.process_answer",
                "from_user_id": data["from_user_id"],
                "to_user_id": data["to_user_id"],
                "payload": data["payload"]
            }
            async_to_sync(self.channel_layer.group_send)(self.room_group_name, text_data)

        elif action == "addIce":
            candidate = data["payload"]
            from_user_id = data["from_user_id"]
            to_user_id = data["to_user_id"]
            print(f"found user_{from_user_id} to user_{to_user_id}", candidate)
            if int(to_user_id) == self.user_id and int(from_user_id) == self.user_id:
                self.rtc.add_ice_candidate(candidate)
                print("local ice")
            else:
                candidates.append({"candidate": candidate, "to_user_id": to_user_id, "from_user_id": from_user_id})
                print("collect for remote")

        elif action == "error" or action == "stop":
            print("Something weird happened in the frontend")
class WebRtcConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = f"webrtc_{self.room_name}"

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        
        self.user_id = self.scope["user"].id

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
    
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        
        await self.channel_layer.group_send(
            self.room_group_name, text_data_json
        )

    async def webrtc_share_ice_candidate(self, event):
        sender_user_id = event["sender_user_id"]
        ice_candidate = event["ice_candidate"]

        if sender_user_id == self.user_id:
            return
        
        await self.send(text_data=json.dumps({"type": "NewIceCandidate",
                                              "iceCandidate": ice_candidate
                                              }))


    async def webrtc_peer_connection(self, event):
        head = event["head"]
        sender_user_id = event["sender_user_id"]
        body = event["body"]
        if int(sender_user_id) == self.user_id:
            return

        if head == "RTCPeerConnectionOffer":
            print(f"making peer conection offer from {sender_user_id}")
            await self.send(text_data=json.dumps({"type": "RTCPeerConnectionOffer",
                                              "body": body
                                              }))

        elif head == "RTCPeerConnectionAnswer":
            print(f"making peer conection answer from {sender_user_id}")
            await self.send(text_data=json.dumps({"type": "RTCPeerConnectionAnswer",
                                              "body": body
                                              }))

class ChatConsumer(AsyncWebsocketConsumer):
    """
    A class to handle WebSocket connections connected with text chates in channels.
    """

    async def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = f"chat_{self.room_name}"
        self.user_id = self.scope["user"].id

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    @database_sync_to_async
    def create_and_get_message(self, user_id: int, channel_id: int, message: str) -> Message:
        """
        Makes async requests in database.

        Create a new record Message in data base and returns it.
        """
        
        profile = Queries.getCurrentProfileByUserId(user_id, False)
        channel = Channel.objects.get(id=channel_id)
        new_message = Message.objects.create(channel=channel, profile=profile, content=message)
        clearCache(f'cache__{channel_id}__channel_messages', 
                   f'cache__{channel_id}__channel_data_with_serialized_messages')
        return new_message

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
        new_message = await self.create_and_get_message(user_id, channel_id, message)
        serialized_message = new_message.to_dict()
        
        await self.channel_layer.group_send(
            self.room_group_name, {"type": "chat.message", "serialized_message": serialized_message}
        )
    
    async def chat_message(self, event):
        """
        Processes the distribution of the recieve(self, text_data) method with type: chat.message.

        Sends to the client side JSON with serialized Message infromation (method to_dict() in models.py).
        """
            
        serialized_message = event["serialized_message"]
        clearCache(f'cache__{self.user_id}__private_message_list')

        await self.send(text_data=json.dumps({"serialized_message": serialized_message}))

class NotificationConsumer(AsyncWebsocketConsumer):
    """
    A class to handle WebSocket connections connected with notifications 
    about input messages from the channels.
    """

    async def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = f"notification_{self.room_name}"
        self.user = self.scope["user"]
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
        sender_profile_avatar_url = event["sender_profile_avatar_url"]
        message = event["message"]
        channel_id = event["channel_id"]
        #** db request.....

        await self.send(text_data=json.dumps({"type": "message_notification",
                                              "sender_profilename": sender_profilename,
                                              "sender_profile_avatar_url": sender_profile_avatar_url,
                                              "sender_username": sender_username,
                                              "channel_id": channel_id,
                                              "message": message
                                              }))
        
    @database_sync_to_async
    def create_notification_and_get_profile(self, sender_username: str) -> Profile:
        #** db request for notif
        return Queries.getCurrentProfileByUsername(sender_username, False)
    
    @database_sync_to_async
    def create_missing_call_notification(self, declined_username: str, channel_id: int) -> None:
        declined_profile = Queries.getCurrentProfileByUsername(declined_username, False)
        channel = Channel.objects.get(id=channel_id)
        if channel.channel_type.id == 2:
            sender_profile = ChannelInfo.objects.filter(Q(channel=channel) & ~Q(profile=declined_profile)).last().profile
            MISSING_CALL_CLOSED_NOTIFICATION_STATUS = NotificationStatus.objects.get(id=2)
            MISSING_CALL_NOTIFICATION_TYPE = NotificationType.objects.get(id=1)
            missing_call_notification = Notification.objects\
                .create(notification_type=MISSING_CALL_NOTIFICATION_TYPE, 
                        owner_profile=declined_profile, 
                        sender_profile=sender_profile, 
                        notification_status=MISSING_CALL_CLOSED_NOTIFICATION_STATUS)
        else:
            return
            # process for multi user channel


    async def notification_incomingdialogcall(self, event):
        sender_username = event["sender_username"]
        channel_id = event["channel_id"]
        sender_profile = await self.create_notification_and_get_profile(sender_username)
        sender_profilename = sender_profile.profile_name
        sender_profilename_avatar_url = sender_profile.profile_avatar.url

        await self.send(text_data=json.dumps({"type": "incoming_dialog_call",
                                              "sender_username": sender_username,
                                              "sender_profilename": sender_profilename,
                                              "sender_profilename_avatar_url": sender_profilename_avatar_url,
                                              "channel_id": channel_id
                                              }))
        
    async def notification_calldecline(self, event):
        status = event["status"]
        declined_username = event["declined_username"]
        declined_profilename = event["declined_profilename"]
        channel_id = event["channel_id"]
        if status == "timeout" and self.user.username == declined_username:
            await self.create_missing_call_notification(declined_username, channel_id)

        await self.send(text_data=json.dumps({"type": "call_declining",
                                              "sender_username": declined_username,
                                              "sender_profilename": declined_profilename,
                                              "channel_id": channel_id
                                              }))
    
class FriendRequestConsumer(AsyncWebsocketConsumer):
    """
    A class to handle WebSocket connections connected with friend requestes 
    and conforming notifications.
    
    Define witch user owns the Consumer object.
    """

    async def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["friend_username"]
        self.room_group_name = f"friend_request_{self.room_name}"
        self.user_id = self.scope["user"].id
        self.username = self.scope["user"].username

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

        Makes the attribute "target" with username of receiver and sets this value in
        redis db with the room_group_name key.

        The owner of the WebSocket connection - user which can only take 
        friend requestes trough this connection.
        """
        
        target = event["target"]
        if self.room_name == target:
            redis_adapter.set(self.room_group_name, target)
            print(f"*SERVER RESPONSE: Verified target - {target}")
        else:
            print(f"*SERVER RESPONSE: Unexpected detour from user with username {target}")

    @database_sync_to_async
    def get_profiles_data(self, sender_username, friend_username):
        """
        Makes async requests in database.

        Finds and returns names of the profiles of friend request sender (sender_username)
        and friend request receiver (friend_username).
        """

        sender_profile = Queries.getCurrentProfileByUsername(sender_username, False)
        sender_profilename = sender_profile.profile_name

        friend_profile = Queries.getCurrentProfileByUsername(friend_username, False)
        friend_profilename = friend_profile.profile_name

        return {"sender_profilename": sender_profilename, "friend_profilename": friend_profilename}
    
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

        Also this method closes existing notifications connected with found
        friend request records.
        """

        sender_profile = Queries.getCurrentProfileByUsername(sender_username, False)
        friend_profile = Queries.getCurrentProfileByUsername(friend_username, False)

        straight_friendship = Friendship.objects.get(sender=sender_profile, receiver=friend_profile)

        try:
            reverse_friendship = Friendship.objects.get(sender=friend_profile, receiver=sender_profile)
        except Friendship.DoesNotExist:
            reverse_friendship = None

        permitted_status_type = FriendRequestType.objects.get(id=3)

        if (straight_friendship.status_type != permitted_status_type):
            straight_friendship.status_type = permitted_status_type
            straight_friendship.save()

            # Close friend request notification
            FRIEND_REQUEST_NOTIFICATION_TYPE = NotificationType.objects.get(id=2)
            FRIEND_REQUEST_OPENED_NOTIFICATION_STATUS = NotificationStatus.objects.get(id=1)
            FRIEND_REQUEST_CLOSED_NOTIFICATION_STATUS = NotificationStatus.objects.get(id=2)

            existing_notifications = \
                Notification.objects.filter(owner_profile=friend_profile, 
                                            sender_profile=sender_profile,
                                            notification_status=FRIEND_REQUEST_OPENED_NOTIFICATION_STATUS, 
                                            notification_type=FRIEND_REQUEST_NOTIFICATION_TYPE)
            if not existing_notifications.exists():
                print("*SERVER RESPONSE: Notifications do not exist")

            for existing_notification in existing_notifications:
                existing_notification.notification_status = FRIEND_REQUEST_CLOSED_NOTIFICATION_STATUS
                existing_notification.save()

            if (reverse_friendship):
                if (reverse_friendship.status_type != permitted_status_type):
                    reverse_friendship.status_type = permitted_status_type
                    reverse_friendship.save()
                else:
                    print("*SERVER RESPONSE: Error while permitting friend request"
                          f"from reverse_friendship: sender_username: {sender_username}"
                          f"friend_username: {friend_username}."
                          "reverse friendship request is already permitted")
                    
                    raise Exception("Already permitted by other user, check consumers.py")

            try:
                existing_channel = Channel.objects \
                    .filter(channel_infos__profile=sender_profile, channel_type=2) \
                    .get(channel_infos__profile=friend_profile)
                channel_id = existing_channel.id
            except Channel.DoesNotExist:
                new_channel_name = str(sender_username) + "____" + str(friend_username)
                DIALOG_TYPE = 2
                channel_dialog_type = ChannelType.objects.get(id=DIALOG_TYPE)
                new_channel = Channel.objects.create(channel_name=new_channel_name, channel_type=channel_dialog_type)
                ChannelInfo.objects.create(channel=new_channel, profile=sender_profile)
                ChannelInfo.objects.create(channel=new_channel, profile=friend_profile)
                channel_id = new_channel.id
                print(f"*SERVER RESPONSE: Channel was created: {new_channel}")

            print("*SERVER RESPONSE: Successfully permitted friend request"
                  f"from sender_username: {sender_username} to friend_username: {friend_username}")
            
            return {"status": "success", "channel_id": channel_id}
        else:
            print("*SERVER RESPONSE: Error while permitting friend request"
                  f"from straight_friendship: sender_username: {sender_username}"
                  f"friend_username: {friend_username}."
                  "straight friendship request is already permitted")
            
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

        sender_profile = Queries.getCurrentProfileByUsername(sender_username, False)
        friend_profile = Queries.getCurrentProfileByUsername(friend_username, False)

        straight_friendship = Friendship.objects.get(sender=sender_profile, receiver=friend_profile)

        declined_status_type = FriendRequestType.objects.get(id=2)
        
        if (straight_friendship.status_type != declined_status_type):
            straight_friendship.status_type = declined_status_type
            straight_friendship.save()

            print("*SERVER RESPONSE: Successfully declined friend request"
                  f"from sender_username: {sender_username} to friend_username: {friend_username}")
            return "success"
        else:
            print("*SERVER RESPONSE: Error while declining friend request"
                  f"from sender_username: {sender_username} to"
                  f"friend_username: {friend_username}."
                  "Already declined, check consumers.py")
            return "already_declined"
        
    @database_sync_to_async
    def createFriendRequestNotification(self, sender_username, friend_username):
        """
        Makes async requests in database.

        This method creates open friend request notification
        according to the new friend request have created.
        """

        FRIEND_REQUEST_NOTIFICATION_TYPE = NotificationType.objects.get(id=2)
        FRIEND_REQUEST_NOTIFICATION_STATUS = NotificationStatus.objects.get(id=1)

        Notification.objects.create(notification_type=FRIEND_REQUEST_NOTIFICATION_TYPE, \
                                    owner_profile=Queries.getCurrentProfileByUsername(friend_username, False), \
                                    sender_profile=Queries.getCurrentProfileByUsername(sender_username, False), \
                                    notification_status = FRIEND_REQUEST_NOTIFICATION_STATUS)

    async def friendrequest_sendrequest(self, event):
        """
        This method processes friend request from sender user to receiver user.

        Parses sender username and receiver username from the sent data from the client
        through the WebSocket connection.

        Checkes whether the receiver is the target.

        If it called for the receiver, then user will get message
        with friend request information.

        Other users will be passed.
        """

        sender_username = event["sender_username"]
        friend_username = event["friend_username"]

        try:
            target = redis_adapter.get(self.room_group_name)
            if (target == self.username):
                print(f"*SERVER RESPONSE: Sent request only to {target}")
                profiles_data = await self.get_profiles_data(sender_username, friend_username)
                sender_profilename = profiles_data["sender_profilename"]
                friend_profilename = profiles_data["friend_profilename"]

                await self.createFriendRequestNotification(sender_username, friend_username)
                # clearCache for Notification

                await self.send(text_data=json.dumps({"type": "request",
                                                      "sender_username": sender_username,
                                                      "sender_profilename": sender_profilename,
                                                      "friend_username": friend_username,
                                                      "friend_profilename": friend_profilename
                                                      }))
            else:
                print("*SERVER RESPONSE:"
                      f"Deny request for none target (sender, strangers): {self.username},"
                      f"when the target: {target}")
        except Exception as ex:
            print(f"*SERVER RESPONSE: Received an exception while friend request sending: {ex}")
            raise ex
    
    async def friendrequest_permit(self, event):
        """
        This method processes the confirmation of the friend request
        from sender user to receiver user.

        Parses sender username and receiver username from the sent data from the client
        through the WebSocket connection.

        After that premits friend request and sends different messages for receiver user
        and sender user.

        Other users will be passed.
        """

        sender_username = event["sender_username"]
        friend_username = event["friend_username"]
        
        sender_profilename = event["sender_profilename"]
        friend_profilename = event["friend_profilename"]

        try:
            target = redis_adapter.get(self.room_group_name)
            if target == self.username:
                print(f"*SERVER RESPONSE: Processed confirmation only from target: {target}")

                try:
                    response = await self.permit_friend_request(sender_username, friend_username)
                    clearCache(f"cache__{self.user_id}__channel_ids_list")
                    clearCache(f"cache__{self.user_id}__friend_list")
                    status = response["status"]
                    channel_id = response["channel_id"]
                except Exception as ex:
                    print("*SERVER RESPONSE: Received an exception"
                          f"while friend request permitting in database sync_to_async method: {ex}")
                    
                    status = "failure"
                    channel_id = -1

                await self.send(text_data=json.dumps({"type": "permitted",
                                                    "status": status,
                                                    "channel_id": channel_id,
                                                    "sender_username": sender_username,
                                                    "friend_username": friend_username,
                                                    "sender_profilename": sender_profilename,
                                                    "friend_profilename": friend_profilename
                                                    }))

            elif self.username == sender_username:
                print("*SERVER RESPONSE:"
                      "Sending signal about successfull permitting friend request to request sender:"
                      f"{sender_username}, when the receiver is {target}")
                
                clearCache(f"cache__{self.user_id}__channel_ids_list")
                clearCache(f"cache__{self.user_id}__friend_list")
            
                await self.send(text_data=json.dumps({"type": "permitted",
                                                    "state": "success",
                                                    "sender_username": sender_username
                                                    }))
            
            else:
                print("*SERVER RESPONSE: Deny processing in confirmation"
                      f"for stranger: {self.username}, when the target: {target}")
                
        except Exception as ex:
            print(f"*SERVER RESPONSE: Received an exception while friend request permitting: {ex}")
            raise ex
            
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

        try:
            target = redis_adapter.get(self.room_group_name)
            if (self.username == target):
                print("*SERVER RESPONSE: Sending signal about ready state"
                      "to parse new friend list data"
                      f"for sender: {sender_username} from receiver: {friend_username}")

                print(f"*SERVER RESPONSE: Processed readytorefresh only from target: {target}")

                await self.send(text_data=json.dumps({"type": "refreshready",
                                                      "state": "success",
                                                      "sender_username": sender_username
                                                      }))
            else:
                print("*SERVER RESPONSE: Deny processing in readytorefresh"
                      f"for none target (sender, strangers): {self.username},"
                      f"when the target: {target}")
                
        except Exception as ex:
            print(f"*SERVER RESPONSE: Received an exception while readytorefresh signal sending: {ex}")
            raise ex
    
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

        try:
            target = redis_adapter.get(self.room_group_name)
            if self.username == target:
                print("*SERVER RESPONSE: Sending signal about ready state"
                      "of data for the new friend list"
                      f"for sender: {sender_username} from receiver: {friend_username}")
                
                print(f"*SERVER RESPONSE: Processed dataready only from target: {target}")
            elif self.username == sender_username:
                print(f"*SERVER RESPONSE: Signaling to sender: {sender_username}"
                      "about data ready state")

                await self.send(text_data=json.dumps({"type": "data_ready",
                                                      # "status": status,
                                                      "sender_username": sender_username,
                                                      "friend_username": friend_username
                                                      }))
            else:
                print("*SERVER RESPONSE: Deny processing in dataready"
                      f"for stranger: {self.username}, when the target: {target}")
                
        except Exception as ex:
            print(f"*SERVER RESPONSE: Received an exception while dataready signal sending: {ex}")
            raise ex    
    
    async def friendrequest_decline(self, event):
        """
        This method processes the abolition of the friend request
        from sender user to receiver user.

        Parses sender username and receiver username from the sent data from the client
        through the WebSocket connection.

        After that declines friend request and sends different messages for receiver user
        and sender user.

        Other users will be passed.
        """

        sender_username = event["sender_username"]
        friend_username = event["friend_username"]
        
        sender_profilename = event["sender_profilename"]
        friend_profilename = event["friend_profilename"]

        try:
            target = redis_adapter.get(self.room_group_name)
            if self.username == target:
                print(f"*SERVER RESPONSE: Processed abolition only from target: {target}")

                try:
                    status = await self.decline_friend_request(sender_username, friend_username)
                except Exception as ex:
                    print("*SERVER RESPONSE: Received an exception"
                          f"while declining friend request in  database sync_to_async method: {ex}")
                    
                    status = "failure"

                await self.send(text_data=json.dumps({"type": "declined",
                                                    "status": status,
                                                    "sender_username": sender_username,
                                                    "friend_username": friend_username,
                                                    "sender_profilename": sender_profilename,
                                                    "friend_profilename": friend_profilename
                                                    }))
            elif self.username == friend_username:
                print("*SERVER RESPONSE: Sending signal"
                      f"about successfull declining friend request to sender: {friend_username}")
            
                await self.send(text_data=json.dumps({"type": "declined",
                                                      "state": "success",
                                                      "sender_username": sender_username
                                                      }))
            else:
                print("*SERVER RESPONSE: Deny processing in abolition"
                      f"for stranger: {self.username}, when the target: {target}")
        
        except Exception as ex:
            print(f"*SERVER RESPONSE: Received an exception while friend request declining: {ex}")
            raise ex
