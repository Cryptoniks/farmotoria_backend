import pytest

from game.models import InventoryItem, ShopItem


@pytest.mark.django_db
class TestAuth:
    def test_ping_is_public(self, client):
        assert client.get("/api/farmotoria/ping/").status_code == 200

    def test_register_and_login(self, client, game_data):
        r = client.post("/api/auth/register/", {"username": "newbie", "password": "Str0ng-pass-123"}, format="json")
        assert r.status_code == 201
        r = client.post("/api/auth/token/", {"username": "newbie", "password": "Str0ng-pass-123"}, format="json")
        assert r.status_code == 200 and "access" in r.data and "refresh" in r.data

    def test_register_rejects_weak_password(self, client):
        r = client.post("/api/auth/register/", {"username": "weak", "password": "12345678"}, format="json")
        assert r.status_code == 400 and "password" in r.data

    def test_me_requires_auth(self, client):
        assert client.get("/api/me/").status_code == 401

    def test_me_get_and_update(self, auth_client, game_data):
        r = auth_client.get("/api/me/")
        assert r.status_code == 200 and r.data["username"] == "player"
        assert {s["name"] for s in r.data["skills"]} >= {"Земледелие", "Добыча"}
        r = auth_client.put("/api/me/", {"username": "renamed", "email": "a@b.ru"}, format="json")
        assert r.status_code == 200 and r.data["username"] == "renamed"


@pytest.mark.django_db
class TestShopAndMarket:
    def test_seeds_list(self, auth_client, game_data):
        r = auth_client.get("/api/shop/seeds/")
        assert r.status_code == 200
        assert all(i["is_seed"] for i in r.data) and len(r.data) == 9

    def test_buy_and_sell(self, auth_client, user, game_data):
        bread = ShopItem.objects.get(slug="bread")
        start = user.profile.coins_balance
        r = auth_client.post("/api/shop/buy/", {"item_id": bread.id, "quantity": 10}, format="json")
        assert r.status_code == 400  # на 10 хлебов стартовых монет не хватает

        r = auth_client.post("/api/shop/buy/", {"item_id": bread.id, "quantity": 1}, format="json")
        assert r.status_code == 200
        assert r.data["coins_balance"] == start - bread.buy_price

        r = auth_client.post("/api/market/sell/", {"item_id": bread.id, "quantity": 1}, format="json")
        assert r.status_code == 200
        assert r.data["coins_balance"] == start - bread.buy_price + bread.price_coins
        assert not InventoryItem.objects.filter(player=user.profile, item=bread).exists()

    @pytest.mark.parametrize("qty", [0, -5, "abc"])
    def test_invalid_quantity_rejected(self, auth_client, user, game_data, qty):
        item = ShopItem.objects.get(slug="wood")
        InventoryItem.objects.create(player=user.profile, item=item, quantity=3)
        before = user.profile.coins_balance
        assert auth_client.post("/api/shop/buy/", {"item_id": item.id, "quantity": qty}, format="json").status_code == 400
        assert auth_client.post("/api/market/sell/", {"item_id": item.id, "quantity": qty}, format="json").status_code == 400
        user.profile.refresh_from_db()
        assert user.profile.coins_balance == before

    def test_cannot_sell_more_than_owned(self, auth_client, user, game_data):
        item = ShopItem.objects.get(slug="wood")
        InventoryItem.objects.create(player=user.profile, item=item, quantity=1)
        r = auth_client.post("/api/market/sell/", {"item_id": item.id, "quantity": 2}, format="json")
        assert r.status_code == 400

    def test_market_inventory(self, auth_client, game_data):
        r = auth_client.get("/api/market/inventory/")
        assert r.status_code == 200
        assert not any(i["item_slug"] == "wheat" for i in r.data)  # семена не продаются
