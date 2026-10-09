"""
Django management command: create_animals

Creates animal feed items, animal products, and production recipes.
Usage: python manage.py create_animals
"""
from django.core.management.base import BaseCommand
from game.models import ShopItem, ItemCategory, Recipe, RecipeIngredient, BuildingType


class Command(BaseCommand):
    help = 'Create animal feeds, products, and production recipes'

    def handle(self, *args, **options):
        # Categories
        feed_cat, _ = ItemCategory.objects.get_or_create(name="Корма")
        animal_cat, _ = ItemCategory.objects.get_or_create(name="Продукты животноводства")

        # Feeds
        feeds = [
            ("chicken_food", "Корм для кур", 10),
            ("pig_food", "Корм для свиней", 15),
            ("cow_food", "Корм для коров", 20),
            ("sheep_food", "Корм для овец", 18),
        ]

        # Products
        products = [
            ("eggs", "Яйца", 8),
            ("pork", "Свинина", 25),
            ("milk", "Молоко", 30),
            ("wool", "Шерсть", 35),
        ]

        self.stdout.write("=== Creating feeds and products ===\n")

        feed_items = {}
        for slug, name, price in feeds:
            item, created = ShopItem.objects.get_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "category": feed_cat,
                    "price_coins": price,
                    "is_resource": True,
                }
            )
            feed_items[slug] = item
            status = 'Created' if created else 'Exists'
            self.stdout.write(f'  {status}: Корм - {name} (price={price})')

        product_items = {}
        for slug, name, price in products:
            item, created = ShopItem.objects.get_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "category": animal_cat,
                    "price_coins": price,
                    "is_harvest": True,
                    "harvest_yield": 1,
                }
            )
            product_items[slug] = item
            status = 'Created' if created else 'Exists'
            self.stdout.write(f'  {status}: Продукт - {name} (price={price})')

        # Recipes for buildings
        recipes_config = [
            {
                "building_slug": "chicken-coop",
                "recipe_name": "Покормить кур",
                "recipe_slug": "feed-chickens",
                "feed_slug": "chicken_food",
                "product_slug": "eggs",
                "duration": 600,
                "output_qty": 2,
            },
            {
                "building_slug": "pigsty",
                "recipe_name": "Покормить свиней",
                "recipe_slug": "feed-pigs",
                "feed_slug": "pig_food",
                "product_slug": "pork",
                "duration": 900,
                "output_qty": 2,
            },
            {
                "building_slug": "cowshed",
                "recipe_name": "Покормить коров",
                "recipe_slug": "feed-cows",
                "feed_slug": "cow_food",
                "product_slug": "milk",
                "duration": 1800,
                "output_qty": 2,
            },
            {
                "building_slug": "sheepfold",
                "recipe_name": "Покормить овец",
                "recipe_slug": "feed-sheep",
                "feed_slug": "sheep_food",
                "product_slug": "wool",
                "duration": 1200,
                "output_qty": 2,
            },
        ]

        self.stdout.write("\n=== Creating recipes ===\n")

        for config in recipes_config:
            building = BuildingType.objects.get(slug=config["building_slug"])
            feed = feed_items[config["feed_slug"]]
            product = product_items[config["product_slug"]]

            recipe, created = Recipe.objects.update_or_create(
                slug=config["recipe_slug"],
                defaults={
                    "name": config["recipe_name"],
                    "recipe_group": "agroproduction",
                    "building_type": building,
                    "price": 0,
                    "duration_seconds": config["duration"],
                    "output_item": product,
                    "output_quantity": config["output_qty"],
                }
            )

            RecipeIngredient.objects.get_or_create(
                recipe=recipe,
                item=feed,
                defaults={"quantity": 1}
            )

            status = 'Created' if created else 'Updated'
            self.stdout.write(
                f"  {status}: {config['recipe_name']} -> {config['output_qty']} x {product.name}"
            )

        self.stdout.write(self.style.SUCCESS("\n=== Done! ==="))
