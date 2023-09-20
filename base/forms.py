from django import forms
from django.forms import ModelForm, TextInput
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from captcha.fields import ReCaptchaField
from captcha.widgets import ReCaptchaV2Checkbox

class RegisterUserForm(UserCreationForm):
    username = forms.CharField(label='Login',
                               max_length=20,
                               required=True,
                               widget=forms.TextInput(attrs={}))
    email = forms.EmailField(label='Email',
                               max_length=30,
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
    
    def clean(self):
        cleaned_data = super().clean()
        if User.objects.filter(email=cleaned_data.get('email')).exists():
            #** Вынести сообщение об ошибке наружу
            NOT_UNIQUE_EMAIL_MESSAGE = "Данная почта уже используется"
            self.add_error('email', NOT_UNIQUE_EMAIL_MESSAGE)
        return cleaned_data
    
class LoginUserForm(AuthenticationForm):
    username = forms.CharField(label='Username',
                               max_length=20,
                               required=True,
                               widget=forms.TextInput(attrs={}))
    password = forms.CharField(label='Password',
                               max_length=20,
                               required=True,
                               widget=forms.PasswordInput(attrs={}))
    captcha = ReCaptchaField(label='Captcha',
                             widget=ReCaptchaV2Checkbox(),
                             error_messages={
                                'required': 'Please complete the captcha.',
                                'invalid': 'Invalid captcha. Please try again.'
                            })