"""
Django management command: check_production_recipes

Checks production recipes for agroproduction buildings.
Usage: python manage.py check_production_recipes
"""
from django.core.management.base import BaseCommand
from game.models import Recipe, BuildingType


class Command(BaseCommand):
    help = 'Check production recipes for agroproduction buildings'

    def handle(self, *args, **options):
        self.stdout.write("=== Production Recipes ===")
        for r in Recipe.objects.filter(recipe_group='production'):
            self.stdout.write(
                f"  {r.slug}: {r.name}, building={r.building_type}, "
                f"output={r.output_item.name}, duration={r.duration_seconds}s"
            )

        self.stdout.write("\n=== Agroproduction Recipes ===")
        for r in Recipe.objects.filter(recipe_group='agroproduction'):
            self.stdout.write(
                f"  {r.slug}: {r.name}, building={r.building_type}, "
                f"output={r.output_item.name}"
            )
