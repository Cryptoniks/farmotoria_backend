"""
Django management command: check_buildings

Lists all building types and their properties.
Usage: python manage.py check_buildings
"""
from django.core.management.base import BaseCommand
from game.models import BuildingType


class Command(BaseCommand):
    help = 'Check all building types'

    def handle(self, *args, **options):
        self.stdout.write("All BuildingTypes:")
        for b in BuildingType.objects.all():
            self.stdout.write(f"  {b.slug}: name={b.name}, type={b.building_type}, price={b.price}")
