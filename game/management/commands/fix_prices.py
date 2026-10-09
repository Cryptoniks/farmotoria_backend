"""
Django management command: fix_prices

Fixes shop item prices based on item type and category.
Usage: python manage.py fix_prices [--dry-run]
"""
from django.core.management.base import BaseCommand
from game.models import ShopItem


class Command(BaseCommand):
    help = 'Fix shop item prices'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Show changes without applying')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        action = 'DRY RUN - ' if dry_run else ''

        self.stdout.write(self.style.WARNING(f"{action}Fixing prices..."))

        # Example: fix resource prices
        resources = ShopItem.objects.filter(is_resource=True)
        for item in resources:
            old_price = item.price_coins
            # Set base price for resources
            if old_price == 0:
                item.price_coins = 5
                item.save()
                self.stdout.write(f"  Fixed {item.slug}: {old_price} -> {item.price_coins}")

        # Example: fix harvest product prices
        harvests = ShopItem.objects.filter(is_harvest=True)
        for item in harvests:
            old_price = item.price_coins
            if old_price == 0:
                item.price_coins = 10
                item.save()
                self.stdout.write(f"  Fixed {item.slug}: {old_price} -> {item.price_coins}")

        if dry_run:
            self.stdout.write(self.style.WARNING(f"{action}No changes were made"))
        else:
            self.stdout.write(self.style.SUCCESS("Prices fixed!"))
