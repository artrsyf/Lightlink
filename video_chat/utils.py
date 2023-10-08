from .models import Profile, Friendship, Channel, User, Message
from django.db.models import Q

def find_current_profile(user_id: int) -> Profile:
    current_user = User.objects.get(id=user_id)
    current_profile = Profile.objects.get(user=current_user)
    return current_profile

def find_private_messages_list(user_id: int) -> list[tuple[Profile, Message]]:
    current_profile = find_current_profile(user_id)
    current_user = User.objects.get(id=user_id)
    friendship = Friendship.objects.filter(Q(sender=current_profile, status_type=3) \
                                           | Q(receiver=current_profile, status_type=3))
    private_messages = []

    try:
        for relation in friendship:
            friend = relation.receiver if relation.sender.id == current_profile.id else relation.sender
            channel = Channel.objects \
                    .filter(channel_infos__profile=current_profile, channel_type=2)\
                    .get(channel_infos__profile=friend)
            last_message = channel.all_messages.last()
            if (last_message != None):
                private_messages.append((friend, last_message))
    except Channel.DoesNotExist:
        print(f'*SERVER RESPONSE: User with username {current_user.username} has no channels')
        return []
    private_messages = list(set(private_messages))
    return private_messages

def find_friend_list(user_id: int) -> list[Profile]:
    current_profile = find_current_profile(user_id)
    friendship = Friendship.objects.filter(Q(sender=current_profile, status_type=3) \
                                           | Q(receiver=current_profile, status_type=3))
    friends = []
    for relation in friendship:
        friends.append(relation.receiver if relation.sender.id == current_profile.id \
                              else relation.sender)
    friends = list(set(friends))
    return friends

def find_channels_list(user_id: int) -> list[int]:
    current_profile = find_current_profile(user_id)
    channels_info_list = list(current_profile.channels.all().values())
    channels_ids_list = [i['id'] for i in channels_info_list]
    return channels_ids_list
