"""Хранилища, уровни зданий, стартовые здания, Магазин и Рынок (docs/PLAN_buildings.md)."""
import pytest
from django.utils import timezone

from game.models import BuildingPlacement, BuildingType, ExtractionProcess, FarmPlot, InventoryItem, ShopItem
from game.services.player import STARTING_BUILDINGS
from game.services.skills import farming_duration, work_duration


def placement(user, slug):
    return BuildingPlacement.objects.get(profile=user.profile, building_type__slug=slug)


def build(client, slug, row, col):
    bt = BuildingType.objects.get(slug=slug)
    return client.post("/api/iso/place-building/", {"building_id": bt.id, "row": row, "col": col}, format="json")


def give(user, slug, quantity):
    InventoryItem.objects.update_or_create(
        player=user.profile, item=ShopItem.objects.get(slug=slug), defaults={"quantity": quantity}
    )


def rich(user):
    user.profile.coins_balance = 100_000
    user.profile.save()


@pytest.mark.django_db
class TestStartingBuildings:
    def test_new_player_gets_starting_buildings(self, new_player):
        player, _ = new_player
        placements = list(BuildingPlacement.objects.filter(profile=player.profile).select_related("building_type"))
        assert sorted(p.building_type.slug for p in placements) == sorted(s for s, _, _ in STARTING_BUILDINGS)
        for p in placements:
            assert p.price_paid == 0 and p.level == 1
            assert p.row + p.height <= 50 and p.col + p.width <= 50  # внутри бесплатной зоны
        for a in placements:
            for b in placements:
                if a.id < b.id:
                    assert (a.col + a.width <= b.col or b.col + b.width <= a.col
                            or a.row + a.height <= b.row or b.row + b.height <= a.row), (a, b)

    def test_service_buildings_not_buildable_or_sellable(self, new_player):
        player, client = new_player
        rich(player)
        assert all(b["building_type"] not in ("shop", "market")
                   for b in client.get("/api/iso/field/").data["available_buildings"])
        assert build(client, "shop", 20, 20).status_code == 400
        r = client.post("/api/iso/remove-building/", {"placement_id": placement(player, "market").id}, format="json")
        assert r.status_code == 400
        r = client.post("/api/iso/upgrade-building/", {"placement_id": placement(player, "shop").id}, format="json")
        assert r.status_code == 400

    def test_free_starting_building_refunds_nothing(self, new_player):
        player, client = new_player
        before = player.profile.coins_balance
        r = client.post("/api/iso/remove-building/", {"placement_id": placement(player, "farming-field").id}, format="json")
        assert r.status_code == 200 and r.data["refunded"] == 0 and r.data["coins_balance"] == before


@pytest.mark.django_db
class TestStorage:
    def test_item_storage_flags(self, game_data):
        barn = set(ShopItem.objects.filter(storage="barn").values_list("slug", flat=True))
        assert {"wheat", "wheat_harvest", "chicken_food", "eggs", "milk"} <= barn
        assert not {"wood", "board", "bread", "ketchup"} & barn

    def test_summary(self, new_player):
        player, client = new_player
        give(player, "wheat_harvest", 30)
        give(player, "wood", 7)
        data = client.get("/api/storage/").data
        assert data["barn"]["capacity"] == 250 and data["barn"]["used"] == 30 and data["barn"]["free"] == 220
        assert data["warehouse"]["capacity"] == 500 and data["warehouse"]["used"] == 7
        assert [i["slug"] for i in data["warehouse"]["items"]] == ["wood"]

    def test_capacity_adds_up(self, new_player):
        player, client = new_player
        rich(player)
        assert build(client, "barn", 20, 20).status_code == 200
        assert client.get("/api/storage/").data["barn"]["capacity"] == 500

    def test_shop_purchase_blocked_when_full(self, new_player):
        player, client = new_player
        give(player, "wheat_harvest", 245)
        seed = ShopItem.objects.get(slug="wheat")
        r = client.post("/api/shop/buy/", {"item_id": seed.id, "quantity": 6}, format="json")
        assert r.status_code == 400 and r.data["free"] == 5
        assert client.post("/api/shop/buy/", {"item_id": seed.id, "quantity": 5}, format="json").status_code == 200

    def test_harvest_blocked_when_full(self, new_player):
        player, client = new_player
        field = placement(player, "farming-field")
        seed = ShopItem.objects.get(slug="wheat")
        plot = FarmPlot.objects.create(
            profile=player.profile, building=field, cell_row=0, cell_col=0, seed=seed,
            ready_at=timezone.now() - timezone.timedelta(seconds=1), status="ready",
        )
        give(player, "wheat_harvest", 249)
        assert client.post("/api/iso/harvest/", {"plot_id": plot.id}, format="json").status_code == 400
        give(player, "wheat_harvest", 248)
        assert client.post("/api/iso/harvest/", {"plot_id": plot.id}, format="json").status_code == 200

    def test_extraction_pauses_when_full(self, new_player):
        player, client = new_player
        rich(player)
        hut = build(client, "lumberjack_hut", 20, 20).data["building"]["id"]
        client.post("/api/extraction/start/", {"building_id": hut}, format="json")
        give(player, "wood", 497)
        ExtractionProcess.objects.filter(building_id=hut).update(
            next_harvest_at=timezone.now() - timezone.timedelta(hours=1)  # 60 циклов
        )
        client.get("/api/extraction/status/")
        assert InventoryItem.objects.get(player=player.profile, item__slug="wood").quantity == 500
        # пауза: следующий цикл отсчитывается от текущего момента, накопленное не копится
        assert ExtractionProcess.objects.get(building_id=hut).next_harvest_at > timezone.now()

    def test_cannot_sell_storage_if_goods_dont_fit(self, new_player):
        player, client = new_player
        rich(player)
        give(player, "milk", 10)
        barn = placement(player, "barn").id
        assert client.post("/api/iso/remove-building/", {"placement_id": barn}, format="json").status_code == 400
        build(client, "barn", 20, 20)
        assert client.post("/api/iso/remove-building/", {"placement_id": barn}, format="json").status_code == 200


