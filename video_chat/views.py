from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Q
from .models import Profile, Friendship, Channel, ChannelInfo, ChannelType
import json

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

# this view should create or return existing room (amount of tables in db)
def call_process(request):
    if request.method == 'POST':
        json_content = request.POST.get('content')
        content = json.loads(json_content)
        sender_id = content['sender_id']
        receiver_id = content['receiver_id']
        print(f'SERVER RESPONSE: ASYNC POST REQUEST GOT WITH SENDER_ID: {sender_id}')
        print(f'SERVER RESPONSE: ASYNC POST REQUEST GOT WITH RECEIVER_ID: {receiver_id}')
        sender_profile = Profile.objects.get(id=sender_id)
        receiver_profile = Profile.objects.get(id=receiver_id)
        # Нашли все персональные каналы вызывающего
        channels = sender_profile.channels.filter(channel_type=2).values_list('id', flat=True)
        existing_channel_meta = ChannelInfo.objects.filter(Q(channel__in=channels) & Q(profile__id=receiver_id))
        if existing_channel_meta.count() > 1:
            raise Exception("Personal channel have doubles")
        if existing_channel_meta.exists():
            existing_channel = existing_channel_meta.get().channel
            return JsonResponse({'channel_name': existing_channel.channel_name,
                                 'channel_type_id': existing_channel.channel_type.type})
        else:
            new_channel_name = str(sender_id) + '____' + str(receiver_id)
            DIALOG_TYPE = 2
            channel_dialog_type = ChannelType.objects.get(id=DIALOG_TYPE)
            new_channel = Channel.objects.create(channel_name=new_channel_name, channel_type=channel_dialog_type)
            ChannelInfo.objects.create(channel= new_channel, profile=sender_profile)
            ChannelInfo.objects.create(channel= new_channel, profile=receiver_profile)
            return JsonResponse({'channel_name': new_channel.channel_name,
                                 'channel_type_id': new_channel.channel_type.type})
    return JsonResponse({'ERROR_MESSAGE': 'Invalid request method',
                         'REQUEST_METHOD': request.method}, status=400)