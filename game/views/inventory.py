from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from ..models import PlayerProfile, InventoryItem, ShopItem
from ..serializers import InventoryItemSerializer, MarketItemSerializer


class InventoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile, _ = PlayerProfile.objects.get_or_create(user=request.user)
        items = InventoryItem.objects.filter(player=profile, quantity__gt=0).select_related("item")
        return Response(InventoryItemSerializer(items, many=True).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def market_inventory(request):
    """Получить все товары для продажи на рынке (кроме семян).
    Возвращает все товары с информацией о количестве в инвентаре."""
    profile, _ = PlayerProfile.objects.get_or_create(user=request.user)
    
    # Получаем все товары кроме семян
    all_items = ShopItem.objects.filter(
        is_seed=False
    ).select_related("category").order_by("category__name", "name")
    
    # Получаем количество в инвентаре
    inventory = InventoryItem.objects.filter(
        player=profile
    ).select_related("item")
    
    # Создаём словарь количества
    inventory_qty = {inv.item_id: inv.quantity for inv in inventory}
    
    # Формируем результат
    result = []
    for item in all_items:
        qty = inventory_qty.get(item.id, 0)
        result.append({
            "id": item.id,
            "name": item.name,
            "sell_price_coins": item.price_coins,
            "item_slug": item.slug,
            "quantity": qty,
            "item_type": "harvest" if item.is_harvest else ("resource" if item.is_resource else "product"),
            "category_name": item.category.name if item.category else "Без категории",
        })
    
    return Response(result)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def resources_inventory(request):
    """Получить ресурсы добычи из инвентаря"""
    profile, _ = PlayerProfile.objects.get_or_create(user=request.user)
    resource_items = InventoryItem.objects.filter(
        player=profile, item__is_resource=True, quantity__gt=0
    ).select_related("item")
    return Response(InventoryItemSerializer(resource_items, many=True).data)


class SellItemView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        profile, _ = PlayerProfile.objects.get_or_create(user=request.user)
        item_id = request.data.get("item_id")
        qty = int(request.data.get("quantity", 1))

        # item_id может быть как InventoryItem.id, так и ShopItem.id
        # Пробуем сначала как InventoryItem.id
        try:
            inventory_item = InventoryItem.objects.get(
                id=item_id, player=profile, quantity__gte=qty
            )
        except InventoryItem.DoesNotExist:
            # Пробуем как ShopItem.id - ищем запись в инвентаре по товару
            try:
                inventory_item = InventoryItem.objects.get(
                    item_id=item_id, player=profile, quantity__gte=qty
                )
            except InventoryItem.DoesNotExist:
                return Response({"detail": "Товар не найден в инвентаре"}, status=400)

        price_per_item = inventory_item.item.price_coins
        total = price_per_item * qty

        profile.coins_balance += total
        profile.save()

        inventory_item.quantity -= qty
        if inventory_item.quantity <= 0:
            inventory_item.delete()
        else:
            inventory_item.save()

        return Response({
            "coins_balance": profile.coins_balance,
            "sold": qty,
            "total_earned": total,
            "message": f"Продано {qty}×{inventory_item.item.name} за {total} монет"
        })
