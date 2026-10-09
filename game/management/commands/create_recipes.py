"""
Django management command: create_recipes

Creates basic crafting and processing recipes.
Usage: python manage.py create_recipes
"""
from django.core.management.base import BaseCommand
from game.models import ShopItem, Recipe, RecipeIngredient, BuildingType


class Command(BaseCommand):
    help = 'Create basic crafting recipes'

    def handle(self, *args, **options):
        recipes = [
            # (recipe_slug, recipe_name, ingredients, output_slug, output_qty, duration)
            (
                'iron-ingot-from-ore',
                'Переплавка железа',
                [('iron-ore', 2)],
                'iron-ingot',
                1,
                300,
            ),
            (
                'gold-ingot-from-ore',
                'Переплавка золота',
                [('gold-ore', 2)],
                'gold-ingot',
                1,
                600,
            ),
            (
                'sunflower-oil',
                'Подсолнечное масло',
                [('sunflower', 3)],
                'sunflower_oil',
                1,
                200,
            ),
        ]

        self.stdout.write("=== Creating recipes ===\n")

        for recipe_slug, recipe_name, ingredients, output_slug, output_qty, duration in recipes:
            output_item = ShopItem.objects.filter(slug=output_slug).first()
            if not output_item:
                self.stdout.write(self.style.WARNING(f"  Output item '{output_slug}' not found, skipping"))
                continue

            recipe, created = Recipe.objects.update_or_create(
                slug=recipe_slug,
                defaults={
                    'name': recipe_name,
                    'recipe_group': 'crafting',
                    'output_item': output_item,
                    'output_quantity': output_qty,
                    'duration_seconds': duration,
                    'price': 0,
                }
            )

            # Add ingredients
            for ing_slug, ing_qty in ingredients:
                ing_item = ShopItem.objects.filter(slug=ing_slug).first()
                if ing_item:
                    RecipeIngredient.objects.get_or_create(
                        recipe=recipe,
                        item=ing_item,
                        defaults={'quantity': ing_qty}
                    )

            status = 'Created' if created else 'Updated'
            self.stdout.write(f"  {status}: {recipe_name}")

        self.stdout.write(self.style.SUCCESS("\n=== Done! ==="))
