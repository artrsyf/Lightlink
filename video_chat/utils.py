from django.conf import settings
from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django.core.cache import cache
from typing import Any, Callable, Union
from django.db.models import QuerySet
from .models import Profile, Friendship, Channel, User, Message
from django.db.models import Q
from datetime import datetime, timedelta

CACHE_TTL = getattr(settings, 'CACHE_TTL', DEFAULT_TIMEOUT)
CACHE_ENABLED = getattr(settings, 'CACHE_ENABLED', True)

def getOrSetCache(key: str, request_func: Callable, timeout: int=CACHE_TTL) -> Any:
    data_from_cache = cache.get(key) if CACHE_ENABLED else None
    if data_from_cache is not None:
        print('cache')
        return data_from_cache
    else:
        print('request')
        request_result_data = request_func()
        cache.set(key, request_result_data, timeout)
        return request_result_data

class Queries:
    """
    Provide caching for different queries.

    Cache table:

    'cache__<<user_id>>__current_user' -> User
    
    'cache__<<username>>__current_user' -> User
    
    'cache__<<user_id>>__current_profile' -> Profile
    
    'cache__<<user_id>>__current_profile' -> Profile
    
    'cache__<<user_id>>__private_message_list' -> list[tuple[Channel, Message, channel_avatar_utl(str)]]
    
    'cache__<<user_id>>__channel_ids_list' -> list[channel_id(int)]
    
    'cache__<<channel_id>>__channel_messages' -> QuerySet[Message]
    
    'cache__<<channel_id>>__channel_data_with_serialized_messages' -> dict with channel_avatar_url,
    Messages, Channel Data
    
    'cache__<<user_id>>__friend_list' -> List[Profile]
    """

    def getCurrentUserById(user_id: int) -> User:
        cache_key = f"cache__{user_id}__current_user"
        current_user = getOrSetCache(cache_key, lambda: User.objects.get(id=user_id))
        return current_user
    
    def getCurrentUserByUsername(username: str) -> User:
        cache_key = f"cache__{username}__current_user"
        current_user = getOrSetCache(cache_key, lambda: User.objects.get(username=username))
        return current_user
    
    def getCurrentProfileByUserId(user_id: int) -> Profile:
        current_user = Queries.getCurrentUserById(user_id)
        cache_key = f"cache__{user_id}__current_profile"
        current_profile = getOrSetCache(cache_key, lambda: Profile.objects.get(user=current_user))
        return current_profile
    
    def getCurrentProfileByUsername(username: str) -> Profile:
        current_user = Queries.getCurrentUserByUsername(username)
        cache_key = f"cache__{current_user.id}__current_profile"
        current_profile = getOrSetCache(cache_key, lambda: Profile.objects.get(user=current_user))
        return current_profile
    
    def getPrivateMessageListByUserId(user_id: int) -> list[tuple[Channel, Message, str]]:
        cache_key = f"cache__{user_id}__private_message_list"
        private_message_list = getOrSetCache(cache_key, 
                                             lambda: Queries.__findPrivateMessageListByUserId(user_id))
        return private_message_list
    
    def __findPrivateMessageListByUserId(user_id: int) -> list[tuple[Channel, Message, str]]:
        current_profile = Queries.getCurrentProfileByUserId(user_id)
        private_messages = []

        current_profile_channels = current_profile.channels.all()
        for channel in current_profile_channels:
            if channel.channel_type.id == 2:
                query_result = list(channel.profile_set.all())
                query_result.remove(current_profile)
                if len(query_result) > 1:
                    raise Exception('More than 2 users in dialog room')
                friend_profile = query_result[0]
                channel_avatar_url = friend_profile.profile_avatar.url
            else:
                channel_avatar_url = 'x'
            last_message = channel.all_messages.last()
            if last_message != None:
                last_message.updated_at_processed = Queries.convertItemDate(last_message.updated_at \
                                                                    .strftime("%b. %d, %Y, %I:%M %p"))
                channel.channel_name_processed = Queries.convertChannelDialogName(channel.channel_name, user_id)
                private_messages.append((channel, last_message, channel_avatar_url))
        private_messages.sort(key=lambda private_message: private_message[1].updated_at, 
                    reverse=True)
        return private_messages
    
    def __findChannelIdsListByUserId(user_id: int) -> list[int]:
        current_profile = Queries.getCurrentProfileByUserId(user_id)
        channels_data_list = list(current_profile.channels.all().values())
        channels_ids_list = [channel_data['id'] for channel_data in channels_data_list]
        return channels_ids_list

    def getChannelIdsListByUserId(user_id: int) -> list[int]:
        cache_key = f"cache__{user_id}__channel_ids_list"
        channels_ids_list = getOrSetCache(cache_key, 
                                             lambda: Queries.__findChannelIdsListByUserId(user_id))
        return channels_ids_list
    
    def getChannelMessages(channel: Channel) -> QuerySet[Message]:
        cache_key = f"cache__{channel.id}__channel_messages"
        channel_messages = getOrSetCache(cache_key, lambda: channel.all_messages.all())
        return channel_messages
    
    def __findChannelDataWithSerializedMessages(channel_id: int, owner_user_id: int) -> dict:
        channel = Channel.objects.get(id=channel_id)
        channel.channel_name = Queries.convertChannelDialogName(channel.channel_name, owner_user_id)
        channel_messages = Queries.getChannelMessages(channel)

        serialized_channel_messages = [channel_message.to_dict() for channel_message in channel_messages]

        return channel.to_dict() | {"channel_messages": serialized_channel_messages}
    
    def getChannelDataWithSerializedMessages(channel_id: int, owner_user_id: int) -> dict:
        cache_key = f"cache__{channel_id}__channel_data_with_serialized_messages"
        channel_data_dict = getOrSetCache(cache_key, 
                                          lambda: Queries.__findChannelDataWithSerializedMessages(channel_id, owner_user_id))
        channel_avatar_url = Queries.findChannelAvatarUrl(channel_id, owner_user_id)

        return channel_data_dict | {"channel_avatar_url": channel_avatar_url}

    def __findFriendListByUserId(user_id: int) -> list[tuple[Profile, Channel]]:
        current_profile = Queries.getCurrentProfileByUserId(user_id)
        friendship = Friendship.objects.filter(Q(sender=current_profile, status_type=3) \
                                            | Q(receiver=current_profile, status_type=3))
        accepted_friend_with_channel_list = []
        for relation in friendship:
            friend_profile = relation.receiver if relation.sender.id == current_profile.id \
                                else relation.sender
            try:
                channel = Channel.objects\
                        .filter(channel_infos__profile=current_profile, channel_type=2)\
                        .get(channel_infos__profile=friend_profile)
            except Channel.DoesNotExist:
                print("*SERVER RESPONSE: Friendship exists but channel was not found for user"
                    f"with user_id: {user_id} (friend profile - {friend_profile})")
                pass
            
            friend = (friend_profile, channel)
            accepted_friend_with_channel_list.append(friend)

        accepted_friend_with_channel_list = \
            sorted(list(set(accepted_friend_with_channel_list)), 
                   key=lambda friend: friend[0].profile_name)
        
        return accepted_friend_with_channel_list
    
    def getFriendListByUserId(user_id: int) -> list[Profile]:
        cache_key = f"cache__{user_id}__friend_list"
        friend_list = getOrSetCache(cache_key, lambda: Queries.__findFriendListByUserId(user_id))
        return friend_list

    # not requests
    def convertItemDate(unprocessed_string_date: str) -> str:
        processed_date = datetime.strptime(unprocessed_string_date, "%b. %d, %Y, %I:%M %p")
        current_datetime = datetime.now()

        if processed_date.date() == current_datetime.date():
            return processed_date.strftime("%H:%M")

        elif processed_date.date() == (current_datetime - timedelta(days=1)).date():
            return "Вчера"

        elif processed_date.year == current_datetime.year:
            return processed_date.strftime("%b. %d")

        else:
            return processed_date.strftime("%b. %d %Y")
        
    def convertChannelDialogName(unprocessed_channel_name: str, owner_user_id: int) -> str:
        owner_username = Queries.getCurrentUserById(owner_user_id).username
        channel_usernames = unprocessed_channel_name.split("____")
        if len(channel_usernames) != 2:
            raise Exception("More than two users in dialog channel")
        
        channel_usernames.remove(owner_username)
        friend_username = channel_usernames[0]
        channel_name = Queries.getCurrentProfileByUsername(friend_username).profile_name

        return channel_name

    def findChannelAvatarUrl(channel_id: int, owner_user_id: int) -> str:
        channel = Channel.objects.get(id=channel_id)

        if channel.channel_type.id == 2:
            friend_profile = channel.channel_infos \
                .get(~Q(profile=Queries.getCurrentProfileByUserId(owner_user_id))).profile
            channel_avatar_url = friend_profile.profile_avatar.url
        else:
            channel_avatar_url = 'x'

        return channel_avatar_url

    
