from django.forms.models import BaseModelForm
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.contrib.auth.views import LoginView
from django.views.generic.edit import CreateView
from .forms import RegisterUserForm, LoginUserForm
from django.contrib.auth import login as django_login, logout

def index(request):
    return render(request, 'base/index.html')

class RegisterUser(CreateView):
    form_class = RegisterUserForm
    template_name = 'base/registration/register.html'

    def form_valid(self, form: RegisterUserForm) -> HttpResponse:
        user = form.save()
        django_login(self.request, user)
        return redirect('Home')

class LoginUser(LoginView):
    form_class = LoginUserForm
    template_name = 'base/auth/login.html'

    def get_success_url(self) -> str:
        return reverse_lazy('Home')
