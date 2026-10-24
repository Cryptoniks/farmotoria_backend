from django.db import migrations


def reset_appearances(apps, schema_editor):
    """Генератор внешнего вида перешёл на формат v2 (форма, детали, цвета) — старые виды v1
    нарисовались бы иначе, поэтому сбрасываем их к стандартному (игроков пока нет)."""
    apps.get_model("game", "PlayerBuildingAppearance").objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [("game", "0003_player_building_appearance")]

    operations = [migrations.RunPython(reset_appearances, migrations.RunPython.noop)]
