"""Профиль игрока: создание нового игрока, монеты, блокировка строки профиля."""
from django.db.models import F

from game.models import (
    CHUNK_SIZE,
    START_UNLOCKED_SIZE,
    STARTING_COINS,
    FieldChunk,
    PlayerProfile,
    ensure_user_skills,
)

from . import GameError


def setup_new_player(user) -> PlayerProfile:
    """Профиль + стартовые навыки + бесплатное стартовое поле (5x5 чанков)."""
    profile, _ = PlayerProfile.objects.get_or_create(
        user=user, defaults={"coins_balance": STARTING_COINS}
    )
    ensure_user_skills(user)

    side = START_UNLOCKED_SIZE // CHUNK_SIZE
    FieldChunk.objects.bulk_create(
        [
            FieldChunk(profile=profile, chunk_row=r, chunk_col=c, price_paid=0)
            for r in range(side)
            for c in range(side)
        ],
        ignore_conflicts=True,
    )
    return profile


def get_profile(user) -> PlayerProfile:
    """Профиль текущего пользователя (создаётся, если его ещё нет)."""
    try:
        return user.profile
    except PlayerProfile.DoesNotExist:
        return setup_new_player(user)


def lock_profile(user) -> PlayerProfile:
    """Профиль с блокировкой строки — использовать внутри transaction.atomic()."""
    profile = get_profile(user)
    return PlayerProfile.objects.select_for_update().get(pk=profile.pk)


def spend_coins(profile: PlayerProfile, amount: int) -> None:
    """Списать монеты. Профиль должен быть получен через lock_profile()."""
    if amount < 0:
        raise ValueError("amount must be >= 0")
    if profile.coins_balance < amount:
        raise GameError("Недостаточно монет", need=amount, have=profile.coins_balance)
    profile.coins_balance -= amount
    profile.save(update_fields=["coins_balance"])


def add_coins(profile: PlayerProfile, amount: int) -> None:
    if amount < 0:
        raise ValueError("amount must be >= 0")
    PlayerProfile.objects.filter(pk=profile.pk).update(coins_balance=F("coins_balance") + amount)
    profile.refresh_from_db(fields=["coins_balance"])
