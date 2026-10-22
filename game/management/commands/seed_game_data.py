"""
Заполняет справочники игры: категории, навыки, культуры, здания,
ресурсы добычи и рецепты. Заменяет 15 старых команд create_*/fix_*/update_*.

    python manage.py seed_game_data            # добавить недостающее, существующее не трогать
    python manage.py seed_game_data --update   # перезаписать параметры данными из этого файла

Команда идемпотентна, поэтому запускается при каждом деплое на Render.
Цены и время — стартовый баланс; меняйте их здесь или в админке.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from game.models import (
    BuildingType,
    ExtractionResource,
    ItemCategory,
    Recipe,
    RecipeIngredient,
    ShopItem,
    Skill,
)

CAT_SEEDS = "Семена"
CAT_HARVEST = "Урожай"
CAT_RESOURCES = "Ресурсы"
CAT_PROCESSED = "Продукты переработки"
CAT_FEED = "Корма"
CAT_ANIMAL = "Продукты животноводства"
CAT_FOOD = "Продукция"

# code, название, max_level, base_exp, exp_growth, эффект, описание, значение за уровень
SKILLS = [
    ("farming", "Земледелие", 10, 50, 1.3, "Ускорение роста", "−1% времени созревания за уровень", 0.01),
    ("extraction", "Добыча", 10, 50, 1.3, "Ускорение добычи", "−2% времени цикла добычи за уровень", 0.02),
    ("processing", "Переработка", 10, 50, 1.3, "Ускорение переработки", "−2% времени переработки за уровень", 0.02),
    ("production", "Производство", 10, 50, 1.3, "Ускорение производства", "−2% времени производства за уровень", 0.02),
    ("agroproduction", "Животноводство", 10, 50, 1.3, "Ускорение животноводства", "−2% времени за уровень", 0.02),
]

# slug семени (= slug иконки на фронте), название, цена семени, минут роста, цена урожая, урожай с клетки
CROPS = [
    ("wheat", "Пшеница", 10, 2, 8, 2),
    ("oats", "Овёс", 8, 2, 6, 2),
    ("rutabaga", "Брюква", 12, 3, 9, 2),
    ("corn", "Кукуруза", 15, 4, 12, 2),
    ("peas", "Горох", 18, 5, 14, 2),
    ("tomato", "Томат", 20, 6, 16, 2),
    ("sunflower", "Подсолнечник", 25, 8, 20, 2),
    ("cabbage", "Капуста", 30, 10, 24, 2),
    ("soy", "Соя", 35, 12, 28, 2),
]

# название, slug, тип, ширина, высота, цена (список из SpriteInfo.txt)
BUILDINGS = [
    ("Фермерское поле", "farming-field", "field", 2, 2, 100),
    ("Магазин", "shop", "shop", 3, 3, 0),
    ("Рынок", "market", "market", 4, 3, 0),
    ("Дом", "house", "agroproduction", 2, 3, 50),
    ("Склад", "warehouse", "storage", 5, 5, 100),
    ("Сарай", "barn", "storage", 2, 2, 100),
    ("Лесорубка", "lumberjack_hut", "extraction", 2, 2, 100),
    ("Каменоломня", "quarry", "extraction", 3, 3, 100),
    ("Рудник", "mine", "extraction", 3, 3, 100),
    ("Водяная мельница", "water_mill", "extraction", 2, 2, 100),
    ("Лесопилка", "sawmill", "processing", 3, 2, 500),
    ("Каменотёс", "stonecutter_hut", "processing", 2, 2, 500),
    ("Кузница", "blacksmith", "processing", 3, 3, 500),
    ("Мельница", "mill", "processing", 2, 2, 500),
    ("Пекарня", "bakery", "production", 3, 3, 1000),
    ("Завод соусов", "sauce_factory", "production", 4, 3, 1000),
    ("Маслозавод", "butter_factory", "production", 4, 3, 1000),
    ("Курятник", "chicken-coop", "agroproduction", 2, 2, 500),
    ("Свинарник", "pigsty", "agroproduction", 3, 3, 1000),
    ("Коровник", "cowshed", "agroproduction", 4, 4, 5000),
    ("Овчарня", "sheepfold", "agroproduction", 3, 3, 2500),
]

# Бонусы уровня по типу здания: (выход продукции за уровень, сокращение времени за уровень)
LEVEL_BONUSES = {
    "field": (0.10, 0.03),
    "agroproduction": (0.10, 0.03),
    "extraction": (0.10, 0.03),
    "processing": (0.0, 0.05),
    "production": (0.0, 0.05),
}
NO_BONUS_BUILDINGS = {"house"}  # здания без функции: уровень есть, бонусов нет

# Хранилища: slug → (что хранит, вместимость на 1 уровне)
STORAGES = {"barn": ("barn", 250), "warehouse": ("warehouse", 500)}

# Товары этих категорий лежат в Сарае, остальные — на Складе
BARN_CATEGORIES = {CAT_SEEDS, CAT_HARVEST, CAT_FEED, CAT_ANIMAL}

# slug, название, категория, цена продажи, это ресурс добычи
ITEMS = [
    ("wood", "Древесина", CAT_RESOURCES, 3, True),
    ("stone", "Камень", CAT_RESOURCES, 4, True),
    ("ore", "Руда", CAT_RESOURCES, 8, True),
    ("water", "Вода", CAT_RESOURCES, 2, True),
    ("board", "Доски", CAT_PROCESSED, 10, False),
    ("stone-block", "Каменный блок", CAT_PROCESSED, 12, False),
    ("iron-ingot", "Железный слиток", CAT_PROCESSED, 35, False),
    ("flour", "Мука", CAT_PROCESSED, 30, False),
    ("sunflower_oil", "Подсолнечное масло", CAT_PROCESSED, 70, False),
    ("chicken_food", "Корм для кур", CAT_FEED, 6, False),
    ("pig_food", "Корм для свиней", CAT_FEED, 8, False),
    ("cow_food", "Корм для коров", CAT_FEED, 10, False),
    ("sheep_food", "Корм для овец", CAT_FEED, 9, False),
    ("eggs", "Яйца", CAT_ANIMAL, 8, False),
    ("pork", "Свинина", CAT_ANIMAL, 25, False),
    ("milk", "Молоко", CAT_ANIMAL, 30, False),
    ("wool", "Шерсть", CAT_ANIMAL, 35, False),
    ("bread", "Хлеб", CAT_FOOD, 80, False),
    ("ketchup", "Кетчуп", CAT_FOOD, 65, False),
    ("butter", "Сливочное масло", CAT_FOOD, 80, False),
]

# здание, название, slug ресурса, выход за цикл, секунд на цикл
EXTRACTION = [
    ("lumberjack_hut", "Рубка леса", "wood", 1, 60),
    ("quarry", "Добыча камня", "stone", 1, 90),
    ("mine", "Добыча руды", "ore", 1, 120),
    ("water_mill", "Забор воды", "water", 1, 45),
]

# slug, название, здание, [(ингредиент, кол-во)], результат, кол-во, секунд, опыт навыка
RECIPES = [
    ("boards", "Распил брёвен", "sawmill", [("wood", 2)], "board", 1, 120, 5),
    ("stone-blocks", "Обтёсывание камня", "stonecutter_hut", [("stone", 2)], "stone-block", 1, 120, 5),
    ("iron-ingot", "Выплавка железа", "blacksmith", [("ore", 3)], "iron-ingot", 1, 180, 5),
    ("flour", "Помол муки", "mill", [("wheat_harvest", 3)], "flour", 1, 120, 5),
    ("sunflower-oil", "Подсолнечное масло", "mill", [("sunflower_harvest", 3)], "sunflower_oil", 1, 180, 5),
    ("chicken-food", "Корм для кур", "mill", [("wheat_harvest", 2)], "chicken_food", 3, 60, 3),
    ("pig-food", "Корм для свиней", "mill", [("corn_harvest", 2)], "pig_food", 3, 60, 3),
    ("cow-food", "Корм для коров", "mill", [("oats_harvest", 2)], "cow_food", 3, 60, 3),
    ("sheep-food", "Корм для овец", "mill", [("peas_harvest", 2)], "sheep_food", 3, 60, 3),
    ("bread", "Выпечка хлеба", "bakery", [("flour", 2), ("water", 1)], "bread", 1, 240, 8),
    ("ketchup", "Кетчуп", "sauce_factory", [("tomato_harvest", 3), ("water", 1)], "ketchup", 1, 240, 8),
    ("butter", "Сливочное масло", "butter_factory", [("milk", 2)], "butter", 1, 300, 8),
    ("feed-chickens", "Покормить кур", "chicken-coop", [("chicken_food", 1)], "eggs", 2, 600, 5),
    ("feed-pigs", "Покормить свиней", "pigsty", [("pig_food", 1)], "pork", 2, 900, 5),
    ("feed-cows", "Покормить коров", "cowshed", [("cow_food", 1)], "milk", 2, 1800, 5),
    ("feed-sheep", "Покормить овец", "sheepfold", [("sheep_food", 1)], "wool", 2, 1200, 5),
]


class Command(BaseCommand):
    help = "Заполняет справочники игры (идемпотентно)"

    def add_arguments(self, parser):
        parser.add_argument("--update", action="store_true", help="перезаписать существующие записи")

    def upsert(self, model, lookup: dict, values: dict):
        if self.update:
            obj, created = model.objects.update_or_create(**lookup, defaults=values)
        else:
            obj, created = model.objects.get_or_create(**lookup, defaults=values)
        self.counter["created" if created else ("updated" if self.update else "kept")] += 1
        return obj

    @transaction.atomic
    def handle(self, *args, **options):
        self.update = options["update"]
        self.counter = {"created": 0, "updated": 0, "kept": 0}

        categories = {
            name: ItemCategory.objects.get_or_create(name=name)[0]
            for name in (CAT_SEEDS, CAT_HARVEST, CAT_RESOURCES, CAT_PROCESSED, CAT_FEED, CAT_ANIMAL, CAT_FOOD)
        }

        skills = {}
        for code, name, max_level, base_exp, growth, effect, descr, per_level in SKILLS:
            skills[code] = self.upsert(Skill, {"code": code}, {
                "name": name, "max_level": max_level, "base_exp": base_exp, "exp_growth": growth,
                "effect_name": effect, "effect_description": descr, "effect_value_per_level": per_level,
            })

        items = {}
        for slug, name, seed_price, minutes, harvest_price, harvest_yield in CROPS:
            harvest = self.upsert(ShopItem, {"slug": f"{slug}_harvest"}, {
                "name": name, "category": categories[CAT_HARVEST], "price_coins": harvest_price,
                "is_harvest": True, "harvest_yield": harvest_yield, "storage": ShopItem.STORAGE_BARN,
            })
            items[harvest.slug] = harvest
            items[slug] = self.upsert(ShopItem, {"slug": slug}, {
                "name": f"{name} (семена)", "category": categories[CAT_SEEDS], "price_coins": seed_price,
                "is_seed": True, "grow_time_minutes": minutes, "harvest_yield": harvest_yield,
                "harvest_item": harvest, "storage": ShopItem.STORAGE_BARN,
            })

        for slug, name, category, price, is_resource in ITEMS:
            items[slug] = self.upsert(ShopItem, {"slug": slug}, {
                "name": name, "category": categories[category], "price_coins": price,
                "is_resource": is_resource,
                "storage": ShopItem.STORAGE_BARN if category in BARN_CATEGORIES else ShopItem.STORAGE_WAREHOUSE,
            })

        buildings = {}
        for name, slug, kind, width, height, price in BUILDINGS:
            yield_bonus, speed_bonus = (0.0, 0.0) if slug in NO_BONUS_BUILDINGS else LEVEL_BONUSES.get(kind, (0.0, 0.0))
            storage, capacity = STORAGES.get(slug, ("", 0))
            buildings[slug] = self.upsert(BuildingType, {"slug": slug}, {
                "name": name, "building_type": kind, "width": width, "height": height, "price": price,
                "max_level": 1 if kind in BuildingType.SERVICE_TYPES else 10,
                "yield_bonus_per_level": yield_bonus, "speed_bonus_per_level": speed_bonus,
                "storage": storage, "capacity": capacity,
            })

        for building, name, item, qty, seconds in EXTRACTION:
            self.upsert(ExtractionResource, {"slug": item}, {
                "name": name, "building_type": buildings[building], "output_item": items[item],
                "output_quantity": qty, "duration_seconds": seconds,
            })

        for slug, name, building, ingredients, output, qty, seconds, skill_exp in RECIPES:
            bt = buildings[building]
            recipe = self.upsert(Recipe, {"slug": slug}, {
                "name": name, "recipe_group": bt.building_type, "building_type": bt,
                "output_item": items[output], "output_quantity": qty, "duration_seconds": seconds,
                "skill": skills.get(bt.building_type), "skill_exp": skill_exp, "price": 0,
            })
            for ingredient, amount in ingredients:
                self.upsert(RecipeIngredient, {"recipe": recipe, "item": items[ingredient]}, {"quantity": amount})

        c = self.counter
        self.stdout.write(self.style.SUCCESS(
            f"Справочники готовы: создано {c['created']}, обновлено {c['updated']}, без изменений {c['kept']}"
        ))
