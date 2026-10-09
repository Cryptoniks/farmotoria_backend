from django.db import transaction
from django.utils import timezone
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from ..models import (
    PlayerProfile, FieldChunk, BuildingPlacement,
    BuildingType, FarmPlot, ShopItem, Skill, UserSkill,
    ExtractionResource, ExtractionProcess, InventoryItem,
    Recipe, RecipeIngredient, RecipeProcess,
    CHUNK_SIZE, START_UNLOCKED_SIZE, MAX_FIELD_SIZE
)


def cell_to_chunk(row, col):
    return row // CHUNK_SIZE, col // CHUNK_SIZE


def is_chunk_in_bounds(cr, cc):
    max_chunk = MAX_FIELD_SIZE // CHUNK_SIZE
    return 0 <= cr < max_chunk and 0 <= cc < max_chunk


def is_chunk_adjacent_to_owned(profile, cr, cc):
    """Проверяет, есть ли у чанка соседний купленный чанк."""
    neighbors = [
        (cr - 1, cc),  # верхний
        (cr + 1, cc),  # нижний
        (cr, cc - 1),  # левый
        (cr, cc + 1),  # правний
    ]
    existing = set(
        FieldChunk.objects.filter(profile=profile).values_list("chunk_row", "chunk_col")
    )
    for nc, nr in neighbors:
        if (nc, nr) in existing:
            return True
    return False


def next_chunk_cost(profile):
    paid_count = FieldChunk.objects.filter(profile=profile, price_paid__gt=0).count()
    return 100 + paid_count * 100


def rects_overlap(a_row, a_col, a_w, a_h, b_row, b_col, b_w, b_h):
    return not (
        a_col + a_w <= b_col or
        b_col + b_w <= a_col or
        a_row + a_h <= b_row or
        b_row + b_h <= a_row
    )


class IsoFieldStateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile, _ = PlayerProfile.objects.get_or_create(user=request.user)

        chunks = list(FieldChunk.objects.filter(profile=profile).values(
            "chunk_row", "chunk_col", "price_paid"
        ))

        placements = (
            BuildingPlacement.objects
            .filter(profile=profile)
            .select_related("building_type")
            .order_by("row", "col")
        )

        buildings = [{
            "id": p.id,
            "building_id": p.building_type_id,
            "slug": p.building_type.slug,
            "building_type": p.building_type.building_type,
            "name": p.building_type.name,
            "row": p.row,
            "col": p.col,
            "w": p.width,
            "h": p.height,
            "price_paid": p.price_paid,
        } for p in placements]

        available_buildings = list(BuildingType.objects.values(
            "id", "name", "slug", "building_type", "width", "height", "price"
        ))

        return Response({
            "coins_balance": profile.coins_balance,
            "field": {
                "chunk_size": CHUNK_SIZE,
                "start_unlocked_size": START_UNLOCKED_SIZE,
                "max_size": MAX_FIELD_SIZE,
                "next_chunk_cost": next_chunk_cost(profile),
            },
            "chunks": chunks,
            "buildings": buildings,
            "available_buildings": available_buildings,
        })


class IsoExpandChunkView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        profile = PlayerProfile.objects.select_for_update().get(user=request.user)

        cr = int(request.data["chunk_row"])
        cc = int(request.data["chunk_col"])

        if not is_chunk_in_bounds(cr, cc):
            return Response({"detail": "Чанк вне допустимых границ"}, status=400)

        if FieldChunk.objects.filter(profile=profile, chunk_row=cr, chunk_col=cc).exists():
            return Response({"detail": "Чанк уже куплен"}, status=400)

        if not is_chunk_adjacent_to_owned(profile, cr, cc):
            return Response({"detail": "Можно покупать только рядом с уже купленными участками"}, status=400)

        cost = next_chunk_cost(profile)
        if profile.coins_balance < cost:
            return Response({"detail": "Недостаточно монет"}, status=400)

        profile.coins_balance -= cost
        profile.save()

        FieldChunk.objects.create(profile=profile, chunk_row=cr, chunk_col=cc, price_paid=cost)

        return Response({
            "success": True,
            "coins_balance": profile.coins_balance,
            "chunk": {"chunk_row": cr, "chunk_col": cc},
            "paid": cost,
            "next_cost": next_chunk_cost(profile),
        })


