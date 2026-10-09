from django.utils import timezone
from rest_framework import serializers
from ..models import FarmField, Cell, ShopItem
from .shop import ShopItemSerializer


class FarmFieldSerializer(serializers.Serializer):
    field = serializers.SerializerMethodField()
    grid = serializers.ListField(child=serializers.DictField(), required=False)

    def get_field(self, obj):
        field = obj["field"]
        return {
            "level": field.level,
            "grid_size": field.level * 5,
            "max_cells": getattr(field, "max_cells", field.level * field.level * 25),
            "expansion_cost_coins": getattr(field, "expansion_cost_coins", 1000 * field.level ** 2),
            "coins_needed": getattr(field, "expansion_cost_coins", 1000 * field.level ** 2),
        }


class ObjectDataField(serializers.DictField):
    """
    object_data с расшифровкой.
    """
    def to_representation(self, value):
        value = super().to_representation(value)
        if not isinstance(value, dict):
            return value

        shop_item_id = value.get("shop_item_id")
        if shop_item_id:
            cache = self.context.get("shop_item_cache") if hasattr(self, "context") else None
            shop_item = None

            if isinstance(cache, dict):
                shop_item = cache.get(shop_item_id)

            if shop_item is None:
                try:
                    shop_item = ShopItem.objects.get(id=shop_item_id)
                    if isinstance(cache, dict):
                        cache[shop_item_id] = shop_item
                except ShopItem.DoesNotExist:
                    shop_item = None

            if shop_item:
                value["plant"] = ShopItemSerializer(shop_item).data

        return value


class CellSerializer(serializers.ModelSerializer):
    row = serializers.SerializerMethodField()
    col = serializers.SerializerMethodField()

    plant = serializers.SerializerMethodField()
    harvest = serializers.SerializerMethodField()

    object_data = ObjectDataField()

    remaining_seconds = serializers.SerializerMethodField()
    is_ready = serializers.SerializerMethodField()

    class Meta:
        model = Cell
        fields = (
            "id",
            "position", "row", "col",
            "object_type",
            "object_data",
            "is_anchor", "anchor_position", "size_w", "size_h",
            "planted_at", "grow_duration_seconds",
            "remaining_seconds", "is_ready",
            "plant", "harvest",
        )
        read_only_fields = ("position",)

    def get_row(self, obj):
        grid_size = self.context.get("grid_size", 10)
        return obj.position // grid_size

    def get_col(self, obj):
        grid_size = self.context.get("grid_size", 10)
        return obj.position % grid_size

    def get_plant(self, obj):
        if obj.object_type != "field" or not obj.object_data.get("shop_item_id"):
            return None

        shop_item_id = obj.object_data["shop_item_id"]

        cache = self.context.get("shop_item_cache")
        shop_item = cache.get(shop_item_id) if isinstance(cache, dict) else None

        if shop_item is None:
            try:
                shop_item = ShopItem.objects.get(id=shop_item_id)
                if isinstance(cache, dict):
                    cache[shop_item_id] = shop_item
            except ShopItem.DoesNotExist:
                return None

        if obj.is_ready_for_harvest and shop_item.harvest_item:
            harvest = shop_item.harvest_item
            return {
                "id": shop_item.id,
                "name": harvest.name,
                "slug": harvest.slug,
                "type": "harvest",
                "is_ready": True,
                "description": f"×{shop_item.harvest_yield} шт. Продажа: {harvest.price_coins} монет/шт.",
                "grow_time_minutes": shop_item.grow_time_minutes,
            }

        return {
            "id": shop_item.id,
            "name": shop_item.name,
            "slug": shop_item.slug,
            "type": "seed",
            "is_ready": False,
            "description": shop_item.description or "Посажено",
        }

    def get_harvest(self, obj):
        if (
            obj.object_type != "field"
            or not obj.is_ready_for_harvest
            or not obj.object_data.get("shop_item_id")
        ):
            return None

        shop_item_id = obj.object_data["shop_item_id"]

        cache = self.context.get("shop_item_cache")
        shop_item = cache.get(shop_item_id) if isinstance(cache, dict) else None

        if shop_item is None:
            try:
                shop_item = ShopItem.objects.get(id=shop_item_id)
                if isinstance(cache, dict):
                    cache[shop_item_id] = shop_item
            except ShopItem.DoesNotExist:
                return None

        if not shop_item.harvest_item:
            return None

        harvest = shop_item.harvest_item
        return {
            "id": harvest.id,
            "name": harvest.name,
            "slug": harvest.slug,
            "sell_price": harvest.price_coins,
            "yield_quantity": shop_item.harvest_yield or 1,
            "image_url": f"/static/plants/{harvest.slug}.png",
            "type": "harvest",
        }

    def get_remaining_seconds(self, obj):
        if not obj.planted_at or not obj.grow_duration_seconds:
            return None
        remaining = (
            obj.planted_at
            + timezone.timedelta(seconds=obj.grow_duration_seconds)
            - timezone.now()
        ).total_seconds()
        return max(int(remaining), 0)

    def get_is_ready(self, obj):
        return bool(getattr(obj, "is_ready_for_harvest", False))
