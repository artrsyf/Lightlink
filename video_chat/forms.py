from django import forms
from django.forms import ModelForm, TextInput, FileInput
from .models import Friendship, FriendRequestType, Profile, User
from django.db.models import Q

class ProfileForm(ModelForm):
    profilename = forms.CharField(label='profilename',
                                  max_length=20,
                                  required=False)
    profile_avatar = forms.ImageField()
    
    class Meta:
        model = Profile
        fields = ['profilename', 'profile_avatar']
        widgets = {
            "profilename": TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'New profilename'
            }),
            "profile_avatar": FileInput()
        }

    def __init__(self, *args, updated_profile=None, **kwargs):
        super().__init__(*args, **kwargs)
        if updated_profile == None:
            raise Exception("Can't recognize updated profile")
        self.updated_profile = updated_profile

    def clean(self):
        self.cleaned_data = super().clean()
        print(self.cleaned_data)
        profilename = self.cleaned_data.get('profilename')
        profile_avatar = self.cleaned_data.get('profile_avatar')

        previous_profilename = self.updated_profile.profile_name
        default_form_profile_avatar = self.updated_profile.profile_avatar \
            if self.updated_profile.profile_avatar != 'default_profile_avatar.jpg' else None
        if (previous_profilename == profilename and default_form_profile_avatar == profile_avatar):
            raise forms.ValidationError('Profilename is the same')
        
        if (profilename == "" or profilename[0] == " "):
            raise forms.ValidationError('Incorrect profilename')
    
    def save(self, commit=False):
        profile = super().save(commit=False)
        profile.profile_name = self.cleaned_data['profilename']
        profile.profile_avatar = self.cleaned_data['profile_avatar']

        if commit:
            profile.save()

        return profile

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
        # print('init', sender)

    def clean(self):
        self.cleaned_data = super().clean()
        receiver_username = self.cleaned_data.get('receiver_username')
        try:
            user = User.objects.get(username=receiver_username)
            profile = Profile.objects.get(user=user)
        except User.DoesNotExist:
            self.add_error('receiver_username', 'User with this username does not exist')
            return

        self.cleaned_data['receiver'] = profile
        self.cleaned_data['sender'] = self.sender
        self.cleaned_data['status_type'] = FriendRequestType.objects.get(id=1)

        if self.sender == profile:
            raise forms.ValidationError('Could not send friend request to your own')

        if Friendship.objects.filter(sender=self.sender, receiver=profile, status_type__id=1).exists():
            raise forms.ValidationError('Friend request is already sent')
        
        if Friendship.objects.filter(Q(sender=self.sender, receiver=profile, status_type__id=3) | \
                                     Q(sender=profile, receiver=self.sender, status_type__id=3)) \
                                        .exists():
            raise forms.ValidationError('Friend request is already permitted') 
    
    def save(self, commit=True):
        friendship = super().save(commit=False)

        friendship.receiver = self.cleaned_data['receiver']
        friendship.sender = self.cleaned_data['sender']
        friendship.status_type = self.cleaned_data['status_type']

        # if friendship.sender == friendship.receiver:
        #     raise forms.ValidationError('Could not send friend request to your own')

        # if Friendship.objects.filter(sender=friendship.sender, receiver=friendship.receiver).exists():
        #     raise forms.ValidationError('Friend request is already sent')
        
        # if Friendship.objects.filter(Q(sender=friendship.sender, receiver=friendship.receiver, \
        #                                status_type__id=3) | \
        #                              Q(sender=friendship.receiver, receiver=friendship.sender, \
        #                                status_type__id=3)) \
        #                                 .exists():
        #     raise forms.ValidationError('Friend request is already permitted') 
        
        if commit:
            friendship.save()

        return friendship