class IsoAvailableChunksView(APIView):
    """Возвращает список чанков, которые можно купить (рядом с купленными)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile, _ = PlayerProfile.objects.get_or_create(user=request.user)

        existing = set(
            FieldChunk.objects.filter(profile=profile).values_list("chunk_row", "chunk_col")
        )

        available_set = set()
        for cr, cc in existing:
            neighbors = [
                (cr - 1, cc),
                (cr + 1, cc),
                (cr, cc - 1),
                (cr, cc + 1),
            ]
            for nc, nr in neighbors:
                if is_chunk_in_bounds(nc, nr) and (nc, nr) not in existing:
                    available_set.add((nc, nr))

        available = [
            {"chunk_row": cr, "chunk_col": cc, "cost": next_chunk_cost(profile)}
            for cr, cc in sorted(available_set)
        ]

        return Response({
            "available_chunks": available,
            "next_chunk_cost": next_chunk_cost(profile),
        })


class IsoPlaceBuildingView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        profile = PlayerProfile.objects.select_for_update().get(user=request.user)

        row = int(request.data["row"])
        col = int(request.data["col"])
        building_id = int(request.data["building_id"])

        try:
            bt = BuildingType.objects.get(id=building_id)
        except BuildingType.DoesNotExist:
            return Response({"detail": "Тип здания не найден"}, status=404)

        w, h = bt.width, bt.height

        if row + h > MAX_FIELD_SIZE or col + w > MAX_FIELD_SIZE:
            return Response({"detail": "Здание выходит за пределы максимального поля"}, status=400)

        needed_chunks = set()
        for r in range(row, row + h):
            for c in range(col, col + w):
                cr, cc = cell_to_chunk(r, c)
                needed_chunks.add((cr, cc))

        existing = set(
            FieldChunk.objects.filter(profile=profile).values_list("chunk_row", "chunk_col")
        )
        for cr, cc in needed_chunks:
            if (cr, cc) not in existing:
                return Response({"detail": "Часть области не куплена (чанк заблокирован)"}, status=400)

        if profile.coins_balance < bt.price:
            return Response({"detail": "Недостаточно монет"}, status=400)

        placements = BuildingPlacement.objects.filter(profile=profile)
        for p in placements:
            if rects_overlap(row, col, w, h, p.row, p.col, p.width, p.height):
                return Response({"detail": "Место занято"}, status=400)

        profile.coins_balance -= bt.price
        profile.save()

        placement = BuildingPlacement.objects.create(
            profile=profile,
            building_type=bt,
            row=row,
            col=col,
            width=w,
            height=h,
            price_paid=bt.price,
        )

        return Response({
            "success": True,
            "coins_balance": profile.coins_balance,
            "building": {
                "id": placement.id,
                "building_id": bt.id,
                "slug": bt.slug,
                "name": bt.name,
                "building_type": bt.building_type,
                "row": row,
                "col": col,
                "w": w,
                "h": h,
                "price_paid": bt.price,
            }
        })


class IsoRemoveBuildingView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        profile = PlayerProfile.objects.select_for_update().get(user=request.user)
        placement_id = int(request.data["placement_id"])

        try:
            p = BuildingPlacement.objects.select_for_update().select_related("building_type").get(
                id=placement_id,
                profile=profile
            )
        except BuildingPlacement.DoesNotExist:
            return Response({"detail": "Здание не найдено"}, status=404)

        # Проверка на активные процессы
        building_type = p.building_type.building_type
        
        if building_type == BuildingType.TYPE_FIELD:
            # Для полей проверяем активные посадки
            active_plots = FarmPlot.objects.filter(
                building=p,
                status__in=["growing", "ready"]
            ).count()
            if active_plots > 0:
                return Response({
                    "detail": f"Нельзя продать: в здании {active_plots} активных посадок",
                    "active_plots": active_plots
                }, status=400)
        
        # TODO: Для других типов зданий добавить проверки при реализации логики

        refund = p.price_paid or p.building_type.price

        p.delete()

        profile.coins_balance += refund
        profile.save()

        return Response({
            "success": True,
            "coins_balance": profile.coins_balance,
            "refunded": refund,
            "removed_id": placement_id
        })


class IsoMoveBuildingView(APIView):
    """Перемещение здания на новые координаты (без проверки активных процессов)"""
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        try:
            placement_id = int(request.data.get("placement_id"))
            new_row = int(request.data.get("row"))
            new_col = int(request.data.get("col"))
        except (TypeError, ValueError) as e:
            return Response({"detail": f"Некорректные параметры: {e}"}, status=400)

        profile = PlayerProfile.objects.select_for_update().get(user=request.user)

        try:
            p = BuildingPlacement.objects.select_for_update().select_related("building_type").get(
                id=placement_id,
                profile=profile
            )
        except BuildingPlacement.DoesNotExist:
            return Response({"detail": "Здание не найдено"}, status=404)

        w, h = p.width, p.height
        grid_size = MAX_FIELD_SIZE

        # Проверка границ
        if new_row < 0 or new_col < 0 or new_row + h > grid_size or new_col + w > grid_size:
            return Response({"detail": "Здание выходит за границы поля"}, status=400)

        # Проверка доступности чанков для новой позиции
        needed_chunks = set()
        for r in range(new_row, new_row + h):
            for c in range(new_col, new_col + w):
                cr, cc = cell_to_chunk(r, c)
                needed_chunks.add((cr, cc))

        existing_chunks = set(
            FieldChunk.objects.filter(profile=profile).values_list("chunk_row", "chunk_col")
        )

        missing_chunks = []
        for cr, cc in needed_chunks:
            if (cr, cc) not in existing_chunks:
                missing_chunks.append((cr, cc))

        if missing_chunks:
            return Response({
                "detail": "Часть области не куплена (чанки заблокированы)",
                "missing_chunks": [{"chunk_row": cr, "chunk_col": cc} for cr, cc in missing_chunks]
            }, status=400)

        # Проверка занятости новых клеток
        overlapping = BuildingPlacement.objects.filter(
            profile=profile,
            row__lt=new_row + h,
            row__gte=new_row,
            col__lt=new_col + w,
            col__gte=new_col,
        ).exclude(id=placement_id)

        if overlapping.exists():
            return Response({"detail": "Место занято другим зданием"}, status=400)

        # Перемещаем
        old_row, old_col = p.row, p.col
        p.row = new_row
        p.col = new_col
        p.save()

        return Response({
            "success": True,
            "building": {
                "id": p.id,
                "building_id": p.building_type_id,
                "slug": p.building_type.slug,
                "building_type": p.building_type.building_type,
                "name": p.building_type.name,
                "old_row": old_row,
                "old_col": old_col,
                "new_row": new_row,
                "new_col": new_col,
                "width": w,
                "height": h,
            }
        })


class IsoMoveBuildingsBatchView(APIView):
    """Массовое перемещение зданий (пакетное сохранение)"""
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        try:
            moves = request.data.get("moves", [])
        except Exception:
            return Response({"detail": "Некорректные данные"}, status=400)

        profile = PlayerProfile.objects.select_for_update().get(user=request.user)

        results = []
        errors = []

        for move in moves:
            try:
                placement_id = int(move.get("placement_id"))
                new_row = int(move.get("row"))
                new_col = int(move.get("col"))
            except (TypeError, ValueError) as e:
                errors.append({"placement_id": move.get("placement_id"), "error": str(e)})
                continue

            try:
                p = BuildingPlacement.objects.select_for_update().select_related("building_type").get(
                    id=placement_id,
                    profile=profile
                )
            except BuildingPlacement.DoesNotExist:
                errors.append({"placement_id": placement_id, "error": "Здание не найдено"})
                continue

            w, h = p.width, p.height
            grid_size = MAX_FIELD_SIZE

            # Проверка границ
            if new_row < 0 or new_col < 0 or new_row + h > grid_size or new_col + w > grid_size:
                errors.append({"placement_id": placement_id, "error": "Здание выходит за границы поля"})
                continue

            # Проверка доступности чанков
            needed_chunks = set()
            for r in range(new_row, new_row + h):
                for c in range(new_col, new_col + w):
                    cr, cc = cell_to_chunk(r, c)
                    needed_chunks.add((cr, cc))

            existing_chunks = set(
                FieldChunk.objects.filter(profile=profile).values_list("chunk_row", "chunk_col")
            )

            missing_chunks = []
            for cr, cc in needed_chunks:
                if (cr, cc) not in existing_chunks:
                    missing_chunks.append((cr, cc))

            if missing_chunks:
                errors.append({"placement_id": placement_id, "error": "Чанки заблокированы", "missing_chunks": missing_chunks})
                continue

            # Проверка занятости (исключаем текущее здание)
            overlapping = BuildingPlacement.objects.filter(
                profile=profile,
                row__lt=new_row + h,
                row__gte=new_row,
                col__lt=new_col + w,
                col__gte=new_col,
            ).exclude(id=placement_id)

            if overlapping.exists():
                errors.append({"placement_id": placement_id, "error": "Место занято другим зданием"})
                continue

            # Перемещаем
            old_row, old_col = p.row, p.col
            p.row = new_row
            p.col = new_col
            p.save()

            results.append({
                "id": p.id,
                "old_row": old_row,
                "old_col": old_col,
                "new_row": new_row,
                "new_col": new_col,
            })

        return Response({
            "success": len(errors) == 0,
            "moved": results,
            "errors": errors,
        })


class IsoPlantSeedView(APIView):
    """Посадка семени на фермерское поле"""
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        # Parse input data first
        try:
            building_id = int(request.data.get("building_id"))
            cell_row = int(request.data.get("cell_row"))
            cell_col = int(request.data.get("cell_col"))
            seed_id = int(request.data.get("seed_id"))
        except (TypeError, ValueError) as e:
            return Response({"detail": f"Ошибка данных: {str(e)}"}, status=400)
        
        try:
            profile, _ = PlayerProfile.objects.get_or_create(user=request.user)
            profile = PlayerProfile.objects.select_for_update().get(pk=profile.pk)
            print(f"DEBUG plant: building_id={building_id}, cell=({cell_row},{cell_col}), seed_id={seed_id}")
        except Exception as e:
            print(f"DEBUG profile error: {e}")
            return Response({"detail": f"Ошибка профиля: {str(e)}"}, status=500)

        # Получаем здание (должно быть фермерским полем)
        try:
            building = BuildingPlacement.objects.select_related("building_type").get(
                id=building_id,
                profile=profile
            )
        except BuildingPlacement.DoesNotExist:
            return Response({"detail": "Здание не найдено"}, status=404)

        # Проверяем, что это фермерское поле
        if building.building_type.slug != "farming-field":
            return Response({"detail": "Здание не является фермерским полем"}, status=400)

        # Проверяем границы клетки внутри здания
        if cell_row < 0 or cell_row >= building.height or cell_col < 0 or cell_col >= building.width:
            return Response({"detail": "Клетка вне зоны поля"}, status=400)

        # Проверяем семя
        try:
            seed = ShopItem.objects.get(id=seed_id, is_seed=True)
        except ShopItem.DoesNotExist:
            return Response({"detail": "Семя не найдено"}, status=404)

        # Проверяем, что место свободно (только для active статусов)
        existing_plots = FarmPlot.objects.filter(
            building=building, 
            cell_row=cell_row, 
            cell_col=cell_col,
            status__in=["growing", "ready"]
        )
        if existing_plots.exists():
            # Debug info
            for p in existing_plots:
                print(f"DEBUG: Existing plot at ({cell_row},{cell_col}): status={p.status}, seed={p.seed.name}")
            return Response({"detail": "На этой клетке уже что-то растёт"}, status=400)

        # Проверяем баланс
        if profile.coins_balance < seed.price_coins:
            return Response({"detail": "Недостаточно монет"}, status=400)

        # Списываем монеты
        profile.coins_balance -= seed.price_coins
        profile.save()

        # === Учёт бонуса навыка Земледелие ===
        base_grow_seconds = (seed.grow_time_minutes or 3) * 60  # базовое время в секундах
        
        # Получаем уровень навыка
        try:
            farming_skill = Skill.objects.get(code='farming')
            user_skill = UserSkill.objects.get(user=request.user, skill=farming_skill)
            skill_level = user_skill.level
        except (Skill.DoesNotExist, UserSkill.DoesNotExist):
            skill_level = 0
        
        # Бонус: -1% времени за каждый уровень (min 10% бонус)
        reduction_factor = 1.0 - (skill_level * 0.01)
        if reduction_factor < 0.1:
            reduction_factor = 0.1  # максимум 90% уменьшение = 10% от времени
        
        reduced_seconds = int(base_grow_seconds * reduction_factor)
        
        # Вычисляем время готовности
        grow_duration = timezone.timedelta(seconds=reduced_seconds)
        ready_at = timezone.now() + grow_duration

        # Создаём посадку
        plot = FarmPlot.objects.create(
            profile=profile,
            building=building,
            cell_row=cell_row,
            cell_col=cell_col,
            seed=seed,
            planted_at=timezone.now(),
            ready_at=ready_at,
            status="growing",
        )

        return Response({
            "success": True,
            "coins_balance": profile.coins_balance,
            "plot": {
                "id": plot.id,
                "building_id": building_id,
                "cell_row": cell_row,
                "cell_col": cell_col,
                "seed_id": seed_id,
                "seed_name": seed.name,
                "planted_at": plot.planted_at.isoformat(),
                "ready_at": plot.ready_at.isoformat(),
                "status": plot.status,
            }
        })


class IsoHarvestView(APIView):
    """Сбор урожая с фермерского поля"""
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        profile, _ = PlayerProfile.objects.get_or_create(user=request.user)
        profile = PlayerProfile.objects.select_for_update().get(pk=profile.pk)
        
        plot_id = int(request.data["plot_id"])

        try:
            plot = FarmPlot.objects.select_related("seed", "building__building_type").get(
                id=plot_id,
                profile=profile
            )
        except FarmPlot.DoesNotExist:
            return Response({"detail": "Посадка не найдена"}, status=404)

        if plot.status != "ready":
            return Response({"detail": "Урожай ещё не готов"}, status=400)

        # Вычисляем награду (урожай * количество)
        harvest_item = plot.seed.harvest_item
        if not harvest_item:
            return Response({"detail": "У данного семени нет связанного урожая"}, status=400)

        # Получаем количество урожая (по умолчанию 2)
        harvest_yield = plot.seed.harvest_yield or 2

        # Добавляем урожай в инвентарь
        from ..models import InventoryItem
        inv_item, _ = InventoryItem.objects.get_or_create(
            player=profile,
            item=harvest_item,
            defaults={"quantity": 0}
        )
        inv_item.quantity += harvest_yield
        inv_item.save()

        # Удаляем посадку полностью после сбора
        plot.delete()

        # === Начисление опыта ===
        from ..models import PLAYER_EXP_PER_HARVEST, SKILL_EXP_PER_HARVEST, UserSkill, Skill
        
        profile.add_exp(PLAYER_EXP_PER_HARVEST)

        # Опыт на навык "farming"
        try:
            farming_skill = Skill.objects.get(code='farming')
            user_skill, _ = UserSkill.objects.get_or_create(
                user=request.user,
                skill=farming_skill,
                defaults={'level': 0, 'exp': 0}
            )
            user_skill.add_exp(SKILL_EXP_PER_HARVEST)
            
            skill_level = user_skill.level
        except Skill.DoesNotExist:
            skill_level = 0

        return Response({
            "success": True,
            "coins_balance": profile.coins_balance,
            "player_exp": profile.exp,
            "player_level": profile.level,
            "skill_level": skill_level,
            "harvest": {
                "item_id": harvest_item.id,
                "item_name": harvest_item.name,
                "quantity": harvest_yield,
            }
        })


class IsoFieldPlotsView(APIView):
    """Получить все посадки на поле игрока"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile, _ = PlayerProfile.objects.get_or_create(user=request.user)

        plots = FarmPlot.objects.filter(
            profile=profile,
            status__in=["growing", "ready"]
        ).select_related("seed", "building__building_type")

        now = timezone.now()

        # Обновляем статус готовых посадок
        for plot in plots:
            if plot.status == "growing" and plot.ready_at and now >= plot.ready_at:
                plot.status = "ready"
                plot.save(update_fields=["status"])

        plots_data = [{
            "id": p.id,
            "building_id": p.building_id,
            "building_slug": p.building.building_type.slug,
            "cell_row": p.cell_row,
            "cell_col": p.cell_col,
            "seed_id": p.seed_id,
            "seed_name": p.seed.name,
            "planted_at": p.planted_at.isoformat() if p.planted_at else None,
            "ready_at": p.ready_at.isoformat() if p.ready_at else None,
            "status": p.status,
            "is_ready": p.status == "ready" or (p.ready_at and now >= p.ready_at),
        } for p in plots]

        return Response({
            "plots": plots_data,
        })


