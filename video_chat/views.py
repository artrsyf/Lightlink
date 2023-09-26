from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.db.models import Q
from .models import User, Profile, Channel, ChannelInfo, ChannelType
import json, time, environ
from agora_token_builder import RtcTokenBuilder
from sys import maxsize as MAX_INT
from .utils import find_friend_list
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from .forms import FriendshipForm

env = environ.Env()
environ.Env().read_env('../lightlink/')

def index(request):
    current_user_id = request.user.id
    friends = find_friend_list(current_user_id)
    current_profile = Profile.objects.get(user=request.user)
    context = {
        'current_profile': current_profile,
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

        print(f'*SERVER RESPONSE: Async post request got with sender_profile_id: {sender_id}')
        print(f'*SERVER RESPONSE: Async post request got with receiver_profile_id: {receiver_id}')
        
        sender_profile = Profile.objects.get(id=sender_id)
        receiver_profile = Profile.objects.get(id=receiver_id)
        try:
            channel = Channel.objects\
                .filter(channel_infos__profile=sender_profile, channel_type=2)\
                .get(channel_infos__profile=receiver_profile)
            print(f'*SERVER RESPONSE: Channel is using: {channel}')
            return JsonResponse({'channel_id': channel.id,
                                 'channel_name': channel.channel_name,
                                 'channel_type': channel.channel_type.type})
        except Channel.DoesNotExist:
            new_channel_name = str(sender_id) + '____' + str(receiver_id)
            DIALOG_TYPE = 2
            channel_dialog_type = ChannelType.objects.get(id=DIALOG_TYPE)
            new_channel = Channel.objects.create(channel_name=new_channel_name, channel_type=channel_dialog_type)
            ChannelInfo.objects.create(channel=new_channel, profile=sender_profile)
            ChannelInfo.objects.create(channel=new_channel, profile=receiver_profile)
            print(f'*SERVER RESPONSE: Channel was created: {new_channel}')
            return JsonResponse({'channel_id': new_channel.id,
                                 'channel_name': new_channel.channel_name,
                                 'channel_type': new_channel.channel_type.type})
        except MultipleObjectsReturned:
            print(f'*SERVER RESPONSE: Multiple channels detected')
            raise MultipleObjectsReturned

    return JsonResponse({'*JSON_RESPONSE': {'ERROR_MESSAGE': 'Invalid request method',
                         'REQUEST_METHOD': request.method}}, status=400)
def get_token(request):
    app_id = env("APP_ID")
    channel_id = request.GET.get('channel')
    app_certificate = env("APP_CERTIFICATE")
    user_id = request.session['user_id']
    stream_id = MAX_INT // 100_000_000_000 - user_id
    expiration_time_in_sec = 3600
    current_time_stamp = int(time.time())
    privilege_expired_Ts = current_time_stamp + expiration_time_in_sec
    role = 1

    token = RtcTokenBuilder.buildTokenWithUid(app_id, app_certificate, channel_id, user_id, role, privilege_expired_Ts)

    stream_token = RtcTokenBuilder.buildTokenWithUid(app_id, app_certificate, channel_id, stream_id, role, privilege_expired_Ts)

    return JsonResponse({'channel': channel_id, 'user_id': user_id, 'token': token, 'stream_id': stream_id, 'stream_token': stream_token}, safe=False)

def channel(request, channel_id):
    current_user_id = request.user.id
    current_profile = Profile.objects.get(user=request.user)
    friends = find_friend_list(current_user_id)
    context = {
        'current_profile': current_profile,
        'friends': friends,
        'channel_id': channel_id
    }
    return render(request, 'video_chat/channel.html', context)

def get_user_data(request):
    try:
        user_id = request.session['user_id']
        user_username = request.session['user_username']
        user_profilename = request.session['user_profilename']
        return JsonResponse({'user_id': user_id,
                            'user_username': user_username,
                            'user_profilename': user_profilename})
    except KeyError:
        return JsonResponse({'*JSON_RESPONSE': {'ERROR_MESSAGE':
                                               'Request session has KeyError in get_user_data',
                                               'REQUEST METHOD': request.method}}, status=400)
    except Exception:
        return JsonResponse({'*JSON_RESPONSE': {'ERROR_MESSAGE': 'Unexpected Exception',
                                               'REQUEST METHOD': request.method}}, status=400)
    
def get_agora_sdk_data(request):
    if request.method == 'POST':
        app_id = env("APP_ID")
        return JsonResponse({'app_id': app_id})
    else:
        return JsonResponse({'*JSON_RESPONSE': {'ERROR_MESSAGE': 'Invalid request method',
                                                'REQUEST_METHOD': request.method}}, status=400)

def get_member(request):
    try:
        uid = request.GET.get('uid')
        member = User.objects.get(id=uid)
        member_profile = Profile.objects.get(user=member)
        name = member_profile.profile_name
        return JsonResponse({'name': name}, safe=False)
    except ValueError:
        print(f'*SERVER RESPONSE: Incorrect request URL')
        return JsonResponse({'*JSON_RESPONSE': {'ERROR_MESSAGE': 'Incorrect request URL'}}, status=400)
    except ObjectDoesNotExist:
        try:
            print(f'*SERVER RESPONSE: Can\'t find user by id, trying to find by stream_id')
            possible_id = MAX_INT // 100_000_000_000 - int(uid)
            member = User.objects.get(id=possible_id)
            member_profile = Profile.objects.get(user=member)
            name = ""
            return JsonResponse({'name': name}, safe=False)
        except ObjectDoesNotExist:
            print(f'*SERVER RESPONSE: Requested user does not exist')
            return JsonResponse({'*JSON_RESPONSE': {'ERROR_MESSAGE': 'Requested user does not exist'}}, status=400)

def friendRequest(request):
    print('friendrequest ', request.method)
    error = ''
    if request.method == 'POST':
        form = FriendshipForm(request.POST, sender=request.user)
        print(form.errors)
        if form.is_valid():
            print('form is valid')
            form.save()
            # return redirect('Home')
        else:
            print('form is invalid')

            error = 'Error in friend request form'
            return JsonResponse({'result': str(form.errors)})
    form = FriendshipForm(sender=request.user)
    context = {
        'form': form,
        'error': error
    }
    return render(request, 'video_chat/friend_request.html', context)
