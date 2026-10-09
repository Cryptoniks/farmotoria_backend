"""
Django management command: check_placements

Checks building placements for a user.
Usage: python manage.py check_placements [--username USERNAME]
"""
from django.core.management.base import BaseCommand, CommandParser
from django.contrib.auth.models import User
from game.models import BuildingPlacement, BuildingType


class Command(BaseCommand):
    help = 'Check building placements for a user'

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument('--username', type=str, default='test5', help='Username to check')

    def handle(self, *args, **options):
        username = options['username']

        try:
            user = User.objects.get(username=username)
            self.stdout.write(f"User: {user.username}")

            buildings = BuildingPlacement.objects.filter(
                profile=user.profile
            ).select_related('building_type')

            self.stdout.write(f"\nTotal buildings: {buildings.count()}")
            for b in buildings:
                self.stdout.write(
                    f"  id={b.id}, type={b.building_type.slug}, "
                    f"building_type={b.building_type.building_type}, "
                    f"name={b.building_type.name}, "
                    f"row={b.row}, col={b.col}"
                )

            # Check specific building
            chicken = buildings.filter(building_type__slug='chicken-coop').first()
            if chicken:
                self.stdout.write(f"\nChicken coop: id={chicken.id}, slug={chicken.building_type.slug}")

        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User {username} not found'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {e}'))
