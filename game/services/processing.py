"""
Переработка, производство и животноводство (рецепты в зданиях).

Процесс на N циклов длится N × (время одного цикла). Время одного цикла
хранится неявно: (ready_at - started_at) / quantity, поэтому прогресс
(quantity_done) всегда можно посчитать без фоновых задач.
"""
from django.db import transaction
from django.utils import timezone

from game.models import (
    RECIPE_GROUP_AGROPRODUCTION,
    RECIPE_GROUP_PROCESSING,
    RECIPE_GROUP_PRODUCTION,
    BuildingType,
    InventoryItem,
    PlayerProfile,
    Recipe,
    RecipeProcess,
)

from . import GameError
from .field import get_placement
from .inventory import add_item, available_quantities, parse_quantity, remove_item
from .skills import add_skill_exp, skill_level, work_duration

RECIPE_GROUPS = {RECIPE_GROUP_PROCESSING, RECIPE_GROUP_PRODUCTION, RECIPE_GROUP_AGROPRODUCTION}


def recipe_group_for(building_type: BuildingType) -> str | None:
    group = building_type.building_type
    return group if group in RECIPE_GROUPS else None


def recipes_for(building_type: BuildingType):
    """Рецепты конкретного здания + общие рецепты его группы (без привязки к зданию)."""
    from django.db.models import Q

    qs = Recipe.objects.select_related("output_item").prefetch_related("ingredients__item")
    group = recipe_group_for(building_type)
    condition = Q(building_type=building_type)
    if group:
        condition |= Q(recipe_group=group, building_type__isnull=True)
    return qs.filter(condition).order_by("id")


