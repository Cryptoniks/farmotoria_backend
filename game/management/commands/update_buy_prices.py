"""
Django management command: update_buy_prices

Updates buy prices (sell_price) for shop items.
Usage: python manage.py update_buy_prices
"""
from django.core.management.base import BaseCommand
from game.models import ShopItem


class Command(BaseCommand):
    help = 'Update buy/sell prices for shop items'

    def handle(self, *args, **options):
        updated = 0

        for item in ShopItem.objects.all():
            # Sell price is typically 50% of buy price
            sell_price = int(item.price_coins * 0.5)

            if item.sell_price != sell_price:
                item.sell_price = sell_price
                item.save()
                self.stdout.write(
                    f"  {item.slug}: sell_price {item.sell_price} -> {sell_price}"
                )
                updated += 1

        self.stdout.write(self.style.SUCCESS(f"\nDone! Updated: {updated} items"))
