"""
Inventory service - handles inventory operations.
Manages items in player inventory, buying, selling.
"""

from django.db import transaction
from game.models import (
    PlayerProfile,
    InventoryItem,
    ShopItem,
)
import logging

logger = logging.getLogger(__name__)


class InventoryServiceError(Exception):
    """Base exception for inventory service errors."""
    pass


class InventoryService:
    """Service for managing player inventory."""

    @staticmethod
    def get_inventory(profile: PlayerProfile) -> list:
        """Get player's inventory."""
        items = InventoryItem.objects.filter(
            player=profile
        ).select_related('item__category').order_by('item__name')

        result = []
        for inv_item in items:
            result.append({
                'id': inv_item.id,
                'item_id': inv_item.item.id,
                'item_name': inv_item.item.name,
                'item_slug': inv_item.item.slug,
                'quantity': inv_item.quantity,
                'price': inv_item.item.price_coins,
                'sell_price': inv_item.item.sell_price,
                'category': inv_item.item.category.name if inv_item.item.category else None,
            })

        return result

    @staticmethod
    def get_resources_inventory(profile: PlayerProfile) -> list:
        """Get player's resource inventory."""
        items = InventoryItem.objects.filter(
            player=profile,
            item__is_resource=True,
        ).select_related('item').order_by('item__name')

        result = []
        for inv_item in items:
            result.append({
                'id': inv_item.id,
                'item_id': inv_item.item.id,
                'item_name': inv_item.item.name,
                'item_slug': inv_item.item.slug,
                'quantity': inv_item.quantity,
                'price': inv_item.item.price_coins,
            })

        return result

    @staticmethod
    def get_market_inventory(profile: PlayerProfile) -> list:
        """Get items available for selling (non-resources)."""
        items = InventoryItem.objects.filter(
            player=profile,
            item__is_resource=False,
        ).select_related('item__category').order_by('item__name')

        result = []
        for inv_item in items:
            result.append({
                'id': inv_item.id,
                'item_id': inv_item.item.id,
                'item_name': inv_item.item.name,
                'item_slug': inv_item.item.slug,
                'quantity': inv_item.quantity,
                'sell_price': inv_item.item.sell_price,
                'category': inv_item.item.category.name if inv_item.item.category else None,
            })

        return result

    @staticmethod
    @transaction.atomic
    def buy_item(profile: PlayerProfile, item_id: int, quantity: int = 1) -> dict:
        """Buy an item from the shop."""
        shop_item = ShopItem.objects.filter(id=item_id).first()

        if not shop_item:
            raise InventoryServiceError("Item not found")

        total_cost = shop_item.price_coins * quantity

        if profile.coins_balance < total_cost:
            raise InventoryServiceError("Insufficient coins")

        # Deduct coins
        profile.coins_balance -= total_cost
        profile.save(update_fields=['coins_balance'])

        # Add to inventory
        inventory_item, created = InventoryItem.objects.get_or_create(
            player=profile,
            item=shop_item,
            defaults={'quantity': 0}
        )
        inventory_item.quantity += quantity
        inventory_item.save(update_fields=['quantity'])

        logger.info(f"User {profile.user.username} bought {quantity}x {shop_item.name}")

        return {
            'success': True,
            'item': shop_item.name,
            'quantity': quantity,
            'total_cost': total_cost,
            'coins_balance': profile.coins_balance,
        }

    @staticmethod
    @transaction.atomic
    def sell_item(profile: PlayerProfile, item_slug: str, quantity: int = 1) -> dict:
        """Sell an item to the market."""
        shop_item = ShopItem.objects.filter(slug=item_slug).first()

        if not shop_item:
            raise InventoryServiceError("Item not found")

        inventory_item = InventoryItem.objects.filter(
            player=profile,
            item=shop_item,
        ).first()

        if not inventory_item or inventory_item.quantity < quantity:
            raise InventoryServiceError("Not enough items in inventory")

        # Calculate sell price
        sell_price = shop_item.sell_price * quantity

        # Update inventory
        inventory_item.quantity -= quantity
        if inventory_item.quantity <= 0:
            inventory_item.delete()
        else:
            inventory_item.save(update_fields=['quantity'])

        # Add coins
        profile.coins_balance += sell_price
        profile.save(update_fields=['coins_balance'])

        logger.info(f"User {profile.user.username} sold {quantity}x {shop_item.name}")

        return {
            'success': True,
            'item': shop_item.name,
            'quantity': quantity,
            'sell_price': sell_price,
            'coins_balance': profile.coins_balance,
        }

    @staticmethod
    def get_item_count(profile: PlayerProfile, item_slug: str) -> int:
        """Get quantity of a specific item in inventory."""
        shop_item = ShopItem.objects.filter(slug=item_slug).first()
        if not shop_item:
            return 0

        inv_item = InventoryItem.objects.filter(
            player=profile,
            item=shop_item,
        ).first()

        return inv_item.quantity if inv_item else 0
