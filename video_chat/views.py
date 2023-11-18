from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.db.models import Q
from .models import User, Profile, Channel, ChannelInfo, Friendship
import json, time, environ
from agora_token_builder import RtcTokenBuilder
from sys import maxsize as MAX_INT
# from .utils import find_private_messages_list, find_friend_list, find_channels_list, \
#     find_current_profile, findChannelDataWithSerializedMessages, convertItemDate, \
#     convertChannelDialogName, findChannelAvatarUrl
from .utils import Queries
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from .forms import FriendshipForm, ProfileForm
from django.contrib.auth.decorators import login_required

env = environ.Env()
environ.Env().read_env('../lightlink/')

@login_required(login_url="/login/")
def index(request):
    current_user_id = request.user.id
    private_messages = Queries.getPrivateMessageListByUserId(current_user_id)
    current_profile = Profile.objects.get(user=request.user)
    channels_ids = Queries.getChannelIdsListByUserId(current_user_id)
    context = {
        'current_user': request.user,
        'current_profile': current_profile,
        'private_messages': private_messages,
        'channels_ids': channels_ids
    }
    return render(request, 'video_chat/index.html', context)

@login_required(login_url="/login/")
def return_profile_data(request, _id):
    profile_name = Profile.objects.get(id=_id).profile_name
    return JsonResponse({'profile_name': profile_name})

@login_required(login_url="/login/")
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

@login_required(login_url="/login/")
def channel(request, channel_id):
    channel = Channel.objects.get(id=channel_id)
    current_user_id = request.user.id
    current_profile = Profile.objects.get(user=request.user)
    
    try:
        channel.channel_infos.get(profile=current_profile)
    except ChannelInfo.DoesNotExist as ex:
        print(F"*SERVER RESPONSE: {ex}")
        return redirect("WebChatHome")

    channel_name_unprocessed = channel.channel_name
    channel_name_processed = Queries.convertChannelDialogName(channel_name_unprocessed, current_user_id)
    channel_type_id = channel.channel_type.id

    channel_messages_json = json.dumps(Queries.getChannelDataWithSerializedMessages(channel_id, current_user_id))
    private_messages = Queries.getPrivateMessageListByUserId(current_user_id) 
    channels_ids = Queries.getChannelIdsListByUserId(current_user_id)
    channel_avatar_url = Queries.findChannelAvatarUrl(channel_id, current_user_id)
    context = {
        'current_user': request.user,
        'current_profile': current_profile,
        'private_messages': private_messages,
        'channels_ids': channels_ids,
        'channel_id': channel_id,
        'channel_name': channel_name_processed,
        'channel_avatar_url': channel_avatar_url,
        'channel_type_id': channel_type_id,
        'channel_messages': channel_messages_json,
        'current_user_id': current_user_id
    }
    return render(request, 'video_chat/channel.html', context)

@login_required(login_url="/login/")
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

@login_required(login_url="/login/")   
def get_agora_sdk_data(request):
    if request.method == 'POST':
        app_id = env("APP_ID")
        return JsonResponse({'app_id': app_id})
    else:
        return JsonResponse({'*JSON_RESPONSE': {'ERROR_MESSAGE': 'Invalid request method',
                                                'REQUEST_METHOD': request.method}}, status=400)

@login_required(login_url="/login/")
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

@login_required(login_url="/login/")
def friendRequest(request):
    print('friendrequest ', request.method)
    error_default_message = ''
    if request.method == 'POST':
        form = FriendshipForm(request.POST, sender=request.user)
        print(form.errors)
        if form.is_valid():
            form.save()
            return JsonResponse({'result': 'Successfully sent request', 'status': 'success'})
        else:
            error_default_message = 'Something went wrong'
            error_messages = [str(error) for field, errors in form.errors.items() for error in errors]
            return JsonResponse({'result': error_messages, 'status': 'failure'})
    form = FriendshipForm(sender=request.user)
    context = {
        'current_user': request.user,
        'form': form,
        'error': error_default_message
    }
    return render(request, 'video_chat/friend_request.html', context)

# Проверить работу на большом количестве пользователей
@login_required(login_url="/login/")
def getMemberFriends(request, user_id):
    friends = Queries.getFriendListByUserId(user_id)
    friends_serialized = []
    for friend in friends:
        friend_info = friend[0].to_dict()
        channel_info = friend[1].to_dict()
        friends_serialized.append({'friend_info': friend_info, 'channel_info': channel_info})
    return JsonResponse({'fresh_friends': friends_serialized})

@login_required(login_url="/login/")
def getMemberChannelsIds(request, user_id):
    return JsonResponse({'channels_ids': Queries.getChannelIdsListByUserId(user_id)})

