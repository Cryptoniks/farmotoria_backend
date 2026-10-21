import pytest
from django.utils import timezone

from game.models import BuildingType, ExtractionProcess, InventoryItem, RecipeProcess, ShopItem


def place(client, slug, row=0, col=0):
    bt = BuildingType.objects.get(slug=slug)
    r = client.post("/api/iso/place-building/", {"building_id": bt.id, "row": row, "col": col}, format="json")
    assert r.status_code == 200, r.data
    return r.data["building"]["id"]


def qty(user, slug):
    inv = InventoryItem.objects.filter(player=user.profile, item__slug=slug).first()
    return inv.quantity if inv else 0


@pytest.mark.django_db
class TestExtraction:
    def test_lazy_accrual(self, auth_client, user, game_data):
        building = place(auth_client, "lumberjack_hut")
        r = auth_client.post("/api/extraction/start/", {"building_id": building}, format="json")
        assert r.status_code == 200 and r.data["duration_seconds"] == 60
        assert auth_client.post("/api/extraction/start/", {"building_id": building}, format="json").status_code == 400

        # прошло 5 циклов с хвостиком
        ExtractionProcess.objects.update(next_harvest_at=timezone.now() - timezone.timedelta(seconds=250))
        r = auth_client.get("/api/extraction/status/")
        assert r.status_code == 200 and r.data["collected"][0]["cycles"] == 5
        assert qty(user, "wood") == 5
        # повторный запрос ничего не начисляет
        auth_client.get("/api/extraction/status/")
        assert qty(user, "wood") == 5
        assert ExtractionProcess.objects.get().next_harvest_at > timezone.now()

    def test_collect_and_stop(self, auth_client, user, game_data):
        building = place(auth_client, "quarry")
        pid = auth_client.post("/api/extraction/start/", {"building_id": building}, format="json").data["process_id"]
        assert auth_client.post("/api/extraction/collect/", {"process_id": pid}, format="json").status_code == 400
        ExtractionProcess.objects.update(next_harvest_at=timezone.now())
        r = auth_client.post("/api/extraction/collect/", {"process_id": pid}, format="json")
        assert r.status_code == 200 and r.data["collected"]["quantity"] == 1
        assert auth_client.post("/api/iso/remove-building/", {"placement_id": building}, format="json").status_code == 400
        assert auth_client.post("/api/extraction/stop/", {"process_id": pid}, format="json").status_code == 200
        assert auth_client.post("/api/iso/remove-building/", {"placement_id": building}, format="json").status_code == 200

    def test_not_extraction_building(self, auth_client, game_data):
        building = place(auth_client, "farming-field")
        assert auth_client.post("/api/extraction/start/", {"building_id": building}, format="json").status_code == 400


@pytest.mark.django_db
class TestProcessing:
    def give(self, user, slug, n):
        InventoryItem.objects.create(player=user.profile, item=ShopItem.objects.get(slug=slug), quantity=n)

    def test_recipes_only_for_own_building(self, auth_client, rich, game_data):
        recipes = auth_client.get("/api/processing/recipes/?building_type=mill").data
        assert {r["slug"] for r in recipes} >= {"flour", "chicken-food"}
        assert all(r["slug"] != "bread" for r in recipes)
        assert auth_client.get("/api/processing/recipes/?building_type=house").data == []

    def test_full_cycle_takes_n_times_longer(self, auth_client, rich, game_data):
        building = place(auth_client, "sawmill")
        self.give(rich, "wood", 7)
        recipe = next(r for r in auth_client.get("/api/processing/recipes/?building_type=sawmill").data)
        assert recipe["max_possible"] == 3

        start = {"building_id": building, "recipe_id": recipe["id"]}
        r = auth_client.post("/api/processing/start/", {**start, "quantity": 4}, format="json")
        assert r.status_code == 400 and r.data["max_possible"] == 3
        r = auth_client.post("/api/processing/start/", {**start, "quantity": 3}, format="json")
        assert r.status_code == 200 and r.data["total_duration"] == 3 * r.data["duration_per_one"]
        assert qty(rich, "wood") == 1

        pid = r.data["id"]
        # прошёл один цикл — собрать всё ещё нельзя (раньше было можно)
        p = RecipeProcess.objects.get(id=pid)
        shift = timezone.timedelta(seconds=r.data["duration_per_one"] + 1)
        RecipeProcess.objects.filter(id=pid).update(started_at=p.started_at - shift, ready_at=p.ready_at - shift)
        status = auth_client.get("/api/processing/status/").data[0]
        assert status["quantity_done"] == 1 and not status["all_complete"]
        assert auth_client.post("/api/processing/collect/", {"process_id": pid}, format="json").status_code == 400

        # остановка: 1 готовая доска + возврат дерева за 2 цикла
        r = auth_client.post("/api/processing/stop/", {"process_id": pid}, format="json")
        assert r.status_code == 200 and r.data["produced"] == 1 and r.data["stopped_cycles"] == 2
        assert qty(rich, "board") == 1 and qty(rich, "wood") == 5

    def test_collect_when_complete(self, auth_client, rich, game_data):
        building = place(auth_client, "chicken-coop")
        self.give(rich, "chicken_food", 2)
        recipe = auth_client.get("/api/processing/recipes/?building_type=chicken-coop").data[0]
        start = {"building_id": building, "recipe_id": recipe["id"], "quantity": 2}
        r = auth_client.post("/api/processing/start/", start, format="json")
        RecipeProcess.objects.update(ready_at=timezone.now())
        r = auth_client.post("/api/processing/collect/", {"process_id": r.data["id"]}, format="json")
        assert r.status_code == 200 and r.data["quantity"] == 4
        assert qty(rich, "eggs") == 4
