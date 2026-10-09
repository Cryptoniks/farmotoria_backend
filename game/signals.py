from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver

from .models import ensure_user_skills, PlayerProfile, FieldChunk, CHUNK_SIZE, START_UNLOCKED_SIZE, STARTING_COINS


@receiver(post_save, sender=User)
def create_user_profile_and_skills(sender, instance, created, **kwargs):
    if not created:
        return

    ensure_user_skills(instance)

    profile, created = PlayerProfile.objects.get_or_create(
        user=instance,
        defaults={"coins_balance": STARTING_COINS}
    )

    if created or not FieldChunk.objects.filter(profile=profile).exists():
        # Стартовое поле: 50x50 клеток = 5x5 чанков (по 10x10)
        chunk_count_side = START_UNLOCKED_SIZE // CHUNK_SIZE  # 50/10 = 5
        objs = [
            FieldChunk(
                profile=profile,
                chunk_row=cr,
                chunk_col=cc,
                price_paid=0,
            )
            for cr in range(chunk_count_side)
            for cc in range(chunk_count_side)
        ]
        FieldChunk.objects.bulk_create(objs, ignore_conflicts=True)