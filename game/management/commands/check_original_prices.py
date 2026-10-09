"""
Django management command: check_original_prices

Checks original prices before any modifications.
Usage: python manage.py check_original_prices
"""
from django.core.management.base import BaseCommand
from game.models import ShopItem


# Reference original prices
ORIGINAL_PRICES = {
    'wood': 5,
    'stone': 8,
    'iron-ore': 20,
    'iron-ingot': 50,
    'gold-ore': 50,
    'gold-ingot': 120,
    'wheat_seed': 10,
    'wheat': 12,
}


class Command(BaseCommand):
    help = 'Check original prices vs current prices'

    def handle(self, *args, **options):
        self.stdout.write("=== Original vs Current Prices ===\n")

        discrepancies = 0
        for slug, original_price in ORIGINAL_PRICES.items():
            try:
                item = ShopItem.objects.get(slug=slug)
                current_price = item.price_coins
                status = ''
                if current_price != original_price:
                    status = ' [MISMATCH]'
                    discrepancies += 1
                self.stdout.write(
                    f"  {slug}: original={original_price}, current={current_price}{status}"
                )
            except ShopItem.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"  {slug}: not found"))

        if discrepancies == 0:
            self.stdout.write(self.style.SUCCESS("\nAll prices match!"))
        else:
            self.stdout.write(self.style.WARNING(f"\nDiscrepancies: {discrepancies}"))
