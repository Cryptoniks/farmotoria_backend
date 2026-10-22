"""Инвентарь, покупка и продажа. Изменения количества атомарные (F-выражения)."""
from django.db import transaction
from django.db.models import F

from game.models import InventoryItem, PlayerProfile, ShopItem

from . import GameError, storage
from .player import add_coins, lock_profile, spend_coins


def add_item(profile: PlayerProfile, item: ShopItem, quantity: int) -> None:
    if quantity <= 0:
        return
    inv, created = InventoryItem.objects.get_or_create(
        player=profile, item=item, defaults={"quantity": quantity}
    )
    if not created:
        InventoryItem.objects.filter(pk=inv.pk).update(quantity=F("quantity") + quantity)


def available_quantities(profile: PlayerProfile, item_ids) -> dict[int, int]:
    return dict(
        InventoryItem.objects.filter(player=profile, item_id__in=list(item_ids))
        .values_list("item_id", "quantity")
    )


def remove_item(profile: PlayerProfile, item: ShopItem, quantity: int) -> None:
    """Списать предметы; если не хватает — GameError. Пустые записи удаляются."""
    if quantity <= 0:
        return
    updated = InventoryItem.objects.filter(
        player=profile, item=item, quantity__gte=quantity
    ).update(quantity=F("quantity") - quantity)
    if not updated:
        raise GameError(f"Недостаточно: {item.name}")
    InventoryItem.objects.filter(player=profile, item=item, quantity__lte=0).delete()


def parse_quantity(value, default: int = 1) -> int:
    try:
        quantity = int(value if value is not None else default)
    except (TypeError, ValueError):
        raise GameError("Некорректное количество")
    if quantity <= 0:
        raise GameError("Количество должно быть больше 0")
    return quantity


def buy_item(user, item_id, quantity) -> tuple[PlayerProfile, ShopItem, int, int]:
    quantity = parse_quantity(quantity)
    try:
        item = ShopItem.objects.get(id=item_id)
    except (ShopItem.DoesNotExist, ValueError, TypeError):
        raise GameError(f"Товар ID={item_id} не найден", status=404)

    total = item.buy_price * quantity
    with transaction.atomic():
        profile = lock_profile(user)
        if profile.coins_balance < total:
            raise GameError(f"Недостаточно монет! Нужно: {total}, есть: {profile.coins_balance}")
        storage.ensure_space(profile, item, quantity)
        spend_coins(profile, total)
        add_item(profile, item, quantity)
    return profile, item, quantity, total


def sell_item(user, item_id, quantity) -> tuple[PlayerProfile, ShopItem, int, int]:
    """item_id может быть как InventoryItem.id, так и ShopItem.id (так шлёт фронтенд)."""
    quantity = parse_quantity(quantity)
    with transaction.atomic():
        profile = lock_profile(user)
        inv = (
            InventoryItem.objects.select_related("item").filter(id=item_id, player=profile).first()
            or InventoryItem.objects.select_related("item").filter(item_id=item_id, player=profile).first()
        )
        if not inv or inv.quantity < quantity:
            raise GameError("Товар не найден в инвентаре")
        total = inv.item.price_coins * quantity
        remove_item(profile, inv.item, quantity)
        add_coins(profile, total)
    return profile, inv.item, quantity, total
