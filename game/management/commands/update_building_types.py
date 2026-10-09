"""
Django management command: update_building_types

Updates building type classifications.
Usage: python manage.py update_building_types
"""
from django.core.management.base import BaseCommand
from game.models import BuildingType


# Mapping of slug -> building_type
BUILDING_TYPE_MAP = {
    # Agriculture
    'greenhouse': BuildingType.TYPE_AGRICULTURE,
    'irrigation': BuildingType.TYPE_AGRICULTURE,
    # Processing
    'crusher': BuildingType.TYPE_PROCESSING,
    'smelter': BuildingType.TYPE_PROCESSING,
    'mill': BuildingType.TYPE_PROCESSING,
    # Storage
    'warehouse': BuildingType.TYPE_STORAGE,
    'storage': BuildingType.TYPE_STORAGE,
    # Agro production
    'chicken-coop': BuildingType.TYPE_AGROPRODUCTION,
    'pigsty': BuildingType.TYPE_AGROPRODUCTION,
    'cowshed': BuildingType.TYPE_AGROPRODUCTION,
    'sheepfold': BuildingType.TYPE_AGROPRODUCTION,
}


class Command(BaseCommand):
    help = 'Update building type classifications'

    def handle(self, *args, **options):
        updated = 0

        for slug, new_type in BUILDING_TYPE_MAP.items():
            try:
                building = BuildingType.objects.get(slug=slug)
                old_type = building.building_type
                if old_type != new_type:
                    building.building_type = new_type
                    building.save()
                    self.stdout.write(
                        f"  Updated {slug}: {old_type} -> {new_type}"
                    )
                    updated += 1
                else:
                    self.stdout.write(f"  {slug}: already correct ({new_type})")
            except BuildingType.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"  {slug}: not found"))

        self.stdout.write(self.style.SUCCESS(f"\nDone! Updated: {updated} buildings"))
