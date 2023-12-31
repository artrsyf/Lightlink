# Generated by Django 4.2.4 on 2023-11-04 10:55

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('video_chat', '0010_rename_profile_notification_owner_profile_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='NotificationStatus',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField()),
            ],
        ),
        migrations.AddField(
            model_name='notification',
            name='notification_status',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='video_chat.notificationstatus'),
            preserve_default=False,
        ),
    ]
