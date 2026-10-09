"""
Django management command: cleanup_old_items

Removes old feed and product items that were created with wrong slugs.
Usage: python manage.py cleanup_old_items
"""
from django.core.management.base import BaseCommand
from game.models import ShopItem, RecipeIngredient


class Command(BaseCommand):
    help = 'Clean up old feed and product items with incorrect slugs'

    def handle(self, *args, **options):
        # Remove old feeds with hyphen
        old_feeds = ShopItem.objects.filter(
            slug__in=['chicken-feed', 'pig-feed', 'cow-feed', 'sheep-feed']
        )
        self.stdout.write(f"Removing old feeds: {old_feeds.count()}")
        for f in old_feeds:
            self.stdout.write(f"  Removing: {f.slug}")
            RecipeIngredient.objects.filter(item=f).delete()
        old_feeds.delete()

        # Remove old products if created with wrong slug
        old_products = ShopItem.objects.filter(
            slug__in=['eggs', 'pork', 'milk', 'wool']
        )
        # Filter out the correct ones (eggs, pork, milk, wool ARE correct now)
        # Only remove if they have wrong properties
        old_products = old_products.filter(is_harvest=False) | old_products.filter(is_resource=False)
        self.stdout.write(f"Removing old products with wrong flags: {old_products.count()}")
        for p in old_products:
            self.stdout.write(f"  Removing: {p.slug}")
            RecipeIngredient.objects.filter(item=p).delete()
        old_products.delete()

        self.stdout.write(self.style.SUCCESS('\nCleanup complete!'))
