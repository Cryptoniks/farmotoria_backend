"""Изометрическое поле: чанки, размещение/перемещение/продажа зданий, грядки."""
from django.utils import timezone

from game.models import (
    CHUNK_SIZE,
    MAX_FIELD_SIZE,
    PLAYER_EXP_PER_HARVEST,
    SKILL_EXP_PER_HARVEST,
    SKILL_FARMING,
    BuildingPlacement,
    BuildingType,
    ExtractionProcess,
    FarmPlot,
    FieldChunk,
    PlayerProfile,
    RecipeProcess,
    ShopItem,
)

from . import GameError
from .inventory import add_item
from .player import add_coins, spend_coins
from .skills import add_skill_exp, farming_duration, skill_level

FARMING_FIELD_SLUG = "farming-field"
CHUNK_BASE_COST = 100
CHUNK_COST_STEP = 100
DEFAULT_GROW_MINUTES = 3
ACTIVE_PLOT_STATUSES = ("growing", "ready")


# ---------------------------------------------------------------- чанки ----
def owned_chunks(profile: PlayerProfile) -> set[tuple[int, int]]:
    return set(FieldChunk.objects.filter(profile=profile).values_list("chunk_row", "chunk_col"))


def is_chunk_in_bounds(cr: int, cc: int) -> bool:
    max_chunk = MAX_FIELD_SIZE // CHUNK_SIZE
    return 0 <= cr < max_chunk and 0 <= cc < max_chunk


def neighbours(cr: int, cc: int):
    yield from ((cr - 1, cc), (cr + 1, cc), (cr, cc - 1), (cr, cc + 1))


def next_chunk_cost(profile: PlayerProfile) -> int:
    paid = FieldChunk.objects.filter(profile=profile, price_paid__gt=0).count()
    return CHUNK_BASE_COST + paid * CHUNK_COST_STEP


def available_chunks(profile: PlayerProfile) -> list[tuple[int, int]]:
    owned = owned_chunks(profile)
    result = {
        n for chunk in owned for n in neighbours(*chunk)
        if is_chunk_in_bounds(*n) and n not in owned
    }
    return sorted(result)


def buy_chunk(profile: PlayerProfile, cr: int, cc: int) -> int:
    """Профиль должен быть заблокирован. Возвращает заплаченную цену."""
    if not is_chunk_in_bounds(cr, cc):
        raise GameError("Чанк вне допустимых границ")
    owned = owned_chunks(profile)
    if (cr, cc) in owned:
        raise GameError("Чанк уже куплен")
    if not any(n in owned for n in neighbours(cr, cc)):
        raise GameError("Можно покупать только рядом с уже купленными участками")
    cost = next_chunk_cost(profile)
    spend_coins(profile, cost)
    FieldChunk.objects.create(profile=profile, chunk_row=cr, chunk_col=cc, price_paid=cost)
    return cost


# --------------------------------------------------------------- здания ----
def rects_overlap(a_row, a_col, a_w, a_h, b_row, b_col, b_w, b_h) -> bool:
    return not (
        a_col + a_w <= b_col or b_col + b_w <= a_col
        or a_row + a_h <= b_row or b_row + b_h <= a_row
    )


