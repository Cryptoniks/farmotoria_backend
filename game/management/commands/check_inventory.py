"""
Django management command: check_inventory

Checks player inventory for a specific user.
Usage: python manage.py check_inventory [--username USERNAME]
"""
from django.core.management.base import BaseCommand, CommandParser
from django.contrib.auth.models import User
from game.models import InventoryItem, ShopItem


class Command(BaseCommand):
    help = 'Check player inventory'

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument('--username', type=str, default='test5', help='Username to check')

    def handle(self, *args, **options):
        username = options['username']
        user = User.objects.get(username=username)
        profile = user.profile

        self.stdout.write(f"Inventory for user '{username}':")
        inv = InventoryItem.objects.filter(player=profile).select_related('item')

        if not inv.exists():
            self.stdout.write(self.style.WARNING('  (empty)'))
            return

        for item in inv:
            self.stdout.write(
                f"  {item.item.name} (slug={item.item.slug}): {item.quantity} шт, "
                f"price={item.item.price_coins} coins"
            )

        # Check specific item if requested
        self.stdout.write("\n=== Search for chicken_feed ===")
        chicken_feed = ShopItem.objects.filter(slug='chicken_food').first()
        if chicken_feed:
            self.stdout.write(f"ShopItem: id={chicken_feed.id}, name={chicken_feed.name}")
            inv_item = InventoryItem.objects.filter(player=profile, item=chicken_feed).first()
            if inv_item:
                self.stdout.write(f"In inventory: {inv_item.quantity} шт")
            else:
                self.stdout.write("In inventory: 0 шт (or no record)")
        else:
            self.stdout.write(self.style.WARNING('chicken_food not found in database!'))
