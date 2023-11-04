# Generated by Django 4.2.4 on 2023-11-04 09:34

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('video_chat', '0009_notificationtype_notification'),
    ]

    operations = [
        migrations.RenameField(
            model_name='notification',
            old_name='profile',
            new_name='owner_profile',
        ),
        migrations.AddField(
            model_name='notification',
            name='sender_profile',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='all_sent_notifications', to='video_chat.profile'),
        ),
    ]
