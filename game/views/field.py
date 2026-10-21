"""Изометрическое поле: состояние, чанки, здания, грядки (/api/iso/*)."""
from django.db import transaction
from django.utils import timezone
from rest_framework.response import Response

from ..models import CHUNK_SIZE, MAX_FIELD_SIZE, START_UNLOCKED_SIZE, BuildingPlacement, BuildingType, FarmPlot
from ..services import GameError, field
from ..services.player import get_profile, lock_profile
from .base import GameAPIView, int_param


class IsoFieldStateView(GameAPIView):
    def get(self, request):
        profile = get_profile(request.user)
        placements = (
            BuildingPlacement.objects.filter(profile=profile)
            .select_related("building_type")
            .order_by("row", "col")
        )
        return Response({
            "coins_balance": profile.coins_balance,
            "field": {
                "chunk_size": CHUNK_SIZE,
                "start_unlocked_size": START_UNLOCKED_SIZE,
                "max_size": MAX_FIELD_SIZE,
                "next_chunk_cost": field.next_chunk_cost(profile),
            },
            "chunks": list(profile.field_chunks.values("chunk_row", "chunk_col", "price_paid")),
            "buildings": [field.building_to_dict(p) for p in placements],
            "available_buildings": list(BuildingType.objects.order_by("id").values(
                "id", "name", "slug", "building_type", "width", "height", "price"
            )),
        })


class IsoAvailableChunksView(GameAPIView):
    def get(self, request):
        profile = get_profile(request.user)
        cost = field.next_chunk_cost(profile)
        return Response({
            "available_chunks": [
                {"chunk_row": r, "chunk_col": c, "cost": cost} for r, c in field.available_chunks(profile)
            ],
            "next_chunk_cost": cost,
        })


class IsoExpandChunkView(GameAPIView):
    def post(self, request):
        cr = int_param(request.data, "chunk_row")
        cc = int_param(request.data, "chunk_col")
        with transaction.atomic():
            profile = lock_profile(request.user)
            paid = field.buy_chunk(profile, cr, cc)
        return Response({
            "success": True,
            "coins_balance": profile.coins_balance,
            "chunk": {"chunk_row": cr, "chunk_col": cc},
            "paid": paid,
            "next_cost": field.next_chunk_cost(profile),
        })


class IsoPlaceBuildingView(GameAPIView):
    def post(self, request):
        row = int_param(request.data, "row")
        col = int_param(request.data, "col")
        building_id = int_param(request.data, "building_id")
        with transaction.atomic():
            profile = lock_profile(request.user)
            placement = field.place_building(profile, building_id, row, col)
        return Response({
            "success": True,
            "coins_balance": profile.coins_balance,
            "building": field.building_to_dict(placement),
        })


class IsoRemoveBuildingView(GameAPIView):
    def post(self, request):
        placement_id = int_param(request.data, "placement_id")
        with transaction.atomic():
            profile = lock_profile(request.user)
            refund = field.remove_building(profile, placement_id)
        return Response({
            "success": True,
            "coins_balance": profile.coins_balance,
            "refunded": refund,
            "removed_id": placement_id,
        })


class IsoMoveBuildingView(GameAPIView):
    def post(self, request):
        placement_id = int_param(request.data, "placement_id")
        new_row = int_param(request.data, "row")
        new_col = int_param(request.data, "col")
        with transaction.atomic():
            profile = lock_profile(request.user)
            p, old_row, old_col = field.move_building(profile, placement_id, new_row, new_col)
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
                "width": p.width,
                "height": p.height,
            },
        })


class IsoMoveBuildingsBatchView(GameAPIView):
    """Пакетное перемещение. Каждое перемещение проверяется с учётом уже применённых."""

    def post(self, request):
        moves = request.data.get("moves") or []
        if not isinstance(moves, list):
            raise GameError("moves должен быть списком")

        results, errors = [], []
        with transaction.atomic():
            profile = lock_profile(request.user)
            owned = field.owned_chunks(profile)
            for move in moves:
                pid = move.get("placement_id") if isinstance(move, dict) else None
                try:
                    placement_id = int_param(move, "placement_id")
                    new_row = int_param(move, "row")
                    new_col = int_param(move, "col")
                    placements = list(BuildingPlacement.objects.filter(profile=profile).values_list(
                        "id", "row", "col", "width", "height"
                    ))
                    p, old_row, old_col = field.move_building(
                        profile, placement_id, new_row, new_col, owned=owned, placements=placements
                    )
                except (GameError, AttributeError) as e:
                    error = {"placement_id": pid, "error": getattr(e, "detail", "Некорректные данные")}
                    error.update(getattr(e, "extra", {}))
                    errors.append(error)
                    continue
                results.append({
                    "id": p.id, "old_row": old_row, "old_col": old_col,
                    "new_row": new_row, "new_col": new_col,
                })
        return Response({"success": not errors, "moved": results, "errors": errors})


class IsoPlantSeedView(GameAPIView):
    def post(self, request):
        building_id = int_param(request.data, "building_id")
        cell_row = int_param(request.data, "cell_row")
        cell_col = int_param(request.data, "cell_col")
        seed_id = int_param(request.data, "seed_id")
        with transaction.atomic():
            profile = lock_profile(request.user)
            plot = field.plant_seed(profile, request.user, building_id, cell_row, cell_col, seed_id)
        return Response({
            "success": True,
            "coins_balance": profile.coins_balance,
            "plot": {
                "id": plot.id,
                "building_id": building_id,
                "cell_row": cell_row,
                "cell_col": cell_col,
                "seed_id": seed_id,
                "seed_name": plot.seed.name,
                "planted_at": plot.planted_at.isoformat(),
                "ready_at": plot.ready_at.isoformat(),
                "status": plot.status,
            },
        })


class IsoHarvestView(GameAPIView):
    def post(self, request):
        plot_id = int_param(request.data, "plot_id")
        with transaction.atomic():
            profile = lock_profile(request.user)
            result = field.harvest(profile, request.user, plot_id)
        return Response({
            "success": True,
            "coins_balance": profile.coins_balance,
            "player_exp": profile.exp,
            "player_level": profile.level,
            "skill_level": result["skill_level"],
            "harvest": {
                "item_id": result["item"].id,
                "item_name": result["item"].name,
                "quantity": result["quantity"],
            },
        })


class IsoFieldPlotsView(GameAPIView):
    def get(self, request):
        profile = get_profile(request.user)
        field.refresh_plot_statuses(profile)
        plots = FarmPlot.objects.filter(
            profile=profile, status__in=field.ACTIVE_PLOT_STATUSES
        ).select_related("seed", "building__building_type")
        now = timezone.now()
        return Response({
            "plots": [{
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
                "is_ready": p.status == "ready" or bool(p.ready_at and now >= p.ready_at),
            } for p in plots],
        })
