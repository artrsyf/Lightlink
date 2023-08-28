from django.apps import AppConfig


class VideoChatConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'video_chat'

    def ready(self) -> None:
        import video_chat.signals
