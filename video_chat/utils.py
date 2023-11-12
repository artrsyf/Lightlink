from .models import Profile, Friendship, Channel, User, Message
from django.db.models import Q
from datetime import datetime, timedelta


def find_current_profile(user_id: int) -> Profile:
    current_user = User.objects.get(id=user_id)
    current_profile = Profile.objects.get(user=current_user)
    return current_profile

def find_current_profile_with_username(username: str) -> Profile:
    current_user = User.objects.get(username=username)
    current_profile = Profile.objects.get(user=current_user)
    return current_profile

def find_private_messages_list(user_id: int):
    current_profile = find_current_profile(user_id)
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
            last_message.updated_at_processed = convertItemDate(last_message.updated_at \
                                                                .strftime("%b. %d, %Y, %I:%M %p"))
            channel.channel_name_processed = convertChannelDialogName(channel.channel_name, user_id)
            private_messages.append((channel, last_message, channel_avatar_url))

    return sorted(private_messages, 
                  key=lambda private_message: private_message[1].updated_at, 
                  reverse=True)

def find_friend_list(user_id: int) -> list[Profile]:
    current_profile = find_current_profile(user_id)
    friendship = Friendship.objects.filter(Q(sender=current_profile, status_type=3) \
                                           | Q(receiver=current_profile, status_type=3))
    friends = []
    for relation in friendship:
        friend_profile = relation.receiver if relation.sender.id == current_profile.id \
                              else relation.sender
        try:
            channel = Channel.objects\
                    .filter(channel_infos__profile=current_profile, channel_type=2)\
                    .get(channel_infos__profile=friend_profile)
        except Channel.DoesNotExist:
            print("*SERVER RESPONSE: Friendship exists but channel was not found for user"
                  f"with user_id: {user_id}")
            return []
        
        friend = (friend_profile, channel)
        friends.append(friend)
    friends = sorted(list(set(friends)), key=lambda friend: friend[0].profile_name)
    return friends

def find_channels_list(user_id: int) -> list[int]:
    current_profile = find_current_profile(user_id)
    channels_data_list = list(current_profile.channels.all().values())
    channels_ids_list = [channel_data['id'] for channel_data in channels_data_list]
    return channels_ids_list

def findChannelDataWithSerializedMessages(channel_id: int) -> dict:
    channel = Channel.objects.get(id=channel_id)
    channel_messages = channel.all_messages.all()

    serialized_channel_messages = [channel_message.to_dict() for channel_message in channel_messages]

    return channel.to_dict() | {'channel_messages': serialized_channel_messages}

def convertItemDate(unprocessed_string_date: str) -> str:
    processed_date = datetime.strptime(unprocessed_string_date, "%b. %d, %Y, %I:%M %p")
    current_datetime = datetime.now()

    if processed_date.date() == current_datetime.date():
        return processed_date.strftime("%I:%M %p")

    elif processed_date.date() == (current_datetime - timedelta(days=1)).date():
        return "Yesterday"

    elif processed_date.year == current_datetime.year:
        return processed_date.strftime("%b. %d")

    else:
        return processed_date.strftime("%b. %d %Y")
    
def convertChannelDialogName(unprocessed_channel_name: str, owner_user_id: int) -> str:
    owner_username = User.objects.get(id=owner_user_id).username
    channel_usernames = unprocessed_channel_name.split("____")
    print(channel_usernames)
    if len(channel_usernames) != 2:
        raise Exception("More than two users in dialog channel")
    
    channel_usernames.remove(owner_username)
    friend_username = channel_usernames[0]
    channel_name = find_current_profile_with_username(friend_username).profile_name

    return channel_name