class ExtractionStartView(APIView):
    """Запуск добычи в здании"""
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        profile = PlayerProfile.objects.select_for_update().get(user=request.user)
        building_id = int(request.data.get("building_id"))
        
        try:
            building = BuildingPlacement.objects.select_related("building_type").get(
                id=building_id,
                profile=profile
            )
        except BuildingPlacement.DoesNotExist:
            return Response({"detail": "Здание не найдено"}, status=404)
        
        # Проверяем что здание типа extraction
        if building.building_type.building_type != "extraction":
            return Response({"detail": "Здание не является зданием добычи"}, status=400)
        
        # Проверяем есть ли ресурс для этого здания
        try:
            resource = ExtractionResource.objects.get(building_type=building.building_type)
        except ExtractionResource.DoesNotExist:
            return Response({"detail": "Ресурс для этого здания не настроен"}, status=404)
        
        # Проверяем нет ли уже активного процесса добычи
        if ExtractionProcess.objects.filter(building=building, status="running").exists():
            return Response({"detail": "Добыча уже запущена"}, status=400)
        
        # Учёт бонуса навыка Добытчик
        try:
            extraction_skill = Skill.objects.get(code='extraction')
            user_skill = UserSkill.objects.get(user=request.user, skill=extraction_skill)
            skill_level = user_skill.level
        except (Skill.DoesNotExist, UserSkill.DoesNotExist):
            skill_level = 0
        
        # Бонус: -2% времени за каждый уровень (max 20% при lvl 10)
        reduction_factor = 1.0 - (skill_level * 0.02)
        if reduction_factor < 0.8:
            reduction_factor = 0.8
        
        duration = int(resource.duration_seconds * reduction_factor)
        next_harvest = timezone.now() + timezone.timedelta(seconds=duration)
        
        # Создаём процесс добычи
        process = ExtractionProcess.objects.create(
            profile=profile,
            building=building,
            resource=resource,
            next_harvest_at=next_harvest,
            status="running",
        )
        
        return Response({
            "success": True,
            "process_id": process.id,
            "resource_name": resource.name,
            "duration_seconds": duration,
            "output_quantity": resource.output_quantity,
            "next_harvest_at": next_harvest.isoformat(),
            "skill_level": skill_level,
        })


