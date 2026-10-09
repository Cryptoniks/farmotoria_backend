"""
Django management command: check_feeds

Checks feed items in database and their recipe ingredients.
Usage: python manage.py check_feeds
"""
from django.core.management.base import BaseCommand
from game.models import ShopItem, Recipe, RecipeIngredient


class Command(BaseCommand):
    help = 'Check feed items and their recipe ingredients'

    def handle(self, *args, **options):
        self.stdout.write("=== Feeds in database (is_resource=True) ===")
        for item in ShopItem.objects.filter(is_resource=True):
            self.stdout.write(f"  {item.slug}: {item.name} (price={item.price_coins})")

        self.stdout.write("\n=== Recipe ingredients for feed-chickens ===")
        try:
            r = Recipe.objects.get(slug='feed-chickens')
            for ing in r.ingredients.all():
                self.stdout.write(f"  {ing.item.slug}: {ing.item.name} (qty={ing.quantity})")
        except Recipe.DoesNotExist:
            self.stdout.write(self.style.WARNING('Recipe feed-chickens not found'))
