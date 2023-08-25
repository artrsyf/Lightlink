from django import forms
from django.forms import ModelForm, TextInput
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User

class RegisterUserForm(UserCreationForm):
    username = forms.CharField(label='Login',
                               max_length=20,
                               required=True,
                               widget=forms.TextInput(attrs={}))
    email = forms.EmailField(label='Email',
                               max_length=20,
                               required=True,
                               widget=forms.TextInput(attrs={}))
    password1 = forms.CharField(label='Password',
                               max_length=20,
                               required=True,
                               widget=forms.PasswordInput(attrs={}))
    password2 = forms.CharField(label='Repeat password',
                               max_length=20,
                               required=True,
                               widget=forms.PasswordInput(attrs={}))
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
    
class LoginUserForm(AuthenticationForm):
    username = forms.CharField(label='Username',
                               max_length=20,
                               required=True,
                               widget=forms.TextInput(attrs={}))
    password = forms.CharField(label='Password',
                               max_length=20,
                               required=True,
                               widget=forms.PasswordInput(attrs={}))