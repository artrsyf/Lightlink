from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinLengthValidator, MaxLengthValidator
import os

User = get_user_model()
User._meta.get_field('email')._unique = True

class ChannelType(models.Model):
    type = models.CharField(null=False)

class Channel(models.Model):
    channel_name = models.CharField(max_length=45, null=False)
    channel_type = models.ForeignKey(ChannelType, on_delete=models.PROTECT, null=False)

    def to_dict(self):
        return {
            'id': self.id,
            'channel_name': self.channel_name,
            'channel_type_id': self.channel_type.id
        }
    
def avatar_upload_path(instance, filename):
    CONST_DIRECTORY_PATH = 'profile_avatars/'

    extension = os.path.splitext(filename)[1]
    new_filename = f"{instance.user.username}{extension}"

    return CONST_DIRECTORY_PATH + new_filename

class Profile(models.Model):
    profile_name = models.CharField(max_length=20, 
                                    validators=[MinLengthValidator(5), MaxLengthValidator(20)])
    user = models.OneToOneField(User, 
                                   on_delete=models.CASCADE,
                                   null=False)
    profiles = models.ManyToManyField(to='self', through="Friendship")

    channels = models.ManyToManyField(Channel, through="ChannelInfo")

    profile_avatar = models.ImageField(default='default_profile_avatar.jpg', upload_to=avatar_upload_path)

    def to_dict(self):
        return {
            'id': self.id,
            'profilename': self.profile_name,
            'profile_avatar_url': self.profile_avatar.url,
            'user_id': self.user.id,
        }

    def __str__(self) -> str:
        return f"Profile: {self.profile_name} with User ID: {self.user.id}"
    
class FriendRequestType(models.Model):
    type = models.CharField(null=False)

    def __str__(self) -> str:
        return f"Request type: {self.type}"
    
class Friendship(models.Model):
    sender = models.ForeignKey(Profile, on_delete=models.CASCADE, null=False, related_name='s_friendships')
    receiver = models.ForeignKey(Profile, on_delete=models.CASCADE, null=False, related_name='r_friendships')
    status_type = models.ForeignKey(FriendRequestType, on_delete=models.PROTECT, null=False)

    def __str__(self) -> str:
        return f"Sender: {self.sender} to Receiver: {self.receiver} with Status: {self.status_type}"
    
class ChannelInfo(models.Model):
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE, null=False, related_name='channel_infos')
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, null=False, related_name='channel_infos')

class Message(models.Model):
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE, null=False, related_name='all_messages')
    profile = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, related_name='all_messages')
    content = models.TextField(null=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def to_dict(self):
        return {
            'id': self.id,
            'channel_id': self.channel.id,
            'profile_id': self.profile.id if self.profile else None,
            'profilename': self.profile.profile_name if self.profile else None,
            'content': self.content,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
        } 