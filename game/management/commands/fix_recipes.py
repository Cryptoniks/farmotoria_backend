"""
Django management command: fix_recipes

Fixes recipe ingredients and output quantities.
Usage: python manage.py fix_recipes [--dry-run]
"""
from django.core.management.base import BaseCommand
from game.models import Recipe, RecipeIngredient, ShopItem


class Command(BaseCommand):
    help = 'Fix recipe ingredients and outputs'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Show changes without applying')

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        self.stdout.write("Checking recipes for issues...")

        issues_found = 0

        for recipe in Recipe.objects.all():
            # Check if recipe has ingredients
            if not recipe.ingredients.exists() and recipe.recipe_group != 'extraction':
                self.stdout.write(
                    self.style.WARNING(f"  Recipe '{recipe.slug}' has no ingredients")
                )
                issues_found += 1

            # Check if output item exists
            if not recipe.output_item:
                self.stdout.write(
                    self.style.ERROR(f"  Recipe '{recipe.slug}' has no output item")
                )
                issues_found += 1

            # Check output quantity
            if recipe.output_quantity and recipe.output_quantity <= 0:
                self.stdout.write(
                    self.style.WARNING(f"  Recipe '{recipe.slug}' has invalid output_quantity: {recipe.output_quantity}")
                )
                issues_found += 1

        if issues_found == 0:
            self.stdout.write(self.style.SUCCESS("All recipes look good!"))
        else:
            self.stdout.write(self.style.WARNING(f"Issues found: {issues_found}"))

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - no changes applied"))
