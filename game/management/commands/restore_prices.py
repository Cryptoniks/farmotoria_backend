"""
Django management command: restore_prices

Restores original prices for shop items from a reference.
Usage: python manage.py restore_prices
"""
from django.core.management.base import BaseCommand
from game.models import ShopItem


# Reference prices to restore
PRICE_REFERENCE = {
    # Resources
    'wood': 5,
    'stone': 8,
    'iron-ore': 20,
    'iron-ingot': 50,
    'gold-ore': 50,
    'gold-ingot': 120,
    # Seeds
    'wheat_seed': 10,
    'corn_seed': 15,
    'sunflower_seed': 20,
    # Harvest
    'wheat': 12,
    'corn': 18,
    'sunflower': 25,
}


class Command(BaseCommand):
    help = 'Restore original prices for shop items'

    def handle(self, *args, **options):
        restored = 0

        for slug, price in PRICE_REFERENCE.items():
            try:
                item = ShopItem.objects.get(slug=slug)
                old_price = item.price_coins
                item.price_coins = price
                item.save()
                self.stdout.write(f"  Restored {slug}: {old_price} -> {price}")
                restored += 1
            except ShopItem.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"  {slug}: not found"))

        self.stdout.write(self.style.SUCCESS(f"\nDone! Restored: {restored} items"))
