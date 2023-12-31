from django.urls import path
from base.views import *
from django.contrib.auth.views import LogoutView
from lightlink.settings import LOGOUT_REDIRECT_URL
urlpatterns = [
    path('', index, name="Home"),
    path('login/', LoginUser.as_view(redirect_authenticated_user=True), name='Login'),
    path('sign-up/', RegisterUser.as_view(), name='Signup'),
    path('logout/', LogoutView.as_view(next_page=LOGOUT_REDIRECT_URL), name='Logout'),
    path('activate/<uidb64>/<token>', activate, name='activate')
]