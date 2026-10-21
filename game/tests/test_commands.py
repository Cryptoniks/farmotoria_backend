import pytest
from django.core.management import call_command

from game.models import BuildingType, Recipe, ShopItem


@pytest.mark.django_db
def test_seed_is_idempotent_and_keeps_admin_edits():
    call_command("seed_game_data", verbosity=0)
    counts = (ShopItem.objects.count(), BuildingType.objects.count(), Recipe.objects.count())
    BuildingType.objects.filter(slug="mill").update(price=1)
    call_command("seed_game_data", verbosity=0)
    assert (ShopItem.objects.count(), BuildingType.objects.count(), Recipe.objects.count()) == counts
    assert BuildingType.objects.get(slug="mill").price == 1
    call_command("seed_game_data", "--update", verbosity=0)
    assert BuildingType.objects.get(slug="mill").price == 500


@pytest.mark.django_db
def test_game_report_finds_no_problems(capsys):
    call_command("seed_game_data", verbosity=0)
    call_command("game_report")
    assert "Проблем не найдено" in capsys.readouterr().out
