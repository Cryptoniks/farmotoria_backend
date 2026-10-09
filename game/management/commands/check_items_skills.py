"""
Django management command: check_items_skills

Checks items and their associated skills/recipes.
Usage: python manage.py check_items_skills
"""
from django.core.management.base import BaseCommand
from game.models import ShopItem, Recipe, RecipeIngredient


class Command(BaseCommand):
    help = 'Check items and their associated skills/recipes'

    def handle(self, *args, **options):
        self.stdout.write("=== Items used in recipes ===")

        used_items = set()
        for recipe in Recipe.objects.all():
            for ing in recipe.ingredients.all():
                used_items.add(ing.item)

        for item in ShopItem.objects.filter(id__in=used_items):
            recipes = Recipe.objects.filter(ingredients__item=item)
            self.stdout.write(
                f"  {item.slug}: {item.name} "
                f"(used in {recipes.count()} recipes)"
            )
            for r in recipes:
                self.stdout.write(f"    -> {r.name} ({r.recipe_group})")
