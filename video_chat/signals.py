from django.db.models.signals import post_save, post_delete
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