@pytest.mark.django_db
class TestLevels:
    def test_formulas(self, game_data):
        barn = BuildingType.objects.get(slug="barn")
        assert barn.upgrade_price(1) == 100 and barn.upgrade_price(2) == 160
        assert barn.capacity_at(1) == 250 and barn.capacity_at(10) == 1375
        field = BuildingType.objects.get(slug="farming-field")
        assert field.yield_factor(10) == pytest.approx(1.9)
        assert field.speed_reduction(10) == pytest.approx(0.27)
        assert BuildingType.objects.get(slug="bakery").speed_reduction(10) == pytest.approx(0.45)
        assert BuildingType.objects.get(slug="house").yield_factor(10) == 1

    def test_skill_and_level_bonuses_add_up_with_floor(self):
        assert work_duration(1000, 0, 0.45) == 550
        assert work_duration(1000, 10, 0.45) == 350          # −20% навык −45% уровень
        assert farming_duration(1000, 10, 0.95) == 200       # не быстрее 20%

    def test_upgrade(self, new_player):
        player, client = new_player
        barn = placement(player, "barn")
        before = player.profile.coins_balance
        r = client.post("/api/iso/upgrade-building/", {"placement_id": barn.id}, format="json")
        assert r.status_code == 200
        assert r.data["paid"] == 100 and r.data["coins_balance"] == before - 100
        assert r.data["building"]["level"] == 2 and r.data["building"]["capacity"] == 375
        assert r.data["building"]["upgrade_price"] == 160
        assert client.get("/api/storage/").data["barn"]["capacity"] == 375

    def test_upgrade_limits(self, new_player):
        player, client = new_player
        barn = placement(player, "barn")
        BuildingPlacement.objects.filter(id=barn.id).update(level=10)
        r = client.post("/api/iso/upgrade-building/", {"placement_id": barn.id}, format="json")
        assert r.status_code == 400
        player.profile.coins_balance = 0
        player.profile.save()
        field = placement(player, "farming-field")
        assert client.post("/api/iso/upgrade-building/", {"placement_id": field.id}, format="json").status_code == 400

    def test_timed_upgrade_finishes_later(self, new_player):
        player, client = new_player
        BuildingType.objects.filter(slug="barn").update(upgrade_seconds=60)
        barn = placement(player, "barn")
        r = client.post("/api/iso/upgrade-building/", {"placement_id": barn.id}, format="json")
        assert r.data["building"]["level"] == 1 and r.data["building"]["upgrade_finishes_at"]
        assert client.post("/api/iso/upgrade-building/", {"placement_id": barn.id}, format="json").status_code == 400
        BuildingPlacement.objects.filter(id=barn.id).update(upgrade_finishes_at=timezone.now())
        client.get("/api/iso/field/")
        assert placement(player, "barn").level == 2

    def test_field_level_increases_yield_and_speed(self, new_player):
        player, client = new_player
        field = placement(player, "farming-field")
        BuildingPlacement.objects.filter(id=field.id).update(level=6)  # +50% урожая, −15% времени
        seed = ShopItem.objects.get(slug="wheat")
        r = client.post("/api/iso/plant-seed/", {
            "building_id": field.id, "cell_row": 0, "cell_col": 0, "seed_id": seed.id,
        }, format="json")
        assert r.status_code == 200
        plot = FarmPlot.objects.get(id=r.data["plot"]["id"])
        grow = (plot.ready_at - plot.planted_at).total_seconds()
        assert grow == pytest.approx(seed.grow_time_minutes * 60 * 0.85, abs=1)

        FarmPlot.objects.filter(id=plot.id).update(ready_at=timezone.now(), status="ready")
        r = client.post("/api/iso/harvest/", {"plot_id": plot.id}, format="json")
        assert r.status_code == 200 and r.data["harvest"]["quantity"] == 3  # 2 × 1.5


