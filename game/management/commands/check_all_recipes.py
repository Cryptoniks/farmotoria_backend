"""
Django management command: check_all_recipes

Checks all recipes and validates their structure.
Usage: python manage.py check_all_recipes
"""
from django.core.management.base import BaseCommand
from game.models import Recipe, ShopItem


class Command(BaseCommand):
    help = 'Check all recipes and validate structure'

    def handle(self, *args, **options):
        self.stdout.write("=== All Recipes ===\n")

        total = Recipe.objects.count()
        self.stdout.write(f"Total recipes: {total}\n")

        issues = 0

        for recipe in Recipe.objects.all():
            issues_list = []

            # Check output item
            if not recipe.output_item:
                issues_list.append('no output item')
                issues += 1

            # Check ingredients
            if not recipe.ingredients.exists():
                issues_list.append('no ingredients')

            # Check duration
            if not recipe.duration_seconds or recipe.duration_seconds <= 0:
                issues_list.append('invalid duration')
                issues += 1

            # Check output quantity
            if not recipe.output_quantity or recipe.output_quantity <= 0:
                issues_list.append('invalid output quantity')
                issues += 1

            status = ''
            if issues_list:
                status = f" [ISSUES: {', '.join(issues_list)}]"

            self.stdout.write(
                f"  {recipe.slug}: {recipe.name} -> {recipe.output_item.name if recipe.output_item else 'N/A'}"
                f" (group={recipe.recipe_group}, building={recipe.building_type}, "
                f"duration={recipe.duration_seconds}s, qty={recipe.output_quantity}){status}"
            )

        if issues == 0:
            self.stdout.write(self.style.SUCCESS("\nAll recipes are valid!"))
        else:
            self.stdout.write(self.style.WARNING(f"\nIssues found: {issues}"))
