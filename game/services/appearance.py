"""Внешний вид зданий: игрок выбирает вариант типа здания за монеты, сброс к стандартному — бесплатно."""
from game.models import APPEARANCE_CHANGE_PRICE, BuildingType, PlayerBuildingAppearance, PlayerProfile

from . import GameError
from .player import spend_coins

APPEARANCE_KEYS = ("c", "r", "d")  # цвета, крыша, детали — зёрна генератора на фронтенде (0 — стандарт группы)
MAX_SEED = 2 ** 31 - 1


def clean_appearance(value) -> dict:
    if not isinstance(value, dict) or set(value) != set(APPEARANCE_KEYS):
        raise GameError(f"appearance должен содержать ключи {', '.join(APPEARANCE_KEYS)}")
    result = {}
    for key in APPEARANCE_KEYS:
        seed = value[key]
        if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= MAX_SEED:
            raise GameError(f"appearance.{key} должен быть целым числом 0..{MAX_SEED}")
        result[key] = seed
    return result


def get_building_type(slug) -> BuildingType:
    try:
        return BuildingType.objects.get(slug=slug)
    except BuildingType.DoesNotExist:
        raise GameError("Тип здания не найден", status=404)


def change(profile: PlayerProfile, slug, appearance) -> tuple[PlayerBuildingAppearance, int]:
    """Профиль должен быть заблокирован. Сохраняет вид типа здания, списывает цену смены."""
    bt = get_building_type(slug)
    appearance = clean_appearance(appearance)
    if not any(appearance.values()):
        raise GameError("Это стандартный вид — его можно вернуть бесплатно")
    current = PlayerBuildingAppearance.objects.filter(profile=profile, building_type=bt).first()
    if current and current.appearance == appearance:
        raise GameError("Этот вид уже выбран")
    spend_coins(profile, APPEARANCE_CHANGE_PRICE)
    obj, _ = PlayerBuildingAppearance.objects.update_or_create(
        profile=profile, building_type=bt, defaults={"appearance": appearance}
    )
    return obj, APPEARANCE_CHANGE_PRICE


def reset(profile: PlayerProfile, slug) -> None:
    """Вернуть стандартный вид — бесплатно."""
    bt = get_building_type(slug)
    PlayerBuildingAppearance.objects.filter(profile=profile, building_type=bt).delete()


def appearances_map(profile: PlayerProfile) -> dict:
    return {
        a.building_type.slug: a.appearance
        for a in PlayerBuildingAppearance.objects.filter(profile=profile).select_related("building_type")
    }
