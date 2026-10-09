from django.apps import AppConfig

class GameConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "game"

    def ready(self):
        import game.signals
        # Запуск планировщика
        from game.scheduler import start_scheduler
        start_scheduler()