"""
Django management command: update_prices_to_sell_price

Updates price_coins to match sell_price for all items.
Usage: python manage.py update_prices_to_sell_price
"""
from django.core.management.base import BaseCommand
from game.models import ShopItem


class Command(BaseCommand):
    help = 'Update price_coins to match sell_price'

    def handle(self, *args, **options):
        updated = 0

        for item in ShopItem.objects.all():
            if item.sell_price and item.price_coins != item.sell_price:
                old_price = item.price_coins
                item.price_coins = item.sell_price
                item.save()
                self.stdout.write(f"  {item.slug}: {old_price} -> {item.price_coins}")
                updated += 1

        self.stdout.write(self.style.SUCCESS(f"\nDone! Updated: {updated} items"))
