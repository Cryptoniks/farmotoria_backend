"""
Django management command: test_sell

Tests the sell functionality for inventory items.
Usage: python manage.py test_sell [--username USERNAME]
"""
from django.core.management.base import BaseCommand, CommandParser
from django.contrib.auth.models import User
from game.models import InventoryItem, ShopItem


class Command(BaseCommand):
    help = 'Test sell functionality for inventory items'

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument('--username', type=str, default='test5', help='Username to test')

    def handle(self, *args, **options):
        username = options['username']

        try:
            user = User.objects.get(username=username)
            profile = user.profile

            self.stdout.write(f"Testing sell for user: {username}")
            self.stdout.write(f"Current coins: {profile.coins_balance}")

            # Get inventory items
            inv_items = InventoryItem.objects.filter(
                player=profile
            ).select_related('item')

            if not inv_items.exists():
                self.stdout.write(self.style.WARNING("Inventory is empty"))
                return

            total_sell_value = 0
            for inv_item in inv_items:
                sell_price = inv_item.item.price_coins  # Simple: sell at listed price
                item_value = inv_item.quantity * sell_price
                total_sell_value += item_value
                self.stdout.write(
                    f"  {inv_item.item.name}: {inv_item.quantity} x {sell_price} = {item_value}"
                )

            self.stdout.write(self.style.SUCCESS(f"\nTotal sell value: {total_sell_value} coins"))
            self.stdout.write(self.style.SUCCESS(f"New balance would be: {profile.coins_balance + total_sell_value} coins"))

        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"User {username} not found"))
