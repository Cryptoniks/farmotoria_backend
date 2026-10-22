from rest_framework import generics
from rest_framework.response import Response

from ..models import InventoryItem, ShopItem
from ..serializers import InventoryItemSerializer, ShopItemSerializer
from ..services import inventory, storage
from ..services.extraction import accrue
from ..services.player import get_profile
from .base import GameAPIView

SHOP_ITEMS = ShopItem.objects.select_related("category", "harvest_item")


# ---------------------------------------------------------------- магазин ----
class ShopItemListView(generics.ListAPIView):
    queryset = SHOP_ITEMS.order_by("id")
    serializer_class = ShopItemSerializer


class ShopSeedsListView(generics.ListAPIView):
    queryset = SHOP_ITEMS.filter(is_seed=True).order_by("price_coins")
    serializer_class = ShopItemSerializer


class ShopHarvestListView(generics.ListAPIView):
    queryset = SHOP_ITEMS.filter(is_harvest=True).order_by("price_coins")
    serializer_class = ShopItemSerializer


class BuyItemView(GameAPIView):
    def post(self, request):
        profile, item, qty, total = inventory.buy_item(
            request.user, request.data.get("item_id"), request.data.get("quantity", 1)
        )
        return Response({
            "coins_balance": profile.coins_balance,
            "message": f"✅ Куплено {qty}×{item.name} за {total} монет",
        })


# -------------------------------------------------------- инвентарь/рынок ----
class InventoryView(GameAPIView):
    def get(self, request):
        profile = get_profile(request.user)
        accrue(profile)
        items = InventoryItem.objects.filter(player=profile, quantity__gt=0).select_related(
            "item__category", "item__harvest_item"
        )
        return Response(InventoryItemSerializer(items, many=True).data)


class ResourcesInventoryView(GameAPIView):
    def get(self, request):
        profile = get_profile(request.user)
        accrue(profile)
        items = InventoryItem.objects.filter(
            player=profile, item__is_resource=True, quantity__gt=0
        ).select_related("item__category", "item__harvest_item")
        return Response(InventoryItemSerializer(items, many=True).data)


class MarketInventoryView(GameAPIView):
    """Все товары, кроме семян, с количеством в инвентаре игрока."""

    def get(self, request):
        profile = get_profile(request.user)
        accrue(profile)
        stock = dict(InventoryItem.objects.filter(player=profile).values_list("item_id", "quantity"))
        items = ShopItem.objects.filter(is_seed=False).select_related("category").order_by(
            "category__name", "name"
        )
        return Response([
            {
                "id": item.id,
                "name": item.name,
                "sell_price_coins": item.price_coins,
                "item_slug": item.slug,
                "quantity": stock.get(item.id, 0),
                "item_type": "harvest" if item.is_harvest else ("resource" if item.is_resource else "product"),
                "category_name": item.category.name if item.category_id else "Без категории",
                "storage": item.storage,
            }
            for item in items
        ])


class SellItemView(GameAPIView):
    def post(self, request):
        profile, item, qty, total = inventory.sell_item(
            request.user, request.data.get("item_id"), request.data.get("quantity", 1)
        )
        return Response({
            "coins_balance": profile.coins_balance,
            "sold": qty,
            "total_earned": total,
            "message": f"Продано {qty}×{item.name} за {total} монет",
        })


class StorageView(GameAPIView):
    """Сарай и Склад: вместимость, заполненность и товары в каждом."""

    def get(self, request):
        profile = get_profile(request.user)
        accrue(profile)
        return Response(storage.summary(profile))
