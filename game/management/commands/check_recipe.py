"""
Django management command: check_recipe

Checks recipes for a specific group or all recipes.
Usage: python manage.py check_recipe [--group GROUP_NAME]
"""
from django.core.management.base import BaseCommand, CommandParser
from game.models import Recipe


class Command(BaseCommand):
    help = 'Check recipes, optionally filtered by group'

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument('--group', type=str, default=None, help='Recipe group to filter')

    def handle(self, *args, **options):
        group = options['group']

        if group:
            recipes = Recipe.objects.filter(recipe_group=group)
            self.stdout.write(f"Recipes in group '{group}':")
        else:
            recipes = Recipe.objects.all()
            self.stdout.write("All recipes:")

        for r in recipes:
            self.stdout.write(
                f"  {r.slug}: {r.name} -> {r.output_item.name} "
                f"(group={r.recipe_group}, building={r.building_type}, "
                f"duration={r.duration_seconds}s)"
            )
