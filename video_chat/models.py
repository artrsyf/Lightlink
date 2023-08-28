from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinLengthValidator, MaxLengthValidator

User = get_user_model()

class Profile(models.Model):
    profile_name = models.CharField(max_length=20, 
                                    validators=[MinLengthValidator(5), MaxLengthValidator(20)])
    user = models.OneToOneField(User, 
                                   on_delete=models.CASCADE,
                                   null=False)
    profiles = models.ManyToManyField(to='self', through="Friendship")

    def __str__(self) -> str:
        return f"Profile: {self.profile_name} with User ID: {self.user}"
    
class FriendRequestType(models.Model):
    type = models.CharField(null=False)

    def __str__(self) -> str:
        return f"Request type: {self.type}"
    

class Friendship(models.Model):
    sender = models.ForeignKey(Profile, on_delete=models.CASCADE, null=False, related_name='sender_id')
    receiver = models.ForeignKey(Profile, on_delete=models.CASCADE, null=False, related_name='receiver_id')
    status_type = models.ForeignKey(FriendRequestType, on_delete=models.PROTECT, null=False)

    def __str__(self) -> str:
        return f"Sender: {self.sender} to Receiver: {self.receiver} with Status: {self.status_type}"
