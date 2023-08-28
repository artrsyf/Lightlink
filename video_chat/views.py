from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Q
from .models import Profile, Friendship

def index(request):
    current_user_id = request.user.id
    current_profile = Profile.objects.get(user=current_user_id)
    friendship = Friendship.objects.filter(Q(sender=current_profile, status_type=3) | Q(receiver=current_profile, status_type=3))
    friends = []
    for relation in friendship:
        friends.append(relation.receiver if relation.sender.id == current_profile.id \
                              else relation.sender)
    print(friends)
    context = {
        'friends': friends
    }
    return render(request, 'video_chat/index.html', context)

def return_profile_data(request, _id):
    profile_name = Profile.objects.get(id=_id).profile_name
    return JsonResponse({'profile_name': profile_name})
