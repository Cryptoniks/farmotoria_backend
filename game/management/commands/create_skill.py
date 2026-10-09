"""
Django management command: create_skill

Creates the Farming skill with exp/level mechanics.
Usage: python manage.py create_skill
"""
from django.core.management.base import BaseCommand
from game.models import Skill


class Command(BaseCommand):
    help = 'Create default skills (Farming, etc.)'

    def handle(self, *args, **options):
        skill, created = Skill.objects.get_or_create(
            code='farming',
            defaults={
                'name': 'Земледелие',
                'max_level': 10,
                'base_exp': 50,
                'exp_growth': 1.3,
                'effect_name': 'Ускорение роста',
                'effect_description': 'Уменьшает время созревания культур на 1% за уровень',
                'effect_value_per_level': 0.01,
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f'Created skill: {skill.name}'))
        else:
            self.stdout.write(f'Skill already exists: {skill.name}')

        self.stdout.write('\n=== All Skills ===')
        for s in Skill.objects.all():
            self.stdout.write(f"  {s.code}: {s.name} (max_level={s.max_level})")
