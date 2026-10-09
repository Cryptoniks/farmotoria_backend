"""
Django management command: manage_categories

Manages item categories for the shop.
Usage: python manage.py manage_categories
"""
from django.core.management.base import BaseCommand
from game.models import ItemCategory


CATEGORIES = [
    ("seeds", "Семена", "Seed items for planting"),
    ("harvest", "Урожай", "Harvested crop products"),
    ("resources", "Ресурсы", "Raw materials and resources"),
    ("products", "Продукты", "Processed products"),
    ("animals", "Животные", "Animal-related items"),
    ("buildings", "Здания", "Placeable buildings"),
    ("tools", "Инструменты", "Tools and equipment"),
]


class Command(BaseCommand):
    help = 'Manage item categories'

    def handle(self, *args, **options):
        created = 0
        existing = 0

        for slug, name, description in CATEGORIES:
            cat, is_new = ItemCategory.objects.get_or_create(
                slug=slug,
                defaults={'name': name, 'description': description}
            )
            if is_new:
                created += 1
                self.stdout.write(self.style.SUCCESS(f"Created: {name}"))
            else:
                existing += 1
                self.stdout.write(f"  Exists: {name}")

        self.stdout.write(self.style.SUCCESS(f"\nDone! Created: {created}, Existing: {existing}"))
