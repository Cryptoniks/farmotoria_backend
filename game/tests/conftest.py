import pytest
from django.contrib.auth.models import User
from django.core.management import call_command
from rest_framework.test import APIClient


@pytest.fixture
def game_data(db):
    call_command("seed_game_data", verbosity=0)


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