def missing_chunks_for_rect(profile, row, col, w, h, owned=None) -> list[tuple[int, int]]:
    owned = owned if owned is not None else owned_chunks(profile)
    needed = {
        (r // CHUNK_SIZE, c // CHUNK_SIZE)
        for r in range(row, row + h)
        for c in range(col, col + w)
    }
    return sorted(needed - owned)


def validate_area(profile, row, col, w, h, exclude_id=None, owned=None, placements=None) -> None:
    """Проверяет границы поля, купленные чанки и пересечения с другими зданиями."""
    if row < 0 or col < 0 or row + h > MAX_FIELD_SIZE or col + w > MAX_FIELD_SIZE:
        raise GameError("Здание выходит за границы поля")

    missing = missing_chunks_for_rect(profile, row, col, w, h, owned)
    if missing:
        raise GameError(
            "Часть области не куплена (чанки заблокированы)",
            missing_chunks=[{"chunk_row": r, "chunk_col": c} for r, c in missing],
        )

    if placements is None:
        placements = BuildingPlacement.objects.filter(profile=profile).values_list(
            "id", "row", "col", "width", "height"
        )
    for pid, p_row, p_col, p_w, p_h in placements:
        if pid != exclude_id and rects_overlap(row, col, w, h, p_row, p_col, p_w, p_h):
            raise GameError("Место занято другим зданием")


def place_building(profile: PlayerProfile, building_type_id: int, row: int, col: int) -> BuildingPlacement:
    try:
        bt = BuildingType.objects.get(id=building_type_id)
    except BuildingType.DoesNotExist:
        raise GameError("Тип здания не найден", status=404)

    validate_area(profile, row, col, bt.width, bt.height)
    spend_coins(profile, bt.price)
    return BuildingPlacement.objects.create(
        profile=profile, building_type=bt, row=row, col=col,
        width=bt.width, height=bt.height, price_paid=bt.price,
    )


def get_placement(profile, placement_id, lock=False) -> BuildingPlacement:
    qs = BuildingPlacement.objects.select_related("building_type")
    if lock:
        qs = qs.select_for_update()
    try:
        return qs.get(id=placement_id, profile=profile)
    except BuildingPlacement.DoesNotExist:
        raise GameError("Здание не найдено", status=404)


def remove_building(profile: PlayerProfile, placement_id: int) -> int:
    """Продаёт здание, возвращает потраченные монеты. Нельзя продать здание с активным процессом."""
    placement = get_placement(profile, placement_id, lock=True)

    active_plots = FarmPlot.objects.filter(building=placement, status__in=ACTIVE_PLOT_STATUSES).count()
    if active_plots:
        raise GameError(
            f"Нельзя продать: в здании {active_plots} активных посадок", active_plots=active_plots
        )
    if ExtractionProcess.objects.filter(building=placement, status="running").exists():
        raise GameError("Нельзя продать: в здании идёт добыча. Сначала остановите её")
    if RecipeProcess.objects.filter(building=placement, status="running").exists():
        raise GameError("Нельзя продать: в здании идёт производство. Сначала остановите или заберите его")

    refund = placement.price_paid or placement.building_type.price
    placement.delete()
    add_coins(profile, refund)
    return refund


def move_building(profile, placement_id, new_row, new_col, owned=None, placements=None) -> tuple[BuildingPlacement, int, int]:
    placement = get_placement(profile, placement_id, lock=True)
    validate_area(
        profile, new_row, new_col, placement.width, placement.height,
        exclude_id=placement.id, owned=owned, placements=placements,
    )
    old_row, old_col = placement.row, placement.col
    placement.row, placement.col = new_row, new_col
    placement.save(update_fields=["row", "col"])
    return placement, old_row, old_col


def building_to_dict(p: BuildingPlacement) -> dict:
    bt = p.building_type
    return {
        "id": p.id,
        "building_id": bt.id,
        "slug": bt.slug,
        "building_type": bt.building_type,
        "name": bt.name,
        "row": p.row,
        "col": p.col,
        "w": p.width,
        "h": p.height,
        "price_paid": p.price_paid,
    }


# --------------------------------------------------------------- грядки ----
def refresh_plot_statuses(profile: PlayerProfile) -> None:
    FarmPlot.objects.filter(
        profile=profile, status="growing", ready_at__lte=timezone.now()
    ).update(status="ready")


def plant_seed(profile: PlayerProfile, user, building_id: int, cell_row: int, cell_col: int, seed_id: int) -> FarmPlot:
    building = get_placement(profile, building_id)
    if building.building_type.slug != FARMING_FIELD_SLUG:
        raise GameError("Здание не является фермерским полем")
    if not (0 <= cell_row < building.height and 0 <= cell_col < building.width):
        raise GameError("Клетка вне зоны поля")

    try:
        seed = ShopItem.objects.get(id=seed_id, is_seed=True)
    except ShopItem.DoesNotExist:
        raise GameError("Семя не найдено", status=404)

    if FarmPlot.objects.filter(
        building=building, cell_row=cell_row, cell_col=cell_col, status__in=ACTIVE_PLOT_STATUSES
    ).exists():
        raise GameError("На этой клетке уже что-то растёт")

    spend_coins(profile, seed.price_coins)

    base_seconds = (seed.grow_time_minutes or DEFAULT_GROW_MINUTES) * 60
    seconds = farming_duration(base_seconds, skill_level(user, SKILL_FARMING))
    now = timezone.now()

    # Старая собранная запись на той же клетке мешает unique_together
    FarmPlot.objects.filter(
        profile=profile, building=building, cell_row=cell_row, cell_col=cell_col
    ).delete()
    return FarmPlot.objects.create(
        profile=profile, building=building, cell_row=cell_row, cell_col=cell_col,
        seed=seed, ready_at=now + timezone.timedelta(seconds=seconds), status="growing",
    )


def harvest(profile: PlayerProfile, user, plot_id: int) -> dict:
    try:
        plot = FarmPlot.objects.select_related("seed__harvest_item").select_for_update().get(
            id=plot_id, profile=profile
        )
    except FarmPlot.DoesNotExist:
        raise GameError("Посадка не найдена", status=404)

    if plot.status != "ready" and not (plot.ready_at and plot.ready_at <= timezone.now()):
        raise GameError("Урожай ещё не готов")

    harvest_item = plot.seed.harvest_item
    if not harvest_item:
        raise GameError("У данного семени нет связанного урожая")

    quantity = plot.seed.harvest_yield or 2
    add_item(profile, harvest_item, quantity)
    plot.delete()

    profile.add_exp(PLAYER_EXP_PER_HARVEST)
    level = add_skill_exp(user, SKILL_FARMING, SKILL_EXP_PER_HARVEST)
    return {"item": harvest_item, "quantity": quantity, "skill_level": level}
