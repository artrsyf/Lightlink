# Generated by Django 4.2.4 on 2023-11-04 08:48

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('video_chat', '0008_alter_profile_profile_avatar'),
    ]

    operations = [
        migrations.CreateModel(
            name='NotificationType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField()),
            ],
        ),
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('notification_type', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='video_chat.notificationtype')),
                ('profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='all_notifications', to='video_chat.profile')),
            ],
        ),
    ]