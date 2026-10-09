"""
Django management command: link_recipes

Links recipes to their required building types.
Usage: python manage.py link_recipes
"""
from django.core.management.base import BaseCommand
from game.models import Recipe, BuildingType


# Mapping of recipe_slug -> building_slug
RECIPE_BUILDING_MAP = {
    'feed-chickens': 'chicken-coop',
    'feed-pigs': 'pigsty',
    'feed-cows': 'cowshed',
    'feed-sheep': 'sheepfold',
    'iron-ingot-from-ore': 'smelter',
    'gold-ingot-from-ore': 'smelter',
    'sunflower-oil': 'mill',
}


class Command(BaseCommand):
    help = 'Link recipes to their required building types'

    def handle(self, *args, **options):
        linked = 0
        not_found = 0

        for recipe_slug, building_slug in RECIPE_BUILDING_MAP.items():
            try:
                recipe = Recipe.objects.get(slug=recipe_slug)
                building = BuildingType.objects.get(slug=building_slug)

                if recipe.building_type != building:
                    recipe.building_type = building
                    recipe.save()
                    self.stdout.write(f"  Linked: {recipe_slug} -> {building_slug}")
                    linked += 1
                else:
                    self.stdout.write(f"  Already linked: {recipe_slug} -> {building_slug}")

            except Recipe.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"  Recipe '{recipe_slug}' not found"))
                not_found += 1
            except BuildingType.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"  Building '{building_slug}' not found"))
                not_found += 1

        self.stdout.write(
            self.style.SUCCESS(f"\nDone! Linked: {linked}, Not found: {not_found}")
        )
