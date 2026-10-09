"""
Django management command: create_agroproduction

Creates agroproduction buildings (chicken-coop, pigsty, cowshed, sheepfold).
Usage: python manage.py create_agroproduction
"""
from django.core.management.base import BaseCommand
from game.models import BuildingType


AGROBUILDINGS = [
    {"name": "Курятник", "slug": "chicken-coop", "width": 2, "height": 2, "price": 500},
    {"name": "Свинарник", "slug": "pigsty", "width": 3, "height": 3, "price": 1000},
    {"name": "Коровник", "slug": "cowshed", "width": 4, "height": 4, "price": 5000},
    {"name": "Овчарня", "slug": "sheepfold", "width": 3, "height": 3, "price": 2500},
]


class Command(BaseCommand):
    help = 'Create agroproduction building types'

    def handle(self, *args, **options):
        created = 0
        updated = 0

        for data in AGROBUILDINGS:
            building, is_new = BuildingType.objects.update_or_create(
                slug=data["slug"],
                defaults={
                    "name": data["name"],
                    "building_type": BuildingType.TYPE_AGROPRODUCTION,
                    "width": data["width"],
                    "height": data["height"],
                    "price": data["price"],
                }
            )
            if is_new:
                created += 1
                self.stdout.write(self.style.SUCCESS(f'✓ Created: {building.name}'))
            else:
                updated += 1
                self.stdout.write(f'✓ Updated: {building.name}')

        self.stdout.write(self.style.SUCCESS(f"\nDone! Created: {created}, Updated: {updated}"))
