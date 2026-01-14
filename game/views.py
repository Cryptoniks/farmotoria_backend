from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum, Value, Q
from django.db.models.functions import Coalesce

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated

from .models import (
    PlayerProfile, Cell, InventoryItem, ShopItem, ItemCategory,
    UserSkill, ensure_user_skills
)
from .serializers import (
    RegisterSerializer, PlayerProfileSerializer,
    CellSerializer, InventoryItemSerializer, ShopItemSerializer, MarketItemSerializer
)

# =========================
# Простые вьюшки
# =========================
class FarmotoriaPingView(APIView):
    def get(self, request):
        return Response({"project": "Farmotoria", "message": "pong"})

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile, _ = PlayerProfile.objects.get_or_create(user=request.user)
        user_skills = ensure_user_skills(request.user)

        return Response({
            "id": request.user.id,
            "username": request.user.username,
            "email": request.user.email,
            "coins_balance": profile.coins_balance,
            "level": profile.level,
            "exp": profile.exp,
            "skills": [
                {
                    "id": us.id,
                    "name": us.skill.name,
                    "level": us.level,
                    "exp": us.exp,
                    "exp_to_next": us.exp_to_next,
                    "max_level": us.skill.max_level,
                    "effect_name": us.skill.effect_name,
                    "effect_value_per_level": us.skill.effect_value_per_level,
                }
                for us in user_skills
            ],
        })

# =========================
# Shop Items (семена/урожай)
# =========================
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
        category_name = self.kwargs['category']
        return ShopItem.objects.filter(
            category__name=category_name
        ).order_by('price_coins')

# =========================
# Клетки на ферме
# =========================
class CellListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CellSerializer

    def get_queryset(self):
        return Cell.objects.filter(owner=self.request.user)
    