# def find_current_profile(user_id: int) -> Profile:
#     current_user = User.objects.get(id=user_id)
#     current_profile = Profile.objects.get(user=current_user)
#     return current_profile

# def find_current_profile_with_username(username: str) -> Profile:
#     current_user = User.objects.get(username=username)
#     current_profile = Profile.objects.get(user=current_user)
#     return current_profile

# def find_private_messages_list(user_id: int):
#     current_profile = find_current_profile(user_id)
#     private_messages = []

#     current_profile_channels = current_profile.channels.all()
#     for channel in current_profile_channels:
#         if channel.channel_type.id == 2:
#             query_result = list(channel.profile_set.all())
#             query_result.remove(current_profile)
#             if len(query_result) > 1:
#                 raise Exception('More than 2 users in dialog room')
#             friend_profile = query_result[0]
#             channel_avatar_url = friend_profile.profile_avatar.url
#         else:
#             channel_avatar_url = 'x'
#         last_message = channel.all_messages.last()
#         if last_message != None:
#             last_message.updated_at_processed = convertItemDate(last_message.updated_at \
#                                                                 .strftime("%b. %d, %Y, %I:%M %p"))
#             channel.channel_name_processed = convertChannelDialogName(channel.channel_name, user_id)
#             private_messages.append((channel, last_message, channel_avatar_url))

