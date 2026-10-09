from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from ..models import ShopItem
from ..serializers import ShopItemSerializer


class ShopItemListView(generics.ListAPIView):
    queryset = ShopItem.objects.all().order_by("id")
    serializer_class = ShopItemSerializer
    permission_classes = [IsAuthenticated]


class ShopSeedsListView(generics.ListAPIView):
    queryset = ShopItem.objects.filter(is_seed=True).order_by("price_coins")
    serializer_class = ShopItemSerializer
    permission_classes = [IsAuthenticated]


class ShopHarvestListView(generics.ListAPIView):
    queryset = ShopItem.objects.filter(is_harvest=True).order_by("price_coins")
    serializer_class = ShopItemSerializer
    permission_classes = [IsAuthenticated]


class ShopByCategoryView(generics.ListAPIView):
    serializer_class = ShopItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        category_name = self.kwargs["category"]
        return ShopItem.objects.filter(category__name=category_name).order_by("price_coins")


class PlantListView(generics.ListAPIView):
    queryset = ShopItem.objects.filter(is_seed=True).select_related("harvest_item")
    serializer_class = ShopItemSerializer
    permission_classes = [IsAuthenticated]


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def buy_item(request):
    from ..models import PlayerProfile, InventoryItem
    
    item_id = request.data.get("item_id")
    qty = int(request.data.get("quantity", 1))

    try:
        item = ShopItem.objects.get(id=item_id)
    except ShopItem.DoesNotExist:
        return Response({"detail": f"Товар ID={item_id} не найден"}, status=404)

    profile, _ = PlayerProfile.objects.get_or_create(user=request.user)
    total_price = item.buy_price * qty

    if profile.coins_balance < total_price:
        return Response({
            "detail": f"Недостаточно монет! Нужно: {total_price}, есть: {profile.coins_balance}"
        }, status=400)

    profile.coins_balance -= total_price
    profile.save()

    inv_item, _ = InventoryItem.objects.get_or_create(player=profile, item=item)
    inv_item.quantity += qty
    inv_item.save()

    return Response({
        "coins_balance": profile.coins_balance,
        "message": f"✅ Куплено {qty}×{item.name} за {total_price} монет"
    })
