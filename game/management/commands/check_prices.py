"""
Django management command: check_prices

Checks shop item prices and optionally a specific user's inventory values.
Usage: python manage.py check_prices [--slug SLUG] [--username USERNAME]
"""
from django.core.management.base import BaseCommand, CommandParser
from django.contrib.auth.models import User
from game.models import ShopItem, InventoryItem


class Command(BaseCommand):
    help = 'Check shop prices and inventory values'

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument('--slug', type=str, default=None, help='Item slug to check')
        parser.add_argument('--username', type=str, default=None, help='User to check inventory')

    def handle(self, *args, **options):
        slug = options['slug']
        username = options['username']

        if slug:
            item = ShopItem.objects.filter(slug=slug).first()
            if item:
                self.stdout.write(f"Item '{slug}': price_coins={item.price_coins}, name={item.name}")
            else:
                self.stdout.write(self.style.ERROR(f"Item '{slug}' not found"))
            return

        # Check all items
        self.stdout.write("=== All Shop Items Prices ===")
        for item in ShopItem.objects.all():
            self.stdout.write(f"  {item.slug}: {item.price_coins} coins")

        if username:
            user = User.objects.get(username=username)
            inv = InventoryItem.objects.filter(player=user.profile).select_related('item')
            self.stdout.write(f"\n=== Inventory for {username} ===")
            total_value = 0
            for item in inv:
                value = item.quantity * item.item.price_coins
                total_value += value
                self.stdout.write(
                    f"  {item.item.name}: {item.quantity} x {item.item.price_coins} = {value}"
                )
            self.stdout.write(self.style.SUCCESS(f"Total inventory value: {total_value} coins"))
