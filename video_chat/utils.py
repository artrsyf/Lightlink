from .models import Profile, Friendship
from django.db.models import Q

def find_friend_list(user_id):
    current_profile = Profile.objects.get(user=user_id)
    friendship = Friendship.objects.filter(Q(sender=current_profile, status_type=3) | Q(receiver=current_profile, status_type=3))
    friends = []
    for relation in friendship:
        friends.append(relation.receiver if relation.sender.id == current_profile.id \
                              else relation.sender)
    return friends