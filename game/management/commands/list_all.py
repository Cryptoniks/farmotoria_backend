"""
Django management command: list_all

Lists recipes, buildings, or items.
Usage: python manage.py list_all [--type recipes|buildings|items]
"""
from django.core.management.base import BaseCommand, CommandParser
from game.models import Recipe, BuildingType, ShopItem


class Command(BaseCommand):
    help = 'List recipes, buildings, or items'

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            '--type',
            type=str,
            choices=['recipes', 'buildings', 'items'],
            default='recipes',
            help='What to list'
        )

    def handle(self, *args, **options):
        list_type = options['type']

        if list_type == 'recipes':
            self.stdout.write("=== All Recipes ===")
            for r in Recipe.objects.all():
                self.stdout.write(
                    f"  {r.slug}: {r.name} -> {r.output_item.name} "
                    f"(group={r.recipe_group}, building={r.building_type}, "
                    f"duration={r.duration_seconds}s, qty={r.output_quantity})"
                )

        elif list_type == 'buildings':
            self.stdout.write("=== All Buildings ===")
            for b in BuildingType.objects.all():
                self.stdout.write(
                    f"  {b.slug}: {b.name} (type={b.building_type}, "
                    f"size={b.width}x{b.height}, price={b.price})"
                )

        elif list_type == 'items':
            self.stdout.write("=== All Shop Items ===")
            for item in ShopItem.objects.all():
                self.stdout.write(
                    f"  {item.slug}: {item.name} "
                    f"(seed={item.is_seed}, harvest={item.is_harvest}, "
                    f"resource={item.is_resource}, price={item.price_coins})"
                )
