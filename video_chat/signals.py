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
        print('*SERVER RESPONSE: Session begins and user data saved')
        user = request.user
        user_id = user.id
        user_username = user.username
        request.session['user_id'] = user_id
        request.session['user_username'] = user_username
        try:
            user_profile = Profile.objects.get(user=user)
            user_profilename = user_profile.profile_name
            request.session['user_profilename'] = user_profilename
        except Exception:
            if user.is_superuser & user.is_staff:
                request.session['user_profilename'] = 'admin'
                print('*SERVER RESPONSE: Admin logged in')
            elif not user.is_superuser & user.is_staff:
                request.session['user_profilename'] = f'staff-{user_username}'
                print('*SERVER RESPONSE: Staff logged in')
            else:
                raise Exception(f'*SERVER RESPONSE: Could not match profile for logged user: {user_username}')

    else:
        print('*SERVER RESPONSE: Session begins and immediately closes')