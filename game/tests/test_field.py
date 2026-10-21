import pytest
from django.utils import timezone

from game.models import BuildingPlacement, BuildingType, FarmPlot, InventoryItem, ShopItem


def place(client, slug, row, col):
    bt = BuildingType.objects.get(slug=slug)
    return client.post("/api/iso/place-building/", {"building_id": bt.id, "row": row, "col": col}, format="json")


@pytest.mark.django_db
class TestField:
    def test_field_state(self, auth_client, game_data):
        r = auth_client.get("/api/iso/field/")
        assert r.status_code == 200
        assert len(r.data["chunks"]) == 25 and r.data["field"]["next_chunk_cost"] == 100
        assert any(b["slug"] == "farming-field" for b in r.data["available_buildings"])

    def test_buy_chunk(self, auth_client, game_data):
        assert auth_client.get("/api/iso/available-chunks/").data["available_chunks"]
        r = auth_client.post("/api/iso/expand-chunk/", {"chunk_row": 0, "chunk_col": 5}, format="json")
        assert r.status_code == 200 and r.data["paid"] == 100 and r.data["next_cost"] == 200
        r = auth_client.post("/api/iso/expand-chunk/", {"chunk_row": 20, "chunk_col": 20}, format="json")
        assert r.status_code == 400  # не рядом с купленными

    def test_place_overlap_and_locked_area(self, auth_client, rich, game_data):
        assert place(auth_client, "farming-field", 0, 0).status_code == 200
        assert place(auth_client, "farming-field", 1, 1).status_code == 400  # пересечение
        assert place(auth_client, "farming-field", 49, 49).status_code == 400  # вылезает в некупленный чанк
        assert place(auth_client, "farming-field", 0, 2).status_code == 200

    def test_move_detects_partial_overlap(self, auth_client, rich, game_data):
        """Раньше перемещение не видело зданий, левый верхний угол которых вне новой области."""
        a = place(auth_client, "quarry", 5, 5).data["building"]["id"]   # 3x3: 5..7
        b = place(auth_client, "quarry", 0, 0).data["building"]["id"]   # 3x3: 0..2
        r = auth_client.post("/api/iso/move-building/", {"placement_id": b, "row": 6, "col": 6}, format="json")
        assert r.status_code == 400
        r = auth_client.post("/api/iso/move-building/", {"placement_id": b, "row": 10, "col": 10}, format="json")
        assert r.status_code == 200
        assert BuildingPlacement.objects.get(id=a).row == 5

    def test_batch_move(self, auth_client, rich, game_data):
        a = place(auth_client, "farming-field", 0, 0).data["building"]["id"]
        b = place(auth_client, "farming-field", 0, 2).data["building"]["id"]
        r = auth_client.post("/api/iso/move-buildings/", {"moves": [
            {"placement_id": a, "row": 10, "col": 10},
            {"placement_id": b, "row": 10, "col": 10},   # занято только что перемещённым
            {"placement_id": "x", "row": 1, "col": 1},
        ]}, format="json")
        assert r.status_code == 200
        assert len(r.data["moved"]) == 1 and len(r.data["errors"]) == 2

    def test_remove_refunds(self, auth_client, user, game_data):
        r = place(auth_client, "farming-field", 0, 0)
        balance = r.data["coins_balance"]
        r = auth_client.post("/api/iso/remove-building/", {"placement_id": r.data["building"]["id"]}, format="json")
        assert r.status_code == 200 and r.data["coins_balance"] == balance + 100

    def test_plant_and_harvest(self, auth_client, user, game_data):
        field_id = place(auth_client, "farming-field", 0, 0).data["building"]["id"]
        seed = ShopItem.objects.get(slug="wheat")
        payload = {"building_id": field_id, "cell_row": 0, "cell_col": 0, "seed_id": seed.id}
        r = auth_client.post("/api/iso/plant-seed/", payload, format="json")
        assert r.status_code == 200
        assert auth_client.post("/api/iso/plant-seed/", payload, format="json").status_code == 400  # занято

        plot_id = r.data["plot"]["id"]
        assert auth_client.post("/api/iso/harvest/", {"plot_id": plot_id}, format="json").status_code == 400
        assert auth_client.post("/api/iso/remove-building/", {"placement_id": field_id}, format="json").status_code == 400

        FarmPlot.objects.filter(id=plot_id).update(ready_at=timezone.now() - timezone.timedelta(seconds=1))
        plots = auth_client.get("/api/iso/plots/").data["plots"]
        assert plots[0]["status"] == "ready"

        r = auth_client.post("/api/iso/harvest/", {"plot_id": plot_id}, format="json")
        assert r.status_code == 200 and r.data["harvest"]["quantity"] == 2
        assert InventoryItem.objects.get(player=user.profile, item__slug="wheat_harvest").quantity == 2
        assert r.data["skill_level"] >= 0 and r.data["player_exp"] > 0

        # клетку можно засеять снова
        assert auth_client.post("/api/iso/plant-seed/", payload, format="json").status_code == 200

    def test_bad_params_return_400(self, auth_client, game_data):
        r = auth_client.post("/api/iso/place-building/", {"row": "a"}, format="json")
        assert r.status_code == 400