class CellActionView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        row = request.data.get("row")
        col = request.data.get("col")
        plant_id = request.data.get("plant_id")
        auto_buy = request.data.get("auto_buy", False)

        profile, _ = PlayerProfile.objects.get_or_create(user=request.user)
        cell, _ = Cell.objects.get_or_create(owner=request.user, row=row, col=col)
        
        # ✅ Инициализируем навыки ОДИН РАЗ в начале!
        user_skills = ensure_user_skills(request.user)

        # 🌾 СБОР УРОЖАЯ (plant_id === null)
        if plant_id is None:
            # Проверяем готовность
            if not cell.is_ready_for_harvest:
                return Response(
                    {"detail": "Растение не созрело"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            harvest_item = cell.shop_item.harvest_item
            if not harvest_item:
                return Response(
                    {"detail": "Нет связанного урожая"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Добавляем урожай
            yield_qty = cell.shop_item.harvest_yield or 1
            inv_item, _ = InventoryItem.objects.get_or_create(
                player=profile, 
                item=harvest_item
            )
            inv_item.quantity += yield_qty
            inv_item.save()

            # ✅ EXP: +1 к профилю И навыку "Земледелие"
            exp_gain = 1
            profile.exp += exp_gain
            
            # Навык "Земледелие" — используйте готовый метод!
            farming_skill = next((us for us in user_skills if us.skill.name == "Земледелие"), None)
            if farming_skill:
                farming_skill.add_exp(exp_gain)  # ✅ Автоматически обновляет exp, level
            
            # Level up профиля
            required_exp = profile.level * 100
            if profile.exp >= required_exp:
                profile.exp -= required_exp
                profile.level += 1
            
            profile.save()

            # Сброс клетки
            cell.shop_item = None
            cell.planted_at = None
            cell.grow_duration_seconds = None
            cell.save()

            return Response({
                "cell": CellSerializer(cell).data,
                "harvest_added": {
                    "item": harvest_item.name,
                    "quantity": yield_qty,
                    "exp_gained": exp_gain
                },
                "profile": {
                    "exp": profile.exp,
                    "level": profile.level,
                    "coins_balance": profile.coins_balance
                }
            })

        # 🌱 ПОСАДКА СЕМЯН
        try:
            shop_item = ShopItem.objects.get(id=plant_id, is_seed=True)
        except ShopItem.DoesNotExist:
            return Response({"detail": "Семя не найдено"}, status=400)

        # Семена из инвентаря
        inv_item, _ = InventoryItem.objects.get_or_create(
            player=profile, 
            item=shop_item
        )

        # Автопокупка если нет семян
        if inv_item.quantity <= 0:
            if not auto_buy or profile.coins_balance < shop_item.price_coins:
                return Response({"detail": "Недостаточно семян или монет"}, status=400)
            
            # Покупаем 1 семя
            profile.coins_balance -= shop_item.price_coins
            inv_item.quantity += 1

        # Списываем 1 семя
        inv_item.quantity -= 1
        if inv_item.quantity <= 0:
            inv_item.delete()
        else:
            inv_item.save()

        # ✅ БОНУС ОТ НАВЫКА "Земледелие" (user_skills уже готова!)
        growth_skill = next((us for us in user_skills if us.skill.name == "Земледелие"), None)
        
        time_reduction_percent = 0
        if growth_skill:
            # effect_value_per_level из модели Skill
            time_reduction_percent = growth_skill.level * growth_skill.skill.effect_value_per_level
            time_reduction_percent = min(time_reduction_percent, 75)  # Макс -75%

        # Время роста с бонусом
        base_seconds = shop_item.grow_time_minutes * 60
        reduction_seconds = int(base_seconds * (time_reduction_percent / 100))
        final_duration = max(base_seconds - reduction_seconds, 30)  # Минимум 30 сек

        # Посадка с бонусом
        cell.shop_item = shop_item
        cell.planted_at = timezone.now()
        cell.grow_duration_seconds = final_duration
        cell.save()

        return Response({
            "cell": CellSerializer(cell).data,
            "seeds_remaining": inv_item.quantity if hasattr(inv_item, 'quantity') else 0,
            "growth_bonus": {
                "skill_level": growth_skill.level if growth_skill else 0,
                "effect_value_per_level": growth_skill.skill.effect_value_per_level if growth_skill else 0,
                "percent_reduction": round(time_reduction_percent, 1),
                "original_minutes": shop_item.grow_time_minutes,
                "final_minutes": round(final_duration / 60, 1)
            },
            "message": f"✅ Посажено! ⏱️ {shop_item.grow_time_minutes} → {round(final_duration/60,1)} мин"
        })
    
class PlantListView(generics.ListAPIView):
    queryset = ShopItem.objects.filter(is_seed=True).select_related('harvest_item')
    serializer_class = ShopItemSerializer
    permission_classes = [IsAuthenticated]

# =========================
# Инвентарь игрока
# =========================
class InventoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = PlayerProfile.objects.get(user=request.user)
        items = InventoryItem.objects.filter(player=profile, quantity__gt=0).select_related("item")
        return Response(InventoryItemSerializer(items, many=True).data)

# =========================
# Рынок (продажа урожая)
# =========================
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def market_inventory(request):
    profile = PlayerProfile.objects.get(user=request.user)
    harvest_items = InventoryItem.objects.filter(
        player=profile,
        item__is_harvest=True,
        quantity__gt=0
    ).select_related("item")

    return Response(MarketItemSerializer(harvest_items, many=True).data)

class SellItemView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        profile = PlayerProfile.objects.get(user=request.user)
        item_id = request.data.get("item_id")  # InventoryItem ID!
        qty = int(request.data.get("quantity", 1))

        try:
            # ✅ InventoryItem ID
            inventory_item = InventoryItem.objects.get(
                id=item_id,
                player=profile,
                quantity__gte=qty
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
    
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def buy_item(request):
    item_id = request.data.get("item_id")
    qty = int(request.data.get("quantity", 1))
    
    try:
        item = ShopItem.objects.get(id=item_id)
    except ShopItem.DoesNotExist:
        return Response({"detail": f"Товар ID={item_id} не найден"}, status=404)
    
    profile = PlayerProfile.objects.get(user=request.user)
    total_price = item.price_coins * qty
    
    if profile.coins_balance < total_price:
        return Response({
            "detail": f"Недостаточно монет! Нужно: {total_price}, есть: {profile.coins_balance}"
        }, status=400)
    
    # ✅ Покупка
    profile.coins_balance -= total_price
    profile.save()
    
    inv_item, _ = InventoryItem.objects.get_or_create(
        player=profile, item=item
    )
    inv_item.quantity += qty
    inv_item.save()
    
    return Response({
        "coins_balance": profile.coins_balance,
        "message": f"✅ Куплено {qty}×{item.name} за {total_price} монет"
    })