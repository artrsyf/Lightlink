from .models import Profile, Friendship, Channel, User, Message
from django.db.models import Q

def find_current_profile(user_id: int) -> Profile:
    current_user = User.objects.get(id=user_id)
    current_profile = Profile.objects.get(user=current_user)
    return current_profile

def find_current_profile_with_username(username: str) -> Profile:
    current_user = User.objects.get(username=username)
    current_profile = Profile.objects.get(user=current_user)
    return current_profile

def find_private_messages_list(user_id: int) -> dict[Channel, Message]:
    current_profile = find_current_profile(user_id)
    private_messages = {}

    current_profile_channels = current_profile.channels.all()
    for channel in current_profile_channels:
        last_message = channel.all_messages.last()
        if last_message != None:
            private_messages[channel] = last_message

    return private_messages

def find_friend_list(user_id: int) -> list[Profile]:
    current_profile = find_current_profile(user_id)
    friendship = Friendship.objects.filter(Q(sender=current_profile, status_type=3) \
                                           | Q(receiver=current_profile, status_type=3))
    friends = []
    for relation in friendship:
        friend_profile = relation.receiver if relation.sender.id == current_profile.id \
                              else relation.sender
        channel = Channel.objects\
                 .filter(channel_infos__profile=current_profile, channel_type=2)\
                 .get(channel_infos__profile=friend_profile)
        
        friend = (friend_profile, channel)
        friends.append(friend)
    friends = list(set(friends))
    return friends

def find_channels_list(user_id: int) -> list[int]:
    current_profile = find_current_profile(user_id)
    channels_data_list = list(current_profile.channels.all().values())
    channels_ids_list = [channel_data['id'] for channel_data in channels_data_list]
    return channels_ids_list
