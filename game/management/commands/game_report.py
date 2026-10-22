"""
Сводка по справочникам и проверка их целостности
(заменяет check_*/list_* команды).

    python manage.py game_report
"""
from django.core.management.base import BaseCommand
from django.db.models import Count

from game.models import (
    BuildingType,
    ExtractionResource,
    PlayerProfile,
    Recipe,
    ShopItem,
    Skill,
)


class Command(BaseCommand):
    help = "Сводка по игровым данным и поиск ошибок в справочниках"

    def handle(self, *args, **options):
        out = self.stdout
        out.write(f"Игроков: {PlayerProfile.objects.count()}")
        out.write(f"Навыки: {', '.join(Skill.objects.values_list('code', flat=True)) or '—'}")

        out.write("\nЗдания:")
        for bt in BuildingType.objects.annotate(n=Count("placements")).order_by("building_type", "slug"):
            out.write(f"  [{bt.building_type:<14}] {bt.slug:<16} {bt.width}x{bt.height}  {bt.price:>5} мон.  построено: {bt.n}")

        out.write(f"\nТоваров: {ShopItem.objects.count()} "
                  f"(семян {ShopItem.objects.filter(is_seed=True).count()}, "
                  f"урожая {ShopItem.objects.filter(is_harvest=True).count()}, "
                  f"ресурсов {ShopItem.objects.filter(is_resource=True).count()})")
        out.write(f"Рецептов: {Recipe.objects.count()}, ресурсов добычи: {ExtractionResource.objects.count()}")

        problems = []
        for seed in ShopItem.objects.filter(is_seed=True, harvest_item__isnull=True):
            problems.append(f"семя {seed.slug} без связанного урожая")
        for recipe in Recipe.objects.annotate(n=Count("ingredients")).filter(n=0):
            problems.append(f"рецепт {recipe.slug} без ингредиентов")
        for bt in BuildingType.objects.filter(building_type=BuildingType.TYPE_EXTRACTION):
            if not bt.extraction_resources.exists():
                problems.append(f"здание добычи {bt.slug} без ресурса")
        if not BuildingType.objects.filter(slug="farming-field").exists():
            problems.append("нет здания farming-field — посадка невозможна")
        for kind in BuildingType.SERVICE_TYPES:
            if not BuildingType.objects.filter(building_type=kind).exists():
                problems.append(f"нет здания типа {kind} — игроку негде покупать/продавать")
        for kind, _ in ShopItem.STORAGE_CHOICES:
            if not BuildingType.objects.filter(building_type=BuildingType.TYPE_STORAGE, storage=kind, capacity__gt=0).exists():
                problems.append(f"нет хранилища для товаров «{kind}» с вместимостью > 0")

        if problems:
            out.write(self.style.WARNING("\nПроблемы:"))
            for p in problems:
                out.write(self.style.WARNING(f"  • {p}"))
        else:
            out.write(self.style.SUCCESS("\nПроблем не найдено"))
