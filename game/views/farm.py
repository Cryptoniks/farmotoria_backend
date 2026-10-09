from django.db import transaction
from django.utils import timezone
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import ListAPIView

from ..models import (
    AreaLock, BuildingType, PlayerProfile, Cell, ShopItem, InventoryItem, FarmField,
    Skill, ensure_user_skills
)
from ..serializers import CellSerializer
from .helpers import is_cell_locked, iter_rect


class FarmFieldView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile, _ = PlayerProfile.objects.get_or_create(user=request.user)
        field, _ = FarmField.objects.get_or_create(profile=profile)

        grid_size = field.level * 5

        cells_qs = list(Cell.objects.filter(profile=profile).values(
            "position", "object_type", "object_data",
            "planted_at", "grow_duration_seconds",
            "is_anchor", "anchor_position", "size_w", "size_h",
        ))

        shop_item_ids = set()
        for cell in cells_qs:
            shop_item_id = cell.get("object_data", {}).get("shop_item_id")
            if shop_item_id:
                shop_item_ids.add(shop_item_id)

        shop_item_cache = {}
        if shop_item_ids:
            for item in ShopItem.objects.filter(id__in=shop_item_ids):
                shop_item_cache[item.id] = item

        locks_vals = list(
            AreaLock.objects.filter(profile=profile, is_unlocked=False).values(
                "id", "row_start", "col_start", "rows", "cols", "unlock_cost"
            )
        )

        grid = [[{
            "row": r, "col": c,
            "locked": False,
            "lock_id": None,
            "unlock_cost": None,
            "cell": None,
        } for c in range(grid_size)] for r in range(grid_size)]

        for lock in locks_vals:
            for r in range(lock["row_start"], lock["row_start"] + lock["rows"]):
                for c in range(lock["col_start"], lock["col_start"] + lock["cols"]):
                    if 0 <= r < grid_size and 0 <= c < grid_size:
                        grid[r][c]["locked"] = True
                        grid[r][c]["lock_id"] = lock["id"]
                        grid[r][c]["unlock_cost"] = lock["unlock_cost"]

        for cell in cells_qs:
            r = cell["position"] // grid_size
            c = cell["position"] % grid_size
            if 0 <= r < grid_size and 0 <= c < grid_size:
                grid[r][c]["cell"] = cell

        available_buildings = list(
            BuildingType.objects.values("id", "name", "slug", "building_type", "width", "height", "price")
        )

        return Response({
            "field": {
                "level": field.level,
                "grid_size": grid_size,
                "max_cells": field.max_cells,
                "expansion_cost_coins": field.expansion_cost_coins,
            },
            "coins_balance": profile.coins_balance,
            "grid": grid,
            "locks": locks_vals,
            "available_buildings": available_buildings,
        })


class ExpandFieldView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        profile = PlayerProfile.objects.select_for_update().get(user=request.user)
        field = FarmField.objects.select_for_update().get(profile=profile)

        if profile.coins_balance < field.expansion_cost_coins:
            return Response({"detail": "Недостаточно монет"}, status=400)

        profile.coins_balance -= field.expansion_cost_coins
        field.level += 1
        field.max_cells = field.level * field.level * 25
        field.expansion_cost_coins = int(1000 * field.level ** 2)

        field.save()
        profile.save()

        return Response({
            "new_level": field.level,
            "new_size": field.level * 5,
            "max_cells": field.max_cells,
            "coins_balance": profile.coins_balance,
            "next_cost": field.expansion_cost_coins,
            "message": f"Поле расширено до уровня {field.level} ({field.level * 5}x{field.level * 5})!"
        })


