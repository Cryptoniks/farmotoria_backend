"""
Django management command: setup_processing

Sets up processing buildings and recipes.
Usage: python manage.py setup_processing
"""
from django.core.management.base import BaseCommand
from game.models import BuildingType, ItemCategory, ShopItem, Recipe, RecipeIngredient


class Command(BaseCommand):
    help = 'Set up processing buildings and recipes'

    def handle(self, *args, **options):
        self.stdout.write("Setting up processing buildings...")

        # Create processing building types
        processing_buildings = [
            {"slug": "crusher", "name": "Дробилка", "width": 2, "height": 2, "price": 500},
            {"slug": "smelter", "name": "Печь", "width": 2, "height": 3, "price": 1000},
            {"slug": "mill", "name": "Мельница", "width": 3, "height": 3, "price": 800},
        ]

        for data in processing_buildings:
            bt, created = BuildingType.objects.update_or_create(
                slug=data["slug"],
                defaults={
                    "name": data["name"],
                    "building_type": BuildingType.TYPE_PROCESSING,
                    "width": data["width"],
                    "height": data["height"],
                    "price": data["price"],
                }
            )
            status = "Created" if created else "Updated"
            self.stdout.write(f"  {status}: {data['name']}")

        self.stdout.write(self.style.SUCCESS("\nProcessing setup complete!"))
