# Generated by Django 4.2.4 on 2023-10-25 07:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('video_chat', '0006_profile_profile_avatar'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='profile_avatar',
            field=models.ImageField(default='default_profile_avatar.jpg', upload_to='profile_avatars'),
        ),
    ]