class PlaceObjectView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        try:
            row = int(request.data.get("row", 0))
            col = int(request.data.get("col", 0))
            obj_type = request.data.get("object_type", "field")
            obj_data = request.data.get("object_data", {})
        except (TypeError, ValueError) as e:
            return Response({"detail": f"Некорректные параметры: {e}"}, status=400)

        profile = PlayerProfile.objects.select_for_update().get(user=request.user)
        field = FarmField.objects.get(profile=profile)
        grid_size = field.level * 5

        if row < 0 or col < 0 or row >= grid_size or col >= grid_size:
            return Response({"detail": "Координаты вне границ поля"}, status=400)

        locks = list(AreaLock.objects.filter(profile=profile, is_unlocked=False))
        lock = is_cell_locked(locks, row, col)
        if lock:
            return Response({
                "detail": "Клетка заблокирована",
                "lock_id": lock.id,
                "unlock_cost": lock.unlock_cost
            }, status=400)

        position = row * grid_size + col

        if Cell.objects.filter(profile=profile, position=position).exists():
            return Response({"detail": "Клетка занята"}, status=400)

        cell = Cell.objects.create(
            profile=profile,
            position=position,
            object_type=obj_type,
            object_data=obj_data,
            is_anchor=True,
            anchor_position=position,
            size_w=1,
            size_h=1,
        )

        if obj_type == "field":
            shop_item_id = obj_data.get("shop_item_id")
            if not shop_item_id:
                return Response({"detail": "Для поля нужен shop_item_id"}, status=400)

            try:
                shop_item = ShopItem.objects.get(id=shop_item_id, is_seed=True)
            except ShopItem.DoesNotExist:
                return Response({"detail": "Семя не найдено"}, status=400)

            auto_buy = bool(request.data.get("auto_buy", False))
            inv_item, _ = InventoryItem.objects.get_or_create(player=profile, item=shop_item)

            if inv_item.quantity <= 0:
                if not auto_buy or profile.coins_balance < shop_item.price_coins:
                    return Response({"detail": "Недостаточно семян или монет"}, status=400)
                profile.coins_balance -= shop_item.price_coins
                inv_item.quantity += 1

            inv_item.quantity -= 1
            if inv_item.quantity <= 0:
                inv_item.delete()
            else:
                inv_item.save()

            user_skills = ensure_user_skills(request.user)
            growth_skill = next((us for us in user_skills if us.skill.name == "Земледелие"), None)
            time_reduction_percent = (growth_skill.level * growth_skill.skill.effect_value_per_level) if growth_skill else 0
            time_reduction_percent = min(time_reduction_percent, 75)

            base_seconds = (shop_item.grow_time_minutes or 1) * 60
            reduction_seconds = int(base_seconds * (time_reduction_percent / 100))
            final_duration = max(base_seconds - reduction_seconds, 30)

            cell.planted_at = timezone.now()
            cell.grow_duration_seconds = final_duration
            cell.object_data = {"shop_item_id": shop_item_id}

            # Опыт начисляется только за сбор урожая

            growth_bonus = {
                "percent_reduction": time_reduction_percent,
                "final_duration": final_duration
            }
        else:
            growth_bonus = None

        cell.save()

        serializer = CellSerializer(cell, context={"grid_size": grid_size})
        return Response({
            "success": True,
            "position": position,
            "row": row,
            "col": col,
            "cell": serializer.data,
            "coins_balance": profile.coins_balance,
            "growth_bonus": growth_bonus
        })