#     return sorted(private_messages, 
#                   key=lambda private_message: private_message[1].updated_at, 
#                   reverse=True)

# def find_friend_list(user_id: int) -> list[Profile]:
#     current_profile = find_current_profile(user_id)
#     friendship = Friendship.objects.filter(Q(sender=current_profile, status_type=3) \
#                                            | Q(receiver=current_profile, status_type=3))
#     friends = []
#     for relation in friendship:
#         friend_profile = relation.receiver if relation.sender.id == current_profile.id \
#                               else relation.sender
#         try:
#             channel = Channel.objects\
#                     .filter(channel_infos__profile=current_profile, channel_type=2)\
#                     .get(channel_infos__profile=friend_profile)
#         except Channel.DoesNotExist:
#             print("*SERVER RESPONSE: Friendship exists but channel was not found for user"
#                   f"with user_id: {user_id}")
#             return []
        
#         friend = (friend_profile, channel)
#         friends.append(friend)
#     friends = sorted(list(set(friends)), key=lambda friend: friend[0].profile_name)
#     return friends

# def find_channels_list(user_id: int) -> list[int]:
#     current_profile = find_current_profile(user_id)
#     channels_data_list = list(current_profile.channels.all().values())
#     channels_ids_list = [channel_data['id'] for channel_data in channels_data_list]
#     return channels_ids_list

# def findChannelDataWithSerializedMessages(channel_id: int, owner_user_id: int) -> dict:
#     channel = Channel.objects.get(id=channel_id)
#     channel.channel_name = convertChannelDialogName(channel.channel_name, owner_user_id)
#     channel_messages = channel.all_messages.all()

#     channel_avatar_url = findChannelAvatarUrl(channel_id, owner_user_id)

#     serialized_channel_messages = [channel_message.to_dict() for channel_message in channel_messages]

#     return channel.to_dict() | {"channel_avatar_url": channel_avatar_url} \
#         | {"channel_messages": serialized_channel_messages}

# def convertItemDate(unprocessed_string_date: str) -> str:
#     processed_date = datetime.strptime(unprocessed_string_date, "%b. %d, %Y, %I:%M %p")
#     current_datetime = datetime.now()

#     if processed_date.date() == current_datetime.date():
#         return processed_date.strftime("%H:%M")

#     elif processed_date.date() == (current_datetime - timedelta(days=1)).date():
#         return "Вчера"

#     elif processed_date.year == current_datetime.year:
#         return processed_date.strftime("%b. %d")

#     else:
#         return processed_date.strftime("%b. %d %Y")
    
# def convertChannelDialogName(unprocessed_channel_name: str, owner_user_id: int) -> str:
#     owner_username = User.objects.get(id=owner_user_id).username
#     channel_usernames = unprocessed_channel_name.split("____")
#     if len(channel_usernames) != 2:
#         raise Exception("More than two users in dialog channel")
    
#     channel_usernames.remove(owner_username)
#     friend_username = channel_usernames[0]
#     channel_name = find_current_profile_with_username(friend_username).profile_name

#     return channel_name

# def findChannelAvatarUrl(channel_id: int, owner_user_id: int) -> str:
#     channel = Channel.objects.get(id=channel_id)

#     if channel.channel_type.id == 2:
#         friend_profile = channel.channel_infos \
#             .get(~Q(profile=find_current_profile(owner_user_id))).profile
#         channel_avatar_url = friend_profile.profile_avatar.url
#     else:
#         channel_avatar_url = 'x'

#     return channel_avatar_url
