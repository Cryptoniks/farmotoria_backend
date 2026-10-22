"""
Хранилища: Сарай и Склад.

Товары лежат в одном инвентаре игрока, а у товара есть признак ShopItem.storage —
в Сарае он хранится или на Складе. Вместимость Сарая (Склада) = сумма вместимостей
всех построенных Сараев (Складов) игрока с учётом их уровней. Заполненность —
сколько единиц таких товаров сейчас у игрока.
"""
from django.db.models import Sum

from game.models import BuildingPlacement, BuildingType, InventoryItem, PlayerProfile, ShopItem

from . import GameError

STORAGE_NAMES = dict(ShopItem.STORAGE_CHOICES)
STORAGE_KINDS = tuple(STORAGE_NAMES)


def capacity(profile: PlayerProfile, storage: str, exclude_id=None) -> int:
    placements = BuildingPlacement.objects.filter(
        profile=profile,
        building_type__building_type=BuildingType.TYPE_STORAGE,
        building_type__storage=storage,
    ).select_related("building_type")
    if exclude_id is not None:
        placements = placements.exclude(id=exclude_id)
    return sum(p.building_type.capacity_at(p.level) for p in placements)


def used(profile: PlayerProfile, storage: str) -> int:
    total = InventoryItem.objects.filter(player=profile, item__storage=storage).aggregate(n=Sum("quantity"))["n"]
    return total or 0


def free_space(profile: PlayerProfile, storage: str) -> int:
    return max(0, capacity(profile, storage) - used(profile, storage))


def ensure_space(profile: PlayerProfile, item: ShopItem, quantity: int) -> None:
    """Проверяет, что quantity единиц товара поместятся в его хранилище, иначе GameError."""
    free = free_space(profile, item.storage)
    if quantity > free:
        name = STORAGE_NAMES.get(item.storage, item.storage)
        raise GameError(
            f"{name}: не хватает места. Свободно {free}, нужно {quantity}. "
            f"Продайте товары на Рынке или улучшите/постройте ещё один {name.lower()}",
            storage=item.storage, free=free, need=quantity,
        )


def ensure_can_remove(profile: PlayerProfile, placement: BuildingPlacement) -> None:
    """Хранилище нельзя убрать, если оставшиеся не вместят то, что уже лежит."""
    bt = placement.building_type
    if bt.building_type != BuildingType.TYPE_STORAGE or not bt.storage:
        return
    left = capacity(profile, bt.storage, exclude_id=placement.id)
    stored = used(profile, bt.storage)
    if stored > left:
        name = STORAGE_NAMES.get(bt.storage, bt.storage)
        raise GameError(
            f"Нельзя продать: без этого здания {name.lower()} вместит {left}, а хранится {stored}. "
            "Сначала продайте часть товаров на Рынке",
            capacity_left=left, stored=stored,
        )


def summary(profile: PlayerProfile) -> dict:
    """Для API /api/storage/: по каждому хранилищу вместимость, заполненность и товары."""
    items = (
        InventoryItem.objects.filter(player=profile, quantity__gt=0)
        .select_related("item__category")
        .order_by("item__category__name", "item__name")
    )
    result = {}
    for kind in STORAGE_KINDS:
        cap = capacity(profile, kind)
        rows = [inv for inv in items if inv.item.storage == kind]
        stored = sum(inv.quantity for inv in rows)
        result[kind] = {
            "name": STORAGE_NAMES[kind],
            "capacity": cap,
            "used": stored,
            "free": max(0, cap - stored),
            "items": [{
                "item_id": inv.item_id,
                "name": inv.item.name,
                "slug": inv.item.slug,
                "category": inv.item.category.name,
                "quantity": inv.quantity,
                "sell_price": inv.item.price_coins,
            } for inv in rows],
        }
    return result