class ExtractionStatusView(APIView):
    """Проверка и сбор ресурсов добычи"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile, _ = PlayerProfile.objects.get_or_create(user=request.user)
        
        processes = ExtractionProcess.objects.filter(
            profile=profile,
            status="running"
        ).select_related("building__building_type", "resource__output_item")
        
        now = timezone.now()
        ready_processes = []
        
        for process in processes:
            if process.next_harvest_at and now >= process.next_harvest_at:
                ready_processes.append(process)
        
        return Response({
            "ready_count": len(ready_processes),
            "processes": [{
                "id": p.id,
                "building_id": p.building_id,
                "resource_name": p.resource.name,
                "output_item_id": p.resource.output_item_id,
                "output_item_name": p.resource.output_item.name,
                "output_quantity": p.resource.output_quantity,
                "next_harvest_at": p.next_harvest_at.isoformat() if p.next_harvest_at else None,
                "is_ready": p.next_harvest_at and now >= p.next_harvest_at,
                "status": p.status,  # Добавляем status
            } for p in processes]
        })


class ExtractionCollectView(APIView):
    """Сбор ресурсов добычи"""
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        profile = PlayerProfile.objects.select_for_update().get(user=request.user)
        process_id = int(request.data.get("process_id"))
        
        try:
            process = ExtractionProcess.objects.select_related(
                "building__building_type", "resource__output_item"
            ).get(id=process_id, profile=profile, status="running")
        except ExtractionProcess.DoesNotExist:
            return Response({"detail": "Процесс добычи не найден"}, status=404)
        
        now = timezone.now()
        
        # Проверяем готов ли сбор
        if not process.next_harvest_at or now < process.next_harvest_at:
            remaining = (process.next_harvest_at - now).total_seconds()
            return Response({
                "detail": "Ресурс ещё не готов",
                "remaining_seconds": int(remaining),
            }, status=400)
        
        # Добавляем ресурс в инвентарь
        output_item = process.resource.output_item
        inv_item, _ = InventoryItem.objects.get_or_create(
            player=profile,
            item=output_item,
            defaults={"quantity": 0}
        )
        inv_item.quantity += process.resource.output_quantity
        inv_item.save()
        
        # Начисляем опыт профилю
        profile.add_exp(1)
        
        # Начисляем опыт навыку
        try:
            extraction_skill = Skill.objects.get(code='extraction')
            user_skill = UserSkill.objects.get(user=request.user, skill=extraction_skill)
            user_skill.add_exp(1)
            skill_level = user_skill.level
        except (Skill.DoesNotExist, UserSkill.DoesNotExist):
            skill_level = 0
        
        # Перезапускаем цикл
        duration = process.resource.duration_seconds
        
        # Учёт бонуса навыка
        reduction_factor = 1.0 - (skill_level * 0.02)
        if reduction_factor < 0.8:
            reduction_factor = 0.8
        duration = int(duration * reduction_factor)
        
        process.next_harvest_at = now + timezone.timedelta(seconds=duration)
        process.save()
        
        return Response({
            "success": True,
            "collected": {
                "item_id": output_item.id,
                "item_name": output_item.name,
                "quantity": process.resource.output_quantity,
            },
            "coins_balance": profile.coins_balance,
            "next_harvest_at": process.next_harvest_at.isoformat(),
            "skill_level": skill_level,
            "profile_level": profile.level,
            "profile_exp": profile.exp,
            "exp_to_next": profile.exp_to_next,
        })


class ExtractionStopView(APIView):
    """Остановка добычи"""
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        profile = PlayerProfile.objects.select_for_update().get(user=request.user)
        process_id = int(request.data.get("process_id"))
        
        try:
            process = ExtractionProcess.objects.get(
                id=process_id,
                profile=profile,
                status="running"
            )
        except ExtractionProcess.DoesNotExist:
            return Response({"detail": "Процесс добычи не найден"}, status=404)
        
        process.status = "paused"
        process.save()
        
        return Response({
            "success": True,
            "process_id": process.id,
            "status": "paused",
        })


class ProcessingRecipesView(APIView):
    """Получить рецепты для здания переработки или производства"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        building_type_slug = request.query_params.get("building_type")
        
        if not building_type_slug:
            return Response({"detail": "building_type required"}, status=400)
        
        profile = PlayerProfile.objects.get(user=request.user)
        
        # Получаем инвентарь игрока
        inventory = InventoryItem.objects.filter(player=profile)
        inventory_map = {inv.item_id: inv.quantity for inv in inventory}
        
        # Получаем тип здания и определяем recipe_group
        try:
            bt = BuildingType.objects.get(slug=building_type_slug)
            # Маппинг типа здания на группу рецептов
            recipe_group_map = {
                "processing": "processing",
                "production": "production",
                "agroproduction": "agroproduction",
            }
            recipe_group = recipe_group_map.get(bt.building_type)
        except BuildingType.DoesNotExist:
            recipe_group = None
        
        if not recipe_group:
            return Response([])
        
        # Сначала ищем рецепты по building_type (конкретное здание)
        recipes = Recipe.objects.filter(
            building_type__slug=building_type_slug
        ).select_related("output_item", "building_type").prefetch_related("ingredients")
        
        # Если нет рецептов для конкретного здания, ищем по recipe_group (общие для типа)
        if not recipes.exists():
            recipes = Recipe.objects.filter(
                recipe_group=recipe_group
            ).select_related("output_item", "building_type").prefetch_related("ingredients")
        
        result = []
        for r in recipes:
            # Вычисляем максимальное количество для этого рецепта
            max_possible = float('inf')
            for ing in r.ingredients.all():
                available = inventory_map.get(ing.item.id, 0)
                possible = available // ing.quantity if ing.quantity > 0 else 0
                max_possible = min(max_possible, possible)
            
            result.append({
                "id": r.id,
                "name": r.name,
                "slug": r.slug,
                "duration_seconds": r.duration_seconds,
                "output_item_id": r.output_item.id,
                "output_item_name": r.output_item.name,
                "output_item_slug": r.output_item.slug,
                "output_quantity": r.output_quantity,
                "max_possible": max_possible,
                "ingredients": [
                    {
                        "item_id": ing.item.id,
                        "item_name": ing.item.name,
                        "item_slug": ing.item.slug,
                        "quantity": ing.quantity,
                        "available": inventory_map.get(ing.item.id, 0),
                    }
                    for ing in r.ingredients.all()
                ],
            })
        
        return Response(result)


