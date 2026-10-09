"""
Django management command: list_items

Lists all shop items with details.
Usage: python manage.py list_items
"""
from django.core.management.base import BaseCommand
from game.models import ShopItem


class Command(BaseCommand):
    help = 'List all shop items'

    def handle(self, *args, **options):
        self.stdout.write("=== All Shop Items ===")
        for item in ShopItem.objects.all():
            self.stdout.write(
                f"  {item.slug}: {item.name} "
                f"(category={item.category}, "
                f"seed={item.is_seed}, harvest={item.is_harvest}, "
                f"resource={item.is_resource}, "
                f"price={item.price_coins}, sell={item.sell_price})"
            )