def max_runs(recipe: Recipe, stock: dict[int, int]) -> int:
    ingredients = list(recipe.ingredients.all())
    if not ingredients:
        return 0
    return min(stock.get(ing.item_id, 0) // ing.quantity for ing in ingredients if ing.quantity > 0)


def recipes_payload(profile: PlayerProfile, building_type_slug: str) -> list[dict]:
    try:
        bt = BuildingType.objects.get(slug=building_type_slug)
    except BuildingType.DoesNotExist:
        return []
    if not recipe_group_for(bt):
        return []

    stock = dict(InventoryItem.objects.filter(player=profile).values_list("item_id", "quantity"))
    result = []
    for r in recipes_for(bt):
        ingredients = list(r.ingredients.all())
        result.append({
            "id": r.id,
            "name": r.name,
            "slug": r.slug,
            "duration_seconds": r.duration_seconds,
            "output_item_id": r.output_item_id,
            "output_item_name": r.output_item.name,
            "output_item_slug": r.output_item.slug,
            "output_quantity": r.output_quantity,
            "max_possible": max_runs(r, stock),
            "ingredients": [
                {
                    "item_id": ing.item_id,
                    "item_name": ing.item.name,
                    "item_slug": ing.item.slug,
                    "quantity": ing.quantity,
                    "available": stock.get(ing.item_id, 0),
                }
                for ing in ingredients
            ],
        })
    return result


def cycle_seconds(process: RecipeProcess) -> float:
    total = (process.ready_at - process.started_at).total_seconds()
    return max(total / max(process.quantity, 1), 1)


def cycles_done(process: RecipeProcess, now) -> int:
    if not process.ready_at:
        return 0
    if now >= process.ready_at:
        return process.quantity
    elapsed = (now - process.started_at).total_seconds()
    return min(process.quantity, max(0, int(elapsed // cycle_seconds(process))))


def start(profile: PlayerProfile, building_id, recipe_id, quantity) -> tuple[RecipeProcess, int]:
    quantity = parse_quantity(quantity)
    building = get_placement(profile, building_id)
    group = recipe_group_for(building.building_type)
    if not group:
        raise GameError("Здание не поддерживает рецепты")

    recipe = recipes_for(building.building_type).filter(id=recipe_id).first()
    if not recipe:
        raise GameError("Рецепт не найден", status=404)

    ingredients = list(recipe.ingredients.all())
    stock = available_quantities(profile, [i.item_id for i in ingredients])
    possible = max_runs(recipe, stock)
    if quantity > possible:
        raise GameError(
            f"Недостаточно ресурсов. Максимально можно запустить: {possible}", max_possible=possible
        )

    per_one = work_duration(recipe.duration_seconds, skill_level(profile.user, group))
    with transaction.atomic():
        for ing in ingredients:
            remove_item(profile, ing.item, ing.quantity * quantity)
        now = timezone.now()
        process = RecipeProcess.objects.create(
            profile=profile,
            building=building,
            recipe=recipe,
            quantity=quantity,
            quantity_done=0,
            started_at=now,
            ready_at=now + timezone.timedelta(seconds=per_one * quantity),
        )
    # auto_now_add перезаписывает started_at — выравниваем с ready_at
    RecipeProcess.objects.filter(pk=process.pk).update(started_at=now)
    process.started_at = now
    return process, per_one


def status_payload(profile: PlayerProfile) -> list[dict]:
    now = timezone.now()
    processes = RecipeProcess.objects.filter(profile=profile, status="running").select_related(
        "recipe__output_item"
    )
    result = []
    for p in processes:
        done = cycles_done(p, now)
        if done != p.quantity_done:
            p.quantity_done = done
            p.save(update_fields=["quantity_done"])
        all_complete = done >= p.quantity
        result.append({
            "id": p.id,
            "building_id": p.building_id,
            "recipe_id": p.recipe_id,
            "recipe_name": p.recipe.name,
            "output_item_name": p.recipe.output_item.name,
            "output_item_id": p.recipe.output_item_id,
            "output_quantity": p.recipe.output_quantity * p.quantity,
            "output_quantity_per_one": p.recipe.output_quantity,
            "quantity": p.quantity,
            "quantity_done": done,
            "remaining": p.quantity - done,
            "duration_per_one": int(cycle_seconds(p)),
            "ready_at": p.ready_at.isoformat() if p.ready_at else None,
            "is_ready": all_complete,
            "all_complete": all_complete,
            "status": "ready" if all_complete else p.status,
        })
    return result


def _get_running(profile, process_id) -> RecipeProcess:
    try:
        return (
            # of=("self",): recipe.skill nullable, PostgreSQL не блокирует строки LEFT JOIN
            RecipeProcess.objects.select_for_update(of=("self",))
            .select_related("recipe__output_item", "recipe__skill")
            .get(id=process_id, profile=profile, status="running")
        )
    except RecipeProcess.DoesNotExist:
        raise GameError("Процесс переработки не найден", status=404)


def _reward(profile: PlayerProfile, process: RecipeProcess, cycles: int) -> int:
    if cycles <= 0:
        return 0
    recipe = process.recipe
    total = recipe.output_quantity * cycles
    add_item(profile, recipe.output_item, total)
    profile.add_exp(cycles)
    if recipe.skill_id and recipe.skill_exp:
        add_skill_exp(profile.user, recipe.skill.code, recipe.skill_exp * cycles)
    return total


def collect(profile: PlayerProfile, process_id) -> tuple[RecipeProcess, int]:
    process = _get_running(profile, process_id)
    now = timezone.now()
    if cycles_done(process, now) < process.quantity:
        done = cycles_done(process, now)
        raise GameError(
            "Переработка ещё не завершена",
            completed=done,
            total=process.quantity,
            remaining=process.quantity - done,
            ready_at=process.ready_at.isoformat() if process.ready_at else None,
        )
    total = _reward(profile, process, process.quantity)
    process.delete()
    return process, total


def stop(profile: PlayerProfile, process_id) -> dict:
    """Останавливает процесс: готовые циклы выдаются, ингредиенты остальных возвращаются."""
    process = _get_running(profile, process_id)
    done = cycles_done(process, timezone.now())
    remaining = process.quantity - done

    produced = _reward(profile, process, done)
    returned = []
    for ing in process.recipe.ingredients.select_related("item"):
        qty = ing.quantity * remaining
        if qty:
            add_item(profile, ing.item, qty)
            returned.append({"item_name": ing.item.name, "quantity": qty})
    process.delete()
    return {"returned_items": returned, "stopped_cycles": remaining, "produced": produced}