class PlaceBuildingView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        try:
            row = int(request.data.get("row", 0))
            col = int(request.data.get("col", 0))
            building_id = int(request.data.get("building_id", 0))
        except (TypeError, ValueError) as e:
            return Response({"detail": f"Некорректные параметры: {e}"}, status=400)

        profile = PlayerProfile.objects.select_for_update().get(user=request.user)
        field = FarmField.objects.get(profile=profile)
        grid_size = field.level * 5

        try:
            building = BuildingType.objects.get(id=building_id)
        except BuildingType.DoesNotExist:
            return Response({"detail": "Тип здания не найден"}, status=404)

        w, h = building.width, building.height

        if row < 0 or col < 0 or row + h > grid_size or col + w > grid_size:
            return Response({"detail": "Здание выходит за границы поля"}, status=400)

        if profile.coins_balance < building.price:
            return Response({"detail": "Недостаточно монет"}, status=400)

        locks = list(AreaLock.objects.filter(profile=profile, is_unlocked=False))
        for r, c in iter_rect(row, col, h, w):
            lock = is_cell_locked(locks, r, c)
            if lock:
                return Response({
                    "detail": "Часть области заблокирована",
                    "lock_id": lock.id,
                    "unlock_cost": lock.unlock_cost
                }, status=400)

        positions = [(r * grid_size + c) for r, c in iter_rect(row, col, h, w)]
        if Cell.objects.filter(profile=profile, position__in=positions).exists():
            return Response({"detail": "Место занято"}, status=400)

        profile.coins_balance -= building.price
        profile.save()

        anchor_pos = row * grid_size + col

        cells_to_create = []
        for r, c in iter_rect(row, col, h, w):
            pos = r * grid_size + c
            cells_to_create.append(Cell(
                profile=profile,
                position=pos,
                object_type="building",
                object_data={"building_id": building.id, "slug": building.slug},
                is_anchor=(pos == anchor_pos),
                anchor_position=anchor_pos,
                size_w=w,
                size_h=h,
            ))

        Cell.objects.bulk_create(cells_to_create)

        return Response({
            "success": True,
            "coins_balance": profile.coins_balance,
            "building": {
                "id": building.id,
                "slug": building.slug,
                "building_type": building.building_type,
                "width": w,
                "height": h,
                "anchor_row": row,
                "anchor_col": col
            }
        })


class RemoveBuildingView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        profile = PlayerProfile.objects.select_for_update().get(user=request.user)
        field = FarmField.objects.get(profile=profile)
        grid_size = field.level * 5

        try:
            row = int(request.data.get("row", 0))
            col = int(request.data.get("col", 0))
        except (TypeError, ValueError) as e:
            return Response({"detail": f"Некорректные параметры: {e}"}, status=400)

        anchor_pos = row * grid_size + col

        anchor_cell = Cell.objects.filter(
            profile=profile,
            position=anchor_pos,
            object_type="building",
            is_anchor=True,
        ).first()

        if not anchor_cell:
            return Response({"detail": "Здание (якорь) не найдено"}, status=404)

        building_id = anchor_cell.object_data.get("building_id")
        if not building_id:
            return Response({"detail": "building_id отсутствует"}, status=400)

        try:
            building = BuildingType.objects.get(id=building_id)
        except BuildingType.DoesNotExist:
            return Response({"detail": "Тип здания не найден"}, status=404)

        Cell.objects.filter(
            profile=profile,
            object_type="building",
            anchor_position=anchor_pos,
        ).delete()

        profile.coins_balance += building.price
        profile.save()

        return Response({
            "success": True,
            "coins_balance": profile.coins_balance,
            "refunded": building.price,
            "anchor_row": row,
            "anchor_col": col,
        })


class UnlockAreaView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        profile = PlayerProfile.objects.select_for_update().get(user=request.user)
        lock_id = request.data.get("lock_id")

        try:
            lock = AreaLock.objects.select_for_update().get(profile=profile, id=lock_id)
        except AreaLock.DoesNotExist:
            return Response({"detail": "Lock не найден"}, status=404)

        if lock.is_unlocked:
            return Response({"detail": "Уже разблокировано"}, status=400)

        if profile.coins_balance < lock.unlock_cost:
            return Response({"detail": "Недостаточно монет"}, status=400)

        profile.coins_balance -= lock.unlock_cost
        profile.save()

        lock.is_unlocked = True
        lock.save()

        return Response({
            "success": True,
            "coins_balance": profile.coins_balance,
            "lock_id": lock.id
        })


class CellListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CellSerializer

    def get_queryset(self):
        profile, _ = PlayerProfile.objects.get_or_create(user=self.request.user)
        return Cell.objects.filter(profile=profile)
