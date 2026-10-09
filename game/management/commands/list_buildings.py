"""
Django management command: list_buildings

Lists all building types with details.
Usage: python manage.py list_buildings
"""
from django.core.management.base import BaseCommand
from game.models import BuildingType


class Command(BaseCommand):
    help = 'List all building types'

    def handle(self, *args, **options):
        self.stdout.write("=== All Buildings ===")
        for b in BuildingType.objects.all():
            self.stdout.write(
                f"  {b.slug}: {b.name} "
                f"(type={b.building_type}, "
                f"size={b.width}x{b.height}, "
                f"price={b.price} coins)"
            )
