from .models import Profile, Friendship, Channel
from django.db.models import Q

def find_private_messages_list(user_id):
    current_profile = Profile.objects.get(user=user_id)
    friendship = Friendship.objects.filter(Q(sender=current_profile, status_type=3) \
                                           | Q(receiver=current_profile, status_type=3))
    private_messages = []
    for relation in friendship:
        friend = relation.receiver if relation.sender.id == current_profile.id else relation.sender
        channel = Channel.objects \
                .filter(channel_infos__profile=current_profile, channel_type=2)\
                .get(channel_infos__profile=friend)
        last_message = channel.all_messages.last()
        if (last_message != None):
            private_messages.append((friend, last_message))
    private_messages = list(set(private_messages))
    return private_messages

def find_friend_list(user_id):
    current_profile = Profile.objects.get(user=user_id)
    friendship = Friendship.objects.filter(Q(sender=current_profile, status_type=3) \
                                           | Q(receiver=current_profile, status_type=3))
    friends = []
    for relation in friendship:
        friends.append(relation.receiver if relation.sender.id == current_profile.id \
                              else relation.sender)
    friends = list(set(friends))
    return friends