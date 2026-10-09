"""
Django management command: find_profile_get

Finds all occurrences of PlayerProfile.objects.get in the codebase.
Usage: python manage.py find_profile_get
"""
from django.core.management.base import BaseCommand
import os
import glob


class Command(BaseCommand):
    help = 'Find all occurrences of PlayerProfile.objects.get in view files'

    def handle(self, *args, **options):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        views_dir = os.path.join(base_dir, 'game', 'views')

        self.stdout.write("Searching for PlayerProfile.objects.get in views...")

        for filepath in glob.glob(os.path.join(views_dir, '**', '*.py'), recursive=True):
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                for i, line in enumerate(content.split('\n'), 1):
                    if 'PlayerProfile.objects.get' in line:
                        self.stdout.write(f"  {os.path.basename(filepath)}:{i}: {line.strip()}")
