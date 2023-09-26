from django import forms
from django.forms import ModelForm, TextInput
from .models import Friendship, FriendRequestType, Profile, User
from django.db.models import Q

class FriendshipForm(ModelForm):
    receiver_username = forms.CharField(label='receiver_username',
                               max_length=20,
                               required=True)
    class Meta:
        model = Friendship
        fields = ['receiver_username']
        widgets = {
            "receiver_username": TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Имя пользователя'
            })
        }

    def __init__(self, *args, sender=None, **kwargs):
        super().__init__(*args, **kwargs)
        user = User.objects.get(username=sender)
        self.sender = Profile.objects.get(user=user)
        print('init', sender)

    def clean(self):
        self.cleaned_data = super().clean()
        receiver_username = self.cleaned_data.get('receiver_username')
        try:
            user = User.objects.get(username=receiver_username)
            profile = Profile.objects.get(user=user)
            print('qqqxxx', profile)
        except User.DoesNotExist:
            self.add_error('receiver_username', 'User with this username does not exist')
            return

        self.cleaned_data['receiver'] = profile
        self.cleaned_data['sender'] = self.sender
        self.cleaned_data['status_type'] = FriendRequestType.objects.get(id=1)

        if self.sender == profile:
            raise forms.ValidationError('Could not send request to your own')

        if Friendship.objects.filter(sender=self.sender, receiver=profile).exists():
            raise forms.ValidationError('Request is already sent')
    
    def save(self, commit=True):
        friendship = super().save(commit=False)

        friendship.receiver = self.cleaned_data['receiver']
        friendship.sender = self.cleaned_data['sender']
        friendship.status_type = self.cleaned_data['status_type']

        if friendship.sender == friendship.receiver:
            raise forms.ValidationError('Could not send request to your own')

        if Friendship.objects.filter(sender=friendship.sender, receiver=friendship.receiver).exists():
            raise forms.ValidationError('Request is already sent')
        
        if commit:
            friendship.save()

        return friendship
