from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .services.player import setup_new_player


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_player_on_signup(sender, instance, created, **kwargs):
    """Новый пользователь сразу получает профиль, навыки и стартовое поле."""
    if created:
        setup_new_player(instance)
