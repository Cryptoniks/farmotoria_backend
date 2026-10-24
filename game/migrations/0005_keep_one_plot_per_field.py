from django.db import migrations


def keep_one_plot_per_field(apps, schema_editor):
    """Раньше поле 2×2 можно было засеять по клеткам — оставляем на каждом поле одну посадку:
    ту, что созреет раньше всех (остальные удаляются)."""
    FarmPlot = apps.get_model("game", "FarmPlot")
    seen = set()
    for plot in FarmPlot.objects.order_by("building_id", "ready_at", "id"):
        if plot.building_id in seen:
            plot.delete()
        else:
            seen.add(plot.building_id)


class Migration(migrations.Migration):
    dependencies = [("game", "0004_reset_appearances_v2")]

    operations = [migrations.RunPython(keep_one_plot_per_field, migrations.RunPython.noop)]
