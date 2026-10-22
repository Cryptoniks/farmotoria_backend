import pytest
from django.contrib.auth.models import User
from django.core.management import call_command
from rest_framework.test import APIClient


@pytest.fixture
def game_data(db):
    call_command("seed_game_data", verbosity=0)
    # Игроки, созданные до справочников, остались без стартовых зданий и, значит, без хранилищ.
    # Даём им Склад и Сарай в дальнем углу стартовой зоны, где тесты ничего не строят.
    from game.models import BuildingPlacement, BuildingType, PlayerProfile

    for profile in PlayerProfile.objects.all():
        for slug, row, col in (("warehouse", 40, 40), ("barn", 46, 46)):
            bt = BuildingType.objects.get(slug=slug)
            BuildingPlacement.objects.create(
                profile=profile, building_type=bt, row=row, col=col, width=bt.width, height=bt.height,
            )


@pytest.fixture
def new_player(game_data, django_user_model):
    """Игрок, зарегистрированный после заполнения справочников: со стартовыми зданиями."""
    player = django_user_model.objects.create_user(username="newbie", password="Str0ng-pass-123")
    client = APIClient()
    client.force_authenticate(user=player)
    return player, client


@pytest.fixture
def user(db):
    return User.objects.create_user(username="player", password="Str0ng-pass-123")


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def auth_client(client, user):
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def rich(user):
    """Игроку хватает монет на всё."""
    user.profile.coins_balance = 100_000
    user.profile.save()
    return user
