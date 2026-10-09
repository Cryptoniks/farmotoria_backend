from django.core.management.base import BaseCommand
from django.db import transaction

from game.models import PlayerProfile, FieldChunk, CHUNK_SIZE, START_UNLOCKED_SIZE, STARTING_COINS


class Command(BaseCommand):
    help = "Сброс и создание стартовых чанков (50x50 = 5x5 чанков) для всех профилей"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Сбросить баланс до 500 монет и удалить все купленные чанки",
        )

    @transaction.atomic
    def handle(self, *args, **kwargs):
        reset = kwargs.get("reset", False)

        if reset:
            # Сброс: обнуляем балансы, удаляем все чанки
            PlayerProfile.objects.update(coins_balance=0)
            FieldChunk.objects.all().delete()
            self.stdout.write(self.style.WARNING("Балансы обнулены, все чанки удалены"))

        chunk_count_side = START_UNLOCKED_SIZE // CHUNK_SIZE  # 50/10=5
        total_created = 0

        for profile in PlayerProfile.objects.all():
            # Если чанков нет — создаём стартовые
            if not FieldChunk.objects.filter(profile=profile).exists():
                objs = [
                    FieldChunk(
                        profile=profile,
                        chunk_row=cr,
                        chunk_col=cc,
                        price_paid=0,
                    )
                    for cr in range(chunk_count_side)
                    for cc in range(chunk_count_side)
                ]
                FieldChunk.objects.bulk_create(objs, ignore_conflicts=True)
                total_created += len(objs)

            # Если сброс — даём стартовые монеты
            if reset:
                profile.coins_balance = STARTING_COINS
                profile.save(update_fields=["coins_balance"])

        action = "Сброшено и создано" if reset else "Создано"
        self.stdout.write(self.style.SUCCESS(f"{action} чанков: {total_created}"))