"""Добыча (/api/extraction/*) и переработка/производство (/api/processing/*)."""
from django.db import transaction
from django.utils import timezone
from rest_framework.response import Response

from ..models import ExtractionProcess
from ..services import GameError, extraction, processing
from ..services.player import get_profile, lock_profile
from .base import GameAPIView, int_param


# ----------------------------------------------------------------- добыча ----
class ExtractionStartView(GameAPIView):
    def post(self, request):
        building_id = int_param(request.data, "building_id")
        with transaction.atomic():
            profile = lock_profile(request.user)
            process, duration, level = extraction.start(profile, building_id)
        return Response({
            "success": True,
            "process_id": process.id,
            "resource_name": process.resource.name,
            "duration_seconds": duration,
            "output_quantity": process.resource.output_quantity,
            "next_harvest_at": process.next_harvest_at.isoformat(),
            "skill_level": level,
        })


class ExtractionStatusView(GameAPIView):
    """Статус добычи. Заодно начисляет всё, что добыто с прошлого обращения."""

    def get(self, request):
        profile = get_profile(request.user)
        collected = extraction.accrue(profile)
        processes = ExtractionProcess.objects.filter(profile=profile, status="running").select_related(
            "resource__output_item"
        )
        now = timezone.now()
        data = [extraction.process_to_dict(p, now) for p in processes]
        return Response({
            "ready_count": sum(1 for p in data if p["is_ready"]),
            "processes": data,
            "collected": collected,
        })


class ExtractionCollectView(GameAPIView):
    def post(self, request):
        process_id = int_param(request.data, "process_id")
        profile = get_profile(request.user)
        try:
            process = ExtractionProcess.objects.select_related("resource__output_item").get(
                id=process_id, profile=profile, status="running"
            )
        except ExtractionProcess.DoesNotExist:
            raise GameError("Процесс добычи не найден", status=404)

        collected = [c for c in extraction.accrue(profile) if c["process_id"] == process_id]
        process.refresh_from_db()
        if not collected:
            remaining = (process.next_harvest_at - timezone.now()).total_seconds()
            raise GameError("Ресурс ещё не готов", remaining_seconds=max(0, int(remaining)))

        profile.refresh_from_db()
        item = collected[0]
        return Response({
            "success": True,
            "collected": {
                "item_id": item["item_id"],
                "item_name": item["item_name"],
                "quantity": item["quantity"],
            },
            "coins_balance": profile.coins_balance,
            "next_harvest_at": process.next_harvest_at.isoformat(),
            "profile_level": profile.level,
            "profile_exp": profile.exp,
            "exp_to_next": profile.exp_to_next,
        })


class ExtractionStopView(GameAPIView):
    def post(self, request):
        process_id = int_param(request.data, "process_id")
        process = extraction.stop(get_profile(request.user), process_id)
        return Response({"success": True, "process_id": process.id, "status": process.status})


# ----------------------------------------------------- переработка/производство ----
class ProcessingRecipesView(GameAPIView):
    def get(self, request):
        slug = request.query_params.get("building_type")
        if not slug:
            raise GameError("building_type required")
        profile = get_profile(request.user)
        extraction.accrue(profile)
        return Response(processing.recipes_payload(profile, slug))


class ProcessingStartView(GameAPIView):
    def post(self, request):
        building_id = int_param(request.data, "building_id")
        recipe_id = int_param(request.data, "recipe_id")
        with transaction.atomic():
            profile = lock_profile(request.user)
            extraction.accrue(profile)
            process, per_one = processing.start(
                profile, building_id, recipe_id, request.data.get("quantity", 1)
            )
        return Response({
            "id": process.id,
            "recipe_name": process.recipe.name,
            "quantity": process.quantity,
            "duration_seconds": per_one,
            "total_duration": per_one * process.quantity,
            "duration_per_one": per_one,
            "ready_at": process.ready_at.isoformat(),
            "status": "running",
        })


class ProcessingStatusView(GameAPIView):
    def get(self, request):
        return Response(processing.status_payload(get_profile(request.user)))


class ProcessingCollectView(GameAPIView):
    def post(self, request):
        process_id = int_param(request.data, "process_id")
        with transaction.atomic():
            profile = lock_profile(request.user)
            process, total = processing.collect(profile, process_id)
        item = process.recipe.output_item
        return Response({
            "success": True,
            "item_name": item.name,
            "item_id": item.id,
            "quantity": total,
            "cycles_completed": process.quantity,
            "status": "completed",
            "message": f"Получено: {item.name} x{total}",
            "profile_level": profile.level,
            "profile_exp": profile.exp,
            "exp_to_next": profile.exp_to_next,
        })


class ProcessingStopView(GameAPIView):
    def post(self, request):
        process_id = int_param(request.data, "process_id")
        with transaction.atomic():
            profile = lock_profile(request.user)
            result = processing.stop(profile, process_id)
        return Response({
            "success": True,
            "message": "Переработка остановлена. Готовая продукция и неиспользованные ресурсы — в инвентаре.",
            **result,
        })
