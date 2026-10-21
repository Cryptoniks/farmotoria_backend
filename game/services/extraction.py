"""
Добыча ресурсов.

Раньше ресурсы собирал фоновый APScheduler, запущенный в каждом процессе
сервера (на Render — в каждом воркере gunicorn), из-за чего ресурсы
начислялись несколько раз, а на бесплатном тарифе, когда сервис засыпает,
не начислялись вовсе.

Теперь начисление «ленивое»: при любом обращении игрока (статус добычи,
инвентарь, рынок, рецепты) считаем, сколько полных циклов прошло с момента
next_harvest_at, и начисляем их разом. Фоновый процесс не нужен.
"""
from django.db import transaction
from django.utils import timezone

from game.models import (
    SKILL_EXTRACTION,
    BuildingType,
    ExtractionProcess,
    ExtractionResource,
    PlayerProfile,
)

from . import GameError
from .field import get_placement
from .inventory import add_item
from .skills import add_skill_exp, skill_level, work_duration


def accrue(profile: PlayerProfile) -> list[dict]:
    """Начисляет все завершённые циклы добычи игрока. Возвращает список начислений."""
    now = timezone.now()
    collected = []
    with transaction.atomic():
        processes = list(
            ExtractionProcess.objects.select_for_update()
            .select_related("resource__output_item")
            .filter(profile=profile, status="running", next_harvest_at__lte=now)
        )
        if not processes:
            return collected

        user = profile.user
        level = skill_level(user, SKILL_EXTRACTION)
        total_cycles = 0
        for process in processes:
            resource = process.resource
            duration = work_duration(resource.duration_seconds, level)
            overdue = (now - process.next_harvest_at).total_seconds()
            cycles = 1 + int(overdue // duration)
            quantity = cycles * resource.output_quantity

            add_item(profile, resource.output_item, quantity)
            process.next_harvest_at += timezone.timedelta(seconds=cycles * duration)
            process.save(update_fields=["next_harvest_at"])

            total_cycles += cycles
            collected.append({
                "process_id": process.id,
                "item_id": resource.output_item_id,
                "item_name": resource.output_item.name,
                "quantity": quantity,
                "cycles": cycles,
            })

        profile.add_exp(total_cycles)
        add_skill_exp(user, SKILL_EXTRACTION, total_cycles)
    return collected


def start(profile: PlayerProfile, building_id: int) -> tuple[ExtractionProcess, int, int]:
    building = get_placement(profile, building_id)
    if building.building_type.building_type != BuildingType.TYPE_EXTRACTION:
        raise GameError("Здание не является зданием добычи")

    resource = ExtractionResource.objects.filter(building_type=building.building_type).first()
    if not resource:
        raise GameError("Ресурс для этого здания не настроен", status=404)

    if ExtractionProcess.objects.filter(building=building, status="running").exists():
        raise GameError("Добыча уже запущена")

    # Остановленные ранее процессы этого здания больше не нужны
    ExtractionProcess.objects.filter(building=building).exclude(status="running").delete()

    level = skill_level(profile.user, SKILL_EXTRACTION)
    duration = work_duration(resource.duration_seconds, level)
    process = ExtractionProcess.objects.create(
        profile=profile,
        building=building,
        resource=resource,
        next_harvest_at=timezone.now() + timezone.timedelta(seconds=duration),
        status="running",
    )
    return process, duration, level


def stop(profile: PlayerProfile, process_id: int) -> ExtractionProcess:
    accrue(profile)  # то, что уже добыто, не пропадает
    try:
        process = ExtractionProcess.objects.get(id=process_id, profile=profile, status="running")
    except ExtractionProcess.DoesNotExist:
        raise GameError("Процесс добычи не найден", status=404)
    process.status = "paused"
    process.save(update_fields=["status"])
    return process


def process_to_dict(p: ExtractionProcess, now) -> dict:
    return {
        "id": p.id,
        "building_id": p.building_id,
        "resource_name": p.resource.name,
        "output_item_id": p.resource.output_item_id,
        "output_item_name": p.resource.output_item.name,
        "output_quantity": p.resource.output_quantity,
        "next_harvest_at": p.next_harvest_at.isoformat() if p.next_harvest_at else None,
        "is_ready": bool(p.next_harvest_at and now >= p.next_harvest_at),
        "status": p.status,
    }
