"""
Django management command: check_chunks

Checks field chunks and building placements for a user.
Usage: python manage.py check_chunks [--username USERNAME]
"""
from django.core.management.base import BaseCommand, CommandParser
from django.contrib.auth.models import User
from game.models import PlayerProfile, FieldChunk, BuildingPlacement


class Command(BaseCommand):
    help = 'Check field chunks and building placements for a user'

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument('--username', type=str, default='test5', help='Username to check')

    def handle(self, *args, **options):
        username = options['username']
        user = User.objects.filter(username=username).first()

        if not user:
            self.stdout.write(self.style.ERROR(f'User {username} not found'))
            return

        profile = PlayerProfile.objects.get(user=user)
        chunks = list(FieldChunk.objects.filter(profile=profile).values('chunk_row', 'chunk_col'))
        placements = list(
            BuildingPlacement.objects.filter(profile=profile).values(
                'row', 'col', 'width', 'height', 'building_type__slug'
            )
        )

        self.stdout.write(f"User: {user.username}")
        self.stdout.write(f"Chunks: {len(chunks)}")
        for c in chunks:
            self.stdout.write(f"  chunk_row={c['chunk_row']}, chunk_col={c['chunk_col']}")

        self.stdout.write(f"\nPlacements: {len(placements)}")
        for p in placements:
            self.stdout.write(
                f"  row={p['row']}, col={p['col']}, size={p['width']}x{p['height']}, "
                f"type={p['building_type__slug']}"
            )
