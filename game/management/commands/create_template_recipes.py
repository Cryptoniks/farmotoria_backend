"""
Django management command: create_template_recipes

Creates template recipes for various building types.
Usage: python manage.py create_template_recipes
"""
from django.core.management.base import BaseCommand
from game.models import ShopItem, ItemCategory, Recipe, RecipeIngredient, BuildingType, Skill


class Command(BaseCommand):
    help = 'Create template recipes for various building types'

    def handle(self, *args, **options):
        # Create products category if needed
        products_cat, _ = ItemCategory.objects.get_or_create(name="Продукты")

        items_data = [
            ("chicken_food", "Корм для курицы", 10),
            ("pig_food", "Корм для свиньи", 15),
            ("sheep_food", "Корм для овец", 18),
            ("cow_food", "Корм для коров", 20),
            ("sunflower_oil", "Подсолнечное масло", 25),
        ]

        self.stdout.write("=== Creating items ===")
        items = {}
        for slug, name, price in items_data:
            item, created = ShopItem.objects.get_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "category": products_cat,
                    "price_coins": price,
                    "is_resource": True,
                }
            )
            items[slug] = item
            status = 'Created' if created else 'Exists'
            self.stdout.write(f"  {status}: {name}")

        self.stdout.write(self.style.SUCCESS("\n=== Done! ==="))
