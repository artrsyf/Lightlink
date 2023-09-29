from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinLengthValidator, MaxLengthValidator

User = get_user_model()
User._meta.get_field('email')._unique = True

class ChannelType(models.Model):
    type = models.CharField(null=False)

class Channel(models.Model):
    channel_name = models.CharField(max_length=45, null=False)
    channel_type = models.ForeignKey(ChannelType, on_delete=models.PROTECT, null=False)

class Profile(models.Model):
    profile_name = models.CharField(max_length=20, 
                                    validators=[MinLengthValidator(5), MaxLengthValidator(20)])
    user = models.OneToOneField(User, 
                                   on_delete=models.CASCADE,
                                   null=False)
    profiles = models.ManyToManyField(to='self', through="Friendship")

    channels = models.ManyToManyField(Channel, through="ChannelInfo")

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