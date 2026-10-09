"""
Django management command: check_skills

Lists all skills and their configuration.
Usage: python manage.py check_skills
"""
from django.core.management.base import BaseCommand
from game.models import Skill


class Command(BaseCommand):
    help = 'Check all skills'

    def handle(self, *args, **options):
        self.stdout.write("=== Skills ===")
        for s in Skill.objects.all():
            self.stdout.write(
                f"  {s.code}: {s.name} "
                f"(max_level={s.max_level}, base_exp={s.base_exp}, "
                f"growth={s.exp_growth}, effect={s.effect_name})"
            )
