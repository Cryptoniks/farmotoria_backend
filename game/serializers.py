from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import serializers
from django.utils.timezone import timedelta

from .models import (
    PlayerProfile, Cell, InventoryItem, ShopItem, ItemCategory
)

# =========================
# Регистрация пользователя
# =========================
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ("username", "email", "password")

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
            password=validated_data["password"],
        )

# =========================
# Профиль игрока
# =========================
class PlayerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlayerProfile
        fields = ("coins_balance", "level", "exp")

# =========================
# Категории товаров
# =========================
class ItemCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemCategory
        fields = ("id", "name")

# =========================
# Товар (семена или урожай)
# =========================
class ShopItemSerializer(serializers.ModelSerializer):
    category = ItemCategorySerializer(read_only=True)
    harvest_name = serializers.CharField(source='harvest_item.name', read_only=True, allow_null=True)
    harvest_slug = serializers.CharField(source='harvest_item.slug', read_only=True, allow_null=True)

    class Meta:
        model = ShopItem
        fields = (
            "id",
            "name",
            "description",
            "slug",
            "price_coins",
            "category",
            "is_seed",
            "is_harvest",
            "grow_time_minutes",
            "harvest_yield",
            "harvest_item",
            "harvest_name", 
            "harvest_slug"
        )
        read_only_fields = ("harvest_item",)

# =========================
# Клетка на ферме
# =========================
class CellSerializer(serializers.ModelSerializer):
    plant = serializers.SerializerMethodField()  # Семя при посадке
    harvest = serializers.SerializerMethodField()  # ✅ Урожай при готовности
    planted_at = serializers.DateTimeField(read_only=True)
    ready_at = serializers.SerializerMethodField()
    remaining_seconds = serializers.SerializerMethodField()
    is_ready = serializers.SerializerMethodField()  # ✅ Готовность

    class Meta:
        model = Cell
        fields = (
            "id", "row", "col", "plant", "harvest", "planted_at",
            "ready_at", "remaining_seconds", "is_ready"
        )

    def get_plant(self, obj):
        if not obj.shop_item or not obj.shop_item.is_seed:
            return None
        
        # ✅ ГОТОВО: используем harvest_slug вместо slug семян!
        if obj.is_ready_for_harvest and obj.shop_item.harvest_item:
            harvest = obj.shop_item.harvest_item
            return {
                "id": obj.shop_item.id,
                "name": harvest.name,           # "Пшеница"
                "description": f"×{obj.shop_item.harvest_yield} шт. Продажа: {harvest.price_coins} монет/шт.",
                "grow_time_minutes": obj.shop_item.grow_time_minutes,
                "seed_price": obj.shop_item.price_coins,
                "slug": harvest.slug,           # ✅ "wheat-harvest" !!!
                "type": "harvest",
                "is_ready": True
            }
        
        # РАСТЕТ: slug семян
        return {
            "id": obj.shop_item.id,
            "name": obj.shop_item.name,     # "Семена пшеницы"
            "description": obj.shop_item.description or "Посажено",
            "grow_time_minutes": obj.shop_item.grow_time_minutes,
            "seed_price": obj.shop_item.price_coins,
            "slug": obj.shop_item.slug,     # "wheat"
            "type": "seed", 
            "is_ready": False
        }

    def get_harvest(self, obj):
        """✅ Урожай (когда готово)"""
        if not obj.is_ready_for_harvest or not obj.shop_item.harvest_item:
            return None
        harvest = obj.shop_item.harvest_item
        return {
            "id": harvest.id,
            "name": harvest.name,
            "description": getattr(harvest, "description", f"Продажа: {harvest.price_coins} монет"),
            "sell_price": harvest.price_coins,
            "yield_quantity": obj.shop_item.harvest_yield or 1,
            "image_url": f"/static/plants/{harvest.slug}.png",
            "type": "harvest"
        }

    def get_ready_at(self, obj):
        if not obj.planted_at or obj.grow_duration_seconds is None:
            return None
        return (obj.planted_at + timezone.timedelta(seconds=obj.grow_duration_seconds)).isoformat()

    def get_remaining_seconds(self, obj):
        if not obj.planted_at or obj.grow_duration_seconds is None:
            return None
        remaining = (obj.planted_at + timezone.timedelta(seconds=obj.grow_duration_seconds) - timezone.now()).total_seconds()
        return max(int(remaining), 0)

    def get_is_ready(self, obj):
        return obj.is_ready_for_harvest

# =========================
# Инвентарь игрока
# =========================
class InventoryItemSerializer(serializers.ModelSerializer):
    item = ShopItemSerializer(read_only=True)

    class Meta:
        model = InventoryItem
        fields = ("id", "item", "quantity")

# =========================
# Инвентарь для рынка
# =========================
class MarketItemSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="item.name", read_only=True)
    sell_price_coins = serializers.IntegerField(source="item.price_coins", read_only=True)
    item_slug = serializers.CharField(source="item.slug", read_only=True)

    class Meta:
        model = InventoryItem
        fields = ("id", "name", "sell_price_coins", "quantity", "item_slug")