class ProcessingStartView(APIView):
    """Запуск переработки с указанием количества"""
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        profile = PlayerProfile.objects.select_for_update().get(user=request.user)
        building_id = int(request.data.get("building_id"))
        recipe_id = int(request.data.get("recipe_id"))
        quantity = int(request.data.get("quantity", 1))
        
        if quantity <= 0:
            return Response({"detail": "Количество должно быть больше 0"}, status=400)
        
        # Проверяем здание
        try:
            building = BuildingPlacement.objects.select_related("building_type").get(
                id=building_id, profile=profile
            )
        except BuildingPlacement.DoesNotExist:
            return Response({"detail": "Здание не найдено"}, status=404)
        
        # Определяем recipe_group по типу здания
        recipe_group_map = {
            "processing": "processing",
            "production": "production",
            "agroproduction": "agroproduction",
        }
        recipe_group = recipe_group_map.get(building.building_type.building_type)
        
        if not recipe_group:
            return Response({"detail": "Здание не поддерживает рецепты"}, status=400)
        
        # Проверяем рецепт: сначала по building_type, потом по recipe_group
        try:
            recipe = Recipe.objects.select_related("output_item").prefetch_related("ingredients").get(
                id=recipe_id, building_type=building.building_type
            )
        except Recipe.DoesNotExist:
            try:
                recipe = Recipe.objects.select_related("output_item").prefetch_related("ingredients").get(
                    id=recipe_id, recipe_group=recipe_group
                )
            except Recipe.DoesNotExist:
                return Response({"detail": "Рецепт не найден"}, status=404)
        
        # Вычисляем сколько можем запустить
        max_possible = float('inf')
        for ing in recipe.ingredients.all():
            inv_item = InventoryItem.objects.filter(player=profile, item=ing.item).first()
            available = inv_item.quantity if inv_item else 0
            possible = available // ing.quantity
            max_possible = min(max_possible, possible)
        
        if quantity > max_possible:
            return Response({
                "detail": f"Недостаточно ресурсов. Максимально можно запустить: {max_possible}",
                "max_possible": max_possible
            }, status=400)
        
        # Вычисляем время с учётом навыка (используем recipe_group как код навыка)
        duration_per_one = recipe.duration_seconds
        try:
            skill = Skill.objects.get(code=recipe_group)
            user_skill = UserSkill.objects.get(user=profile.user, skill=skill)
            reduction = 1.0 - (user_skill.level * 0.02)
            if reduction < 0.8:
                reduction = 0.8
            duration_per_one = int(duration_per_one * reduction)
        except (Skill.DoesNotExist, UserSkill.DoesNotExist):
            pass
        
        # Время только для ПЕРВОГО цикла (остальные будут выполняться по очереди)
        first_cycle_duration = duration_per_one
        
        # Списываем ингредиенты
        for ing in recipe.ingredients.all():
            total_needed = ing.quantity * quantity
            inv_item = InventoryItem.objects.get(player=profile, item=ing.item)
            inv_item.quantity -= total_needed
            if inv_item.quantity <= 0:
                inv_item.delete()
            else:
                inv_item.save()
        
        # Создаём процесс - ready_at только для первого цикла!
        from django.utils import timezone
        process = RecipeProcess.objects.create(
            profile=profile,
            building=building,
            recipe=recipe,
            quantity=quantity,
            quantity_done=0,
            ready_at=timezone.now() + timezone.timedelta(seconds=first_cycle_duration),
        )
        
        return Response({
            "id": process.id,
            "recipe_name": recipe.name,
            "quantity": quantity,
            "duration_seconds": first_cycle_duration,
            "total_duration": first_cycle_duration * quantity,  # Общее время для всех циклов
            "duration_per_one": duration_per_one,
            "ready_at": process.ready_at.isoformat(),
            "status": "running",
        })


