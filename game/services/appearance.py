"""Внешний вид зданий: игрок выбирает вариант типа здания за монеты, сброс к стандартному — бесплатно."""
import re

from game.models import APPEARANCE_CHANGE_PRICE, BuildingType, PlayerBuildingAppearance, PlayerProfile

from . import GameError
from .player import spend_coins

APPEARANCE_VERSION = 2
COLOR_SLOTS = ("wall", "roof", "window")  # стены, крыша, окна и двери
MAX_SEED = 2 ** 31 - 1
HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


def clean_appearance(value) -> dict:
    """Формат v2: {"v": 2, "shape": 0..MAX, "details": 0..MAX, "colors": {"wall", "roof", "window": "#rrggbb"} | null}.
    shape=0 — исходная форма здания (её можно просто перекрасить). Картинку по этим данным рисует фронтенд."""
    if not isinstance(value, dict) or set(value) != {"v", "shape", "details", "colors"}:
        raise GameError("appearance должен содержать ключи v, shape, details, colors")
    if value["v"] != APPEARANCE_VERSION:
        raise GameError(f"Неизвестная версия внешнего вида: {value['v']}")
    result = {"v": APPEARANCE_VERSION}
    for key in ("shape", "details"):
        seed = value[key]
        if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= MAX_SEED:
            raise GameError(f"appearance.{key} должен быть целым числом 0..{MAX_SEED}")
        result[key] = seed
    colors = value["colors"]
    if colors is None:
        result["colors"] = None
    else:
        if not isinstance(colors, dict) or set(colors) != set(COLOR_SLOTS):
            raise GameError(f"appearance.colors должен содержать {', '.join(COLOR_SLOTS)}")
        for slot in COLOR_SLOTS:
            if not isinstance(colors[slot], str) or not HEX_COLOR.match(colors[slot]):
                raise GameError(f"appearance.colors.{slot} должен быть цветом вида #rrggbb")
        result["colors"] = {slot: colors[slot].lower() for slot in COLOR_SLOTS}
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
    if appearance["shape"] == 0 and appearance["colors"] is None:
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
