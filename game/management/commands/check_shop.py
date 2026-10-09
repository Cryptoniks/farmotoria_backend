"""
Django management command: check_shop

Checks shop items and their categories.
Usage: python manage.py check_shop
"""
from django.core.management.base import BaseCommand
from game.models import ShopItem, ItemCategory


class Command(BaseCommand):
    help = 'Check shop items and categories'

    def handle(self, *args, **options):
        self.stdout.write("=== Item Categories ===")
        for cat in ItemCategory.objects.all():
            self.stdout.write(f"  {cat.id}: {cat.name} ({cat.slug})")

        self.stdout.write("\n=== Shop Items by Category ===")
        for cat in ItemCategory.objects.all():
            items = ShopItem.objects.filter(category=cat)
            self.stdout.write(f"\n  {cat.name} ({items.count()} items):")
            for item in items:
                self.stdout.write(f"    {item.slug}: {item.name} - {item.price_coins} coins")