class ProcessingStatusView(APIView):
    """Получить статус процессов переработки и производства"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = PlayerProfile.objects.get(user=request.user)
        
        # Получаем все активные процессы переработки и производства
        processes = RecipeProcess.objects.filter(
            profile=profile,
            status="running"
        ).select_related("building", "building__building_type", "recipe", "recipe__output_item")
        
        now = timezone.now()
        result = []
        for p in processes:
            is_ready = p.ready_at and p.ready_at <= now
            
            # Если цикл завершён (is_ready), но quantity_done ещё не обновлён - обновляем
            if is_ready and p.quantity_done < p.quantity:
                p.quantity_done = p.quantity  # Все оставшиеся циклы помечаем как завершённые
                p.save()
            
            all_complete = p.quantity_done >= p.quantity
            
            # Вычисляем сколько ещё осталось
            remaining = p.quantity - p.quantity_done
            
            result.append({
                "id": p.id,
                "building_id": p.building_id,
                "recipe_id": p.recipe_id,
                "recipe_name": p.recipe.name,
                "output_item_name": p.recipe.output_item.name,
                "output_item_id": p.recipe.output_item.id,
                "output_quantity": p.recipe.output_quantity * p.quantity,  # Общее количество
                "output_quantity_per_one": p.recipe.output_quantity,
                "quantity": p.quantity,
                "quantity_done": p.quantity_done,
                "remaining": remaining,
                "duration_per_one": p.recipe.duration_seconds,
                "ready_at": p.ready_at.isoformat() if p.ready_at else None,
                "is_ready": is_ready,
                "all_complete": all_complete,  # Все циклы завершены, можно собирать
                "status": "ready" if all_complete else p.status,
            })
        
        return Response(result)


class ProcessingCollectView(APIView):
    """Сбор результатов переработки (все ресурсы выдаются после завершения всех циклов)"""
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        profile = PlayerProfile.objects.select_for_update().get(user=request.user)
        process_id = int(request.data.get("process_id"))
        
        try:
            process = RecipeProcess.objects.select_related("recipe", "recipe__output_item").get(
                id=process_id,
                profile=profile,
                status="running"
            )
        except RecipeProcess.DoesNotExist:
            return Response({"detail": "Процесс переработки не найден"}, status=404)
        
        now = timezone.now()
        
        # Проверяем, завершены ли ВСЕ циклы
        is_all_complete = process.ready_at and process.ready_at <= now and process.quantity_done >= process.quantity
        
        if not is_all_complete:
            return Response({
                "detail": "Переработка ещё не завершена",
                "completed": process.quantity_done,
                "total": process.quantity,
                "remaining": process.quantity - process.quantity_done,
                "ready_at": process.ready_at.isoformat() if process.ready_at else None,
            }, status=400)
        
        # Все циклы завершены - выдаём ВСЕ ресурсы сразу
        output_item = process.recipe.output_item
        output_qty_per_cycle = process.recipe.output_quantity
        total_output = output_qty_per_cycle * process.quantity
        
        # Добавляем все ресурсы в инвентарь
        inv_item, _ = InventoryItem.objects.get_or_create(
            player=profile,
            item=output_item,
            defaults={"quantity": 0}
        )
        inv_item.quantity += total_output
        inv_item.save()
        
        # Добавляем опыт профилю за все завершённые циклы
        profile.add_exp(process.quantity)
        
        # Добавляем опыт навыку за все завершённые циклы (используем skill из рецепта)
        recipe = process.recipe
        if recipe.skill and recipe.skill_exp > 0:
            try:
                user_skill, _ = UserSkill.objects.get_or_create(
                    user=profile.user, 
                    skill=recipe.skill
                )
                total_skill_exp = recipe.skill_exp * process.quantity
                user_skill.add_exp(total_skill_exp)
            except Exception as e:
                print(f"Error adding skill exp: {e}")
        
        # Удаляем процесс
        process.delete()
        
        return Response({
            "success": True,
            "item_name": output_item.name,
            "item_id": output_item.id,
            "quantity": total_output,
            "cycles_completed": process.quantity,
            "status": "completed",
            "message": f"Получено: {output_item.name} x{total_output}",
            "profile_level": profile.level,
            "profile_exp": profile.exp,
            "exp_to_next": profile.exp_to_next,
        })


class ProcessingStopView(APIView):
    """Остановка переработки с возвратом неиспользованных ресурсов"""
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        profile = PlayerProfile.objects.select_for_update().get(user=request.user)
        process_id = int(request.data.get("process_id"))
        
        try:
            process = RecipeProcess.objects.select_related("recipe").prefetch_related("recipe__ingredients").get(
                id=process_id,
                profile=profile,
                status="running"
            )
        except RecipeProcess.DoesNotExist:
            return Response({"detail": "Процесс переработки не найден"}, status=404)
        
        # Вычисляем сколько циклов ещё не выполнено
        remaining_cycles = process.quantity - process.quantity_done
        
        # Возвращаем неиспользованные ресурсы в инвентарь
        returned_items = []
        if remaining_cycles > 0:
            for ing in process.recipe.ingredients.all():
                returned_qty = ing.quantity * remaining_cycles
                inv_item, _ = InventoryItem.objects.get_or_create(
                    player=profile,
                    item=ing.item,
                    defaults={"quantity": 0}
                )
                inv_item.quantity += returned_qty
                inv_item.save()
                returned_items.append({
                    "item_name": ing.item.name,
                    "quantity": returned_qty
                })
        
        # Удаляем процесс
        process.delete()
        
        return Response({
            "success": True,
            "message": f"Переработка остановлена. Неиспользованные ресурсы возвращены в инвентарь.",
            "returned_items": returned_items,
            "stopped_cycles": remaining_cycles,
        })
