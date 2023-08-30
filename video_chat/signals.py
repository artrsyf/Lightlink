from django.db.models.signals import post_save, post_delete
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Profile 

@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(
            user=instance,
            profile_name=instance.username
        )

@receiver(post_delete, sender=User)
def delete_profile(sender, instance, **kwargs):
    Profile.objects.filter(user=instance).delete()

@receiver(user_logged_in)
def set_logged_user_settings(sender, request, user, **kwargs):
    if user.is_authenticated:
        print('SERVER RESPONSE: SESSION BEGINS AND USER DATA SAVED')
        user = request.user
        user_id = user.id
        user_username = user.username
        request.session['user_id'] = user_id
        request.session['user_username'] = user_username
    else:
        print('SERVER RESPONSE: SESSION BEGINS AND IMMEDIATELY CLOSES')