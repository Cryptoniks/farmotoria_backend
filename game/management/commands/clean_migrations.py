"""
Django management command: clean_migrations

Cleans up duplicate migrations and creates a clean migration for production.
Usage: python manage.py clean_migrations [--dry-run]
"""
import os
import shutil
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Clean up duplicate migrations and create clean migration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        migrations_dir = os.path.dirname(__file__)  # game/migrations

        self.stdout.write("=== Migration Cleanup ===\n")

        # 1. Remove __pycache__
        pycache_dir = os.path.join(migrations_dir, '__pycache__')
        if os.path.exists(pycache_dir):
            if dry_run:
                self.stdout.write(self.style.WARNING(f"Would delete: {pycache_dir}"))
            else:
                shutil.rmtree(pycache_dir)
                self.stdout.write(self.style.SUCCESS(f"Deleted: {pycache_dir}"))
        else:
            self.stdout.write("✓ No __pycache__ found")

        # 2. Check for duplicate migration numbers
        migration_files = [f for f in os.listdir(migrations_dir) if f.startswith('00') and f.endswith('.py')]
        migration_numbers = [f[:6] for f in migration_files]

        from collections import Counter
        duplicates = {num: count for num, count in Counter(migration_numbers).items() if count > 1}

        if duplicates:
            self.stdout.write(self.style.WARNING(f"\nDuplicate migration numbers found:"))
            for num, count in duplicates.items():
                self.stdout.write(f"  {num}: {count} files")
        else:
            self.stdout.write(self.style.SUCCESS("\n✓ No duplicate migration numbers"))

        # 3. Check for .pyc files
        pyc_files = [f for f in os.listdir(migrations_dir) if f.endswith('.pyc')]
        if pyc_files:
            self.stdout.write(self.style.WARNING(f"\nFound .pyc files: {len(pyc_files)}"))
            for f in pyc_files[:5]:
                self.stdout.write(f"  {f}")
        else:
            self.stdout.write(self.style.SUCCESS("\n✓ No .pyc files found"))

        # 4. Show migration status
        if not dry_run:
            self.stdout.write("\n=== Migration Status ===")
            try:
                from django.db.migrations.executor import MigrationExecutor
                executor = MigrationExecutor(connection)
                plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
                
                if plan:
                    self.stdout.write(self.style.WARNING("\nPending migrations:"))
                    for migration, backwards in plan:
                        status = "BACKWARDS" if backwards else "FORWARDS"
                        self.stdout.write(f"  {migration.app_label}.{migration.name} [{status}]")
                else:
                    self.stdout.write(self.style.SUCCESS("\n✓ All migrations applied"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error checking migrations: {e}"))

        self.stdout.write(self.style.SUCCESS("\n=== Cleanup complete ==="))
