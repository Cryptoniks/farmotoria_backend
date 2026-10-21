from django.apps import AppConfig


class GameConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "game"
    verbose_name = "Игра"

    def ready(self):
        from . import signals  # noqa: F401
