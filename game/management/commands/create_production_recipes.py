"""
Django management command: create_production_recipes

Creates production recipes for agroprocessing.
Usage: python manage.py create_production_recipes
"""
from django.core.management.base import BaseCommand
from game.models import ShopItem, Recipe, RecipeIngredient, BuildingType


class Command(BaseCommand):
    help = 'Create production recipes for agroprocessing buildings'

    def handle(self, *args, **options):
        recipes = [
            # (recipe_name, recipe_slug, building, feed, output, duration, qty)
            ('Производство корма для кур', 'prod-chicken-feed', 'chicken-coop', 'wheat', 'chicken_food', 600, 5),
            ('Производство корма для свиней', 'prod-pig-feed', 'pigsty', 'corn', 'pig_food', 600, 5),
            ('Производство корма для коров', 'prod-cow-feed', 'cowshed', 'wheat', 'cow_food', 900, 5),
            ('Производство корма для овец', 'prod-sheep-feed', 'sheepfold', 'corn', 'sheep_food', 900, 5),
        ]

        self.stdout.write("=== Creating production recipes ===\n")

        for name, slug, building_slug, input_slug, output_slug, duration, qty in recipes:
            try:
                building = BuildingType.objects.get(slug=building_slug)
                input_item = ShopItem.objects.get(slug=input_slug)
                output_item = ShopItem.objects.get(slug=output_slug)

                recipe, created = Recipe.objects.update_or_create(
                    slug=slug,
                    defaults={
                        'name': name,
                        'recipe_group': 'production',
                        'building_type': building,
                        'output_item': output_item,
                        'output_quantity': qty,
                        'duration_seconds': duration,
                        'price': 0,
                    }
                )

                RecipeIngredient.objects.get_or_create(
                    recipe=recipe,
                    item=input_item,
                    defaults={'quantity': 2}
                )

                status = 'Created' if created else 'Updated'
                self.stdout.write(f"  {status}: {name}")

            except ShopItem.DoesNotExist as e:
                self.stdout.write(self.style.WARNING(f"  Item not found for {name}: {e}"))

        self.stdout.write(self.style.SUCCESS("\n=== Done! ==="))
