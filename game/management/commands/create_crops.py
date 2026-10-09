"""
Django management command: create_crops

Creates crop plants and seed items.
Usage: python manage.py create_crops
"""
from django.core.management.base import BaseCommand
from game.models import ShopItem, ItemCategory, Plant


class Command(BaseCommand):
    help = 'Create crop plants and seed items'

    def handle(self, *args, **options):
        seeds_cat, _ = ItemCategory.objects.get_or_create(name="Семена")
        harvest_cat, _ = ItemCategory.objects.get_or_create(name="Урожай")

        crops = [
            # (seed_slug, seed_name, harvest_slug, harvest_name, seed_price, grow_time)
            ('wheat', 'Пшеница', 'wheat', 'Пшеница', 10, 300),
            ('corn', 'Кукуруза', 'corn', 'Кукуруза', 15, 400),
            ('sunflower', 'Подсолнух', 'sunflower', 'Подсолнух', 20, 500),
            ('potato', 'Картофель', 'potato', 'Картофель', 12, 350),
            ('carrot', 'Морковь', 'carrot', 'Морковь', 8, 250),
        ]

        self.stdout.write("=== Creating crops ===\n")

        for seed_slug, seed_name, harvest_slug, harvest_name, seed_price, grow_time in crops:
            # Create seed
            seed, created = ShopItem.objects.get_or_create(
                slug=seed_slug + '_seed',
                defaults={
                    'name': seed_name + ' (семена)',
                    'category': seeds_cat,
                    'price_coins': seed_price,
                    'is_seed': True,
                    'is_resource': True,
                }
            )

            # Create harvest product
            harvest, created = ShopItem.objects.get_or_create(
                slug=harvest_slug,
                defaults={
                    'name': harvest_name,
                    'category': harvest_cat,
                    'price_coins': int(seed_price * 1.2),
                    'is_harvest': True,
                    'harvest_yield': 1,
                }
            )

            # Create plant
            plant, created = Plant.objects.get_or_create(
                slug=harvest_slug,
                defaults={
                    'name': harvest_name,
                    'grow_duration_seconds': grow_time,
                    'harvest_product': harvest,
                    'description': f'Вырастить {harvest_name}',
                }
            )

            status = 'Created' if created else 'Exists'
            self.stdout.write(f"  {status}: {seed_name} -> {harvest_name}")

        self.stdout.write(self.style.SUCCESS("\n=== Done! ==="))
