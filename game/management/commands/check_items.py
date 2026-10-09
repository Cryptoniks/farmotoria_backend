"""
Django management command: check_items

Lists all ShopItems and ExtractionResources.
Usage: python manage.py check_items
"""
from django.core.management.base import BaseCommand
from game.models import ShopItem, ExtractionResource


class Command(BaseCommand):
    help = 'Check all shop items and extraction resources'

    def handle(self, *args, **options):
        self.stdout.write("=== ShopItems ===")
        for item in ShopItem.objects.all():
            self.stdout.write(
                f"  {item.id}: {item.name} (slug={item.slug}, "
                f"seed={item.is_seed}, harvest={item.is_harvest}, "
                f"resource={item.is_resource}, price={item.price_coins})"
            )

        self.stdout.write("\n=== ExtractionResources ===")
        for res in ExtractionResource.objects.all():
            self.stdout.write(f"  {res.id}: {res.name} -> output_item={res.output_item}")