@pytest.mark.django_db
class TestAppearance:
    LOOK = {"v": 2, "shape": 11, "details": 22, "colors": {"wall": "#C0392B", "roof": "#3e2723", "window": "#fafafa"}}
    SAVED = {"v": 2, "shape": 11, "details": 22, "colors": {"wall": "#c0392b", "roof": "#3e2723", "window": "#fafafa"}}

    def post(self, client, slug, appearance):
        return client.post("/api/iso/building-appearance/", {"slug": slug, "appearance": appearance}, format="json")

    def test_change_costs_500_and_applies_to_type(self, new_player):
        player, client = new_player
        rich(player)
        before = player.profile.coins_balance
        r = self.post(client, "barn", self.LOOK)
        assert r.status_code == 200 and r.data["paid"] == 500 and r.data["coins_balance"] == before - 500
        state = client.get("/api/iso/field/").data
        assert state["appearances"] == {"barn": self.SAVED} and state["appearance_price"] == 500  # цвета в нижнем регистре

        recolor = {"v": 2, "shape": 0, "details": 0, "colors": {"wall": "#123456", "roof": "#654321", "window": "#ffffff"}}
        r = self.post(client, "barn", recolor)  # новая смена (перекраска исходной формы) — снова 500
        assert r.status_code == 200 and r.data["coins_balance"] == before - 1000
        assert self.post(client, "barn", recolor).status_code == 400  # тот же вид

    def test_service_buildings_can_change_too(self, new_player):
        _, client = new_player
        assert self.post(client, "shop", self.LOOK).status_code == 200

    def test_not_enough_coins(self, new_player):
        player, client = new_player
        player.profile.coins_balance = 499
        player.profile.save()
        assert self.post(client, "barn", self.LOOK).status_code == 400
        assert client.get("/api/iso/field/").data["appearances"] == {}

    def test_reset_is_free(self, new_player):
        player, client = new_player
        self.post(client, "barn", self.LOOK)
        player.profile.refresh_from_db()
        balance = player.profile.coins_balance
        r = self.post(client, "barn", None)
        assert r.status_code == 200 and r.data["paid"] == 0 and r.data["coins_balance"] == balance
        assert client.get("/api/iso/field/").data["appearances"] == {}

    @pytest.mark.parametrize("bad", [
        {"c": 1, "r": 2, "d": 3},                                              # старый формат v1
        {"v": 1, "shape": 1, "details": 1, "colors": None},
        {"v": 2, "shape": -1, "details": 1, "colors": None},
        {"v": 2, "shape": True, "details": 1, "colors": None},
        {"v": 2, "shape": 1, "details": 1, "colors": {"wall": "red", "roof": "#000000", "window": "#ffffff"}},
        {"v": 2, "shape": 1, "details": 1, "colors": {"wall": "#000000", "roof": "#000000"}},
        {"v": 2, "shape": 0, "details": 0, "colors": None},                    # стандартный вид — только бесплатный сброс
        [1, 2, 3],
    ])
    def test_validation(self, new_player, bad):
        _, client = new_player
        assert self.post(client, "barn", bad).status_code == 400

    def test_unknown_building(self, new_player):
        _, client = new_player
        assert self.post(client, "castle", self.LOOK).status_code == 404
