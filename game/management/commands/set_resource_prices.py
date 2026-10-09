"""
Django management command: set_resource_prices

Sets prices for resource items.
Usage: python manage.py set_resource_prices
"""
from django.core.management.base import BaseCommand
from game.models import ShopItem


# Resource prices
RESOURCE_PRICES = {
    'wood': 5,
    'stone': 8,
    'iron-ore': 20,
    'iron-ingot': 50,
    'gold-ore': 50,
    'gold-ingot': 120,
    'copper-ore': 15,
    'copper-ingot': 35,
}


class Command(BaseCommand):
    help = 'Set prices for resource items'

    def handle(self, *args, **options):
        updated = 0

        for slug, price in RESOURCE_PRICES.items():
            try:
                item = ShopItem.objects.get(slug=slug)
                old_price = item.price_coins
                if old_price != price:
                    item.price_coins = price
                    item.save()
                    self.stdout.write(f"  {slug}: {old_price} -> {price}")
                    updated += 1
                else:
                    self.stdout.write(f"  {slug}: already {price}")
            except ShopItem.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"  {slug}: not found"))

        self.stdout.write(self.style.SUCCESS(f"\nDone! Updated: {updated} items"))