@login_required(login_url="/login/")
def getChannelLastMessageInfo(request, channel_id):
    channel = Channel.objects.get(id=channel_id)
    current_profile = Queries.getCurrentProfileByUserId(request.user.id)
    last_message = channel.all_messages.last()
    sender_profile = last_message.profile
    if channel.channel_type.id == 2:
        # check on multy
        channel_name = ChannelInfo.objects \
            .filter(Q(channel=channel) & ~Q(profile=current_profile)).last().profile.profile_name
        channel_avatar_url = Queries.findChannelAvatarUrl(channel_id, request.user.id)
    else:
            channel_name = 'x'
            channel_avatar_url = 'x'
            # else from groups
    sender_profilename = sender_profile.profile_name
    content = last_message.content
    unprocessed_updated_at = last_message.updated_at.strftime("%b. %d, %Y, %I:%M %p")
    processed_updated_at = Queries.convertItemDate(unprocessed_updated_at)

    return JsonResponse({'channel_id': channel_id,
                         'channel_name': channel_name,
                         'sender_profilename': sender_profilename,
                         'channel_avatar_url': channel_avatar_url,
                         'content': content,
                         'updated_at': processed_updated_at
                         })

@login_required(login_url="/login/")
def getMemberPrivateMessagesList(request, user_id):
    current_profile = Queries.getCurrentProfileByUserId(user_id)
    channels_ids = Queries.getChannelIdsListByUserId(user_id)
    channels_infos = []
    for channel_id in channels_ids:
        channel = Channel.objects.get(id=channel_id)

        last_message = channel.all_messages.last()
        if not last_message:
            continue
        
        sender_profile = last_message.profile
        if channel.channel_type.id == 2:
        # check on multy
            friend_profile = ChannelInfo.objects \
                .filter(Q(channel=channel) & ~Q(profile=current_profile)).last().profile
            channel_name = friend_profile.profile_name
            channel_avatar_url = friend_profile.profile_avatar.url
        else:
            channel_name = 'x'
            channel_avatar_url = 'x'
            # else from groups
        sender_profilename = sender_profile.profile_name
        content = last_message.content
        unprocessed_updated_at = last_message.updated_at.strftime("%b. %d, %Y, %I:%M %p")
        processed_updated_at = Queries.convertItemDate(unprocessed_updated_at)

        channels_infos.append({'channel_id': channel_id,
                               'channel_name': channel_name,
                               'sender_profilename': sender_profilename,
                               'channel_avatar_url': channel_avatar_url,
                               'content': content,
                               'updated_at_unprocessed': unprocessed_updated_at,
                               'updated_at': processed_updated_at
                               })
        channels_infos.sort(key=lambda channel_info: channel_info["updated_at_unprocessed"], 
                            reverse=True)
    return JsonResponse(channels_infos, safe=False)

@login_required(login_url="/login/")
def getChannelData(request, channel_id):
    user_id = request.user.id
    full_channel_data_dict = Queries.getChannelDataWithSerializedMessages(channel_id, user_id)

    return JsonResponse(full_channel_data_dict)

@login_required(login_url="/login/")
def getChannelMeta(request, channel_id):
    try:
        channel = Channel.objects.get(id=channel_id)
        channel_name = channel.channel_name
        channel_type_id = channel.channel_type.id
        return JsonResponse({'channel_id': channel_id,
                             'channel_name': channel_name,
                             'channel_type': channel_type_id
                             })
    except Channel.DoesNotExist:
        return JsonResponse({'*JSON_RESPONSE': {'ERROR_MESSAGE': 'Requested channel does not exist'}}, status=400)
    except Channel.MultipleObjectsReturned:
        return JsonResponse({'*JSON_RESPONSE': {'ERROR_MESSAGE': 'Query returned multiple channel objects'}}, status=400)
    except:
        return JsonResponse({'*JSON_RESPONSE': {'ERROR_MESSAGE': 'Unrecognized error while requesting channel type'}}, status=400)

@login_required(login_url="/login/")
def editProfile(request):
    profile = Queries.getCurrentProfileByUserId(request.user.id)
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, updated_profile=profile)
        print(form.errors)
        if form.is_valid():
            profile.profile_name = request.POST['profilename']
            profile.profile_avatar = request.FILES['profile_avatar']
            profile.save()
            return JsonResponse({'result': 'ok'})
    default_form_profile_avatar = profile.profile_avatar \
        if profile.profile_avatar != 'default_profile_avatar.jpg' else None
    form = ProfileForm(initial={'profilename': profile.profile_name,
                                'profile_avatar': default_form_profile_avatar},
                       updated_profile=profile)
    context = {'form': form}
    return render(request, 'video_chat/update_profile.html', context)

@login_required(login_url="/login/")
def getMemberNotifications(request, user_id):
    current_profile = Queries.getCurrentProfileByUserId(user_id)
    notifications_serialized = []

    notifications = current_profile.all_notifications.all().order_by('-created_at')
    notifications_serialized = [notification.to_dict() for notification in notifications]

    return JsonResponse({'fresh_notifications': notifications_serialized})
