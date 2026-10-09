from rest_framework import serializers
from ..models import ItemCategory, ShopItem, InventoryItem


class ItemCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemCategory
        fields = ("id", "name")


class ShopItemSerializer(serializers.ModelSerializer):
    category = ItemCategorySerializer(read_only=True)
    harvest_name = serializers.CharField(source="harvest_item.name", read_only=True, allow_null=True)
    harvest_slug = serializers.CharField(source="harvest_item.slug", read_only=True, allow_null=True)
    buy_price = serializers.IntegerField(read_only=True)

    class Meta:
        model = ShopItem
        fields = (
            "id", "name", "description", "slug", "price_coins", "buy_price", "category",
            "is_seed", "is_harvest", "is_resource", "grow_time_minutes", "harvest_yield",
            "harvest_item", "harvest_name", "harvest_slug"
        )
        read_only_fields = ("harvest_item",)


class InventoryItemSerializer(serializers.ModelSerializer):
    item = ShopItemSerializer(read_only=True)

    class Meta:
        model = InventoryItem
        fields = ("id", "item", "quantity")


class MarketItemSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="item.name", read_only=True)
    sell_price_coins = serializers.IntegerField(source="item.price_coins", read_only=True)
    item_slug = serializers.CharField(source="item.slug", read_only=True)

    class Meta:
        model = InventoryItem
        fields = ("id", "name", "sell_price_coins", "quantity", "item_slug")
