"""
Django management command: update_resources

Updates resource items properties and prices.
Usage: python manage.py update_resources
"""
from django.core.management.base import BaseCommand
from game.models import ShopItem


class Command(BaseCommand):
    help = 'Update resource items properties'

    def handle(self, *args, **options):
        updated = 0

        # Ensure all raw materials are marked as resources
        resource_slugs = ['wood', 'stone', 'iron-ore', 'gold-ore', 'copper-ore']
        for slug in resource_slugs:
            try:
                item = ShopItem.objects.get(slug=slug)
                if not item.is_resource:
                    item.is_resource = True
                    item.save()
                    self.stdout.write(f"  Set is_resource=True: {slug}")
                    updated += 1
            except ShopItem.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"  {slug}: not found"))

        self.stdout.write(self.style.SUCCESS(f"\nDone! Updated: {updated} items"))
