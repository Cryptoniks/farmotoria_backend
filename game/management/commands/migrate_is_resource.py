"""
Django management command: migrate_is_resource

Migrates items to have the is_resource flag set correctly.
Usage: python manage.py migrate_is_resource
"""
from django.core.management.base import BaseCommand
from game.models import ShopItem


class Command(BaseCommand):
    help = 'Migrate is_resource flag for shop items'

    def handle(self, *args, **options):
        updated = 0

        # Items that should be resources
        resource_slugs = [
            'wood', 'stone', 'iron-ore', 'iron-ingot', 'gold-ore', 'gold-ingot',
            'chicken_food', 'pig_food', 'cow_food', 'sheep_food',
        ]

        for item in ShopItem.objects.filter(slug__in=resource_slugs):
            if not item.is_resource:
                item.is_resource = True
                item.save()
                self.stdout.write(f"  Set is_resource=True: {item.slug}")
                updated += 1

        self.stdout.write(self.style.SUCCESS(f"\nDone! Updated: {updated} items"))
