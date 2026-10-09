"""
Django management command: check_model

Checks model fields and their configuration.
Usage: python manage.py check_model [--model MODEL_NAME]
"""
from django.core.management.base import BaseCommand, CommandParser
from django.db import models


class Command(BaseCommand):
    help = 'Check Django model fields'

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument('--model', type=str, default=None, help='Model name to check')

    def handle(self, *args, **options):
        from game import models as game_models

        models_to_check = {}
        for name in dir(game_models):
            obj = getattr(game_models, name)
            if isinstance(obj, type) and issubclass(obj, models.Model):
                models_to_check[name] = obj

        if options['model']:
            if options['model'] in models_to_check:
                model_class = models_to_check[options['model']]
                self.stdout.write(f"=== Model: {options['model']} ===")
                for field in model_class._meta.get_fields():
                    field_type = type(field).__name__
                    self.stdout.write(f"  {field.name}: {field_type}")
            else:
                self.stdout.write(self.style.ERROR(f"Model '{options['model']}' not found"))
                self.stdout.write("Available models:")
                for name in models_to_check:
                    self.stdout.write(f"  {name}")
        else:
            self.stdout.write("=== All Game Models ===")
            for name, model_class in models_to_check.items():
                field_count = len(model_class._meta.get_fields())
                self.stdout.write(f"  {name}: {field_count} fields")
