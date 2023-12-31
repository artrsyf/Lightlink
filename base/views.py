from django.forms.models import BaseModelForm
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.contrib.auth.views import LoginView
from django.views.generic.edit import CreateView
from .forms import RegisterUserForm, LoginUserForm
from django.contrib.auth import login as django_login, logout
from .tokens import account_activation_token

from django.template.loader import render_to_string
from django.contrib.sites.shortcuts import get_current_site
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import EmailMessage
from django.contrib import messages
from django.contrib.auth import get_user_model

from allauth.account.models import EmailAddress

from video_chat.utils import clearCache

def index(request):
    return render(request, 'base/index.html')

def activate(request, uidb64, token):
    User = get_user_model()
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except:
        user = None

    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        clearCache(f'cache__{user.id}__current_user', f'cache__{user.username}__current_user')

        email = user.email
        EmailAddress.objects.create(user=user, email=email, verified=True, primary=True)

        messages.success(request, "Thank you for your email confirmation.")
        django_login(request, user)
        return redirect('Home')
    else:
        messages.error(request, "Activation link is invalid!")

    return redirect('Home')

def activateEmail(request, user, to_email):
    mail_subject = "Activate your user account."
    domain = get_current_site(request).domain
    #** for local
    if domain == 'localhost':
        domain = 'localhost:8000'
    message_context = {'user': user.username,
                       'domain': domain,
                       'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                       'token': account_activation_token.make_token(user),
                       "protocol": 'https' if request.is_secure() else 'http'
                       }
    message = render_to_string("base/template_activate_account.html", message_context)
    email = EmailMessage(mail_subject, message, to=[to_email])
    if email.send():
        messages.success(request, f'Dear <b>{user}</b>, please go to you email <b>{to_email}</b> inbox and click on \
                received activation link to confirm and complete the registration. <b>Note:</b> Check your spam folder.')
    else:
        messages.error(request, f'Problem sending email to {to_email}, check if you typed it correctly.')

class RegisterUser(CreateView):
    form_class = RegisterUserForm
    template_name = 'base/registration/register.html'

    def get(self, request, *args, **kwargs):
        if self.request.user.is_authenticated:
            return redirect('Home')
        return super().get(request, *args, **kwargs)

    def form_valid(self, form: RegisterUserForm) -> HttpResponse:
        user = form.save(commit=False)
        user.is_active = False
        user.save()
        activateEmail(self.request, user, form.cleaned_data.get('email'))
        return redirect('Home')

class LoginUser(LoginView):
    form_class = LoginUserForm
    template_name = 'base/auth/login.html'

    def get_success_url(self) -> str:
        return reverse_lazy('Home')
