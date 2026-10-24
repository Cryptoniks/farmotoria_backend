from django.conf import settings
from django.db import models

User = settings.AUTH_USER_MODEL

# =========================
# Константы (перед моделями)
# =========================
CHUNK_SIZE = 10           # Размер чанка для покупки (10x10 клеток)
START_UNLOCKED_SIZE = 50  # Стартовое поле 50x50 клеток
MAX_FIELD_SIZE = 250      # Максимальное поле 250x250 клеток
STARTING_COINS = 500      # Стартовый баланс для нового игрока
APPEARANCE_CHANGE_PRICE = 500  # Смена внешнего вида типа здания (одинаково для всех зданий)

# Опыт за сбор урожая
PLAYER_EXP_PER_HARVEST = 10   # Опыт профилю за сбор
SKILL_EXP_PER_HARVEST = 20    # Опыт навыку за сбор

# Коды навыков
SKILL_FARMING = "farming"
SKILL_EXTRACTION = "extraction"

# Группы рецептов (совпадают с BuildingType.building_type и с кодом навыка)
RECIPE_GROUP_FIELD = "field"                    # Поле
RECIPE_GROUP_PROCESSING = "processing"          # Переработка
RECIPE_GROUP_PRODUCTION = "production"          # Производство
RECIPE_GROUP_AGROPRODUCTION = "agroproduction"  # Животноводство

RECIPE_GROUP_CHOICES = [
    (RECIPE_GROUP_FIELD, "Поле"),
    (RECIPE_GROUP_PROCESSING, "Переработка"),
    (RECIPE_GROUP_PRODUCTION, "Производство"),
    (RECIPE_GROUP_AGROPRODUCTION, "Животноводство"),
]


# =========================
# Профиль игрока
# =========================
class PlayerProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    coins_balance = models.PositiveIntegerField(default=0)
    level = models.PositiveIntegerField(default=1)
    exp = models.PositiveIntegerField(default=0)

    # Параметры для расчёта опыта
    base_exp = models.PositiveIntegerField(default=100)
    exp_growth = models.FloatField(default=1.5)

    class Meta:
        verbose_name = "Профиль игрока"

    def __str__(self):
        return f"Profile({self.user_id})"

    def required_exp_for_level(self, level: int) -> int:
        """Возвращает количество опыта для перехода на следующий уровень."""
        if level >= 100:  # Максимальный уровень
            return 0
        return int(self.base_exp * (self.exp_growth ** level))

    def add_exp(self, amount: int) -> None:
        """Добавляет опыт и повышает уровень при достижении порога."""
        if amount <= 0:
            return

        self.exp += amount

        while self.level < 100:
            need = self.required_exp_for_level(self.level)
            if need == 0:
                break
            if self.exp < need:
                break
            self.exp -= need
            self.level += 1

        # Если достигнут макс. уровень, сбрасываем exp
        if self.level >= 100:
            self.exp = 0

        self.save()

    @property
    def exp_to_next(self) -> int:
        """Возвращает количество опыта до следующего уровня."""
        if self.level >= 100:
            return 0
        return self.required_exp_for_level(self.level)


# =========================
# Категории товаров
# =========================
class ItemCategory(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


# =========================
# Товары магазина
# =========================
# Наценка для цены покупки в магазине (от цены продажи)
BUY_PRICE_MARKUP = 1.20


class ShopItem(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    slug = models.SlugField(max_length=100, unique=True)
    # Цена продажи (игрок продаёт магазину) - используется как базовая
    price_coins = models.PositiveIntegerField(
        default=0,
        help_text="Цена продажи (игрок продаёт магазину)"
    )
    category = models.ForeignKey(ItemCategory, on_delete=models.CASCADE)

    # Тип товара
    is_seed = models.BooleanField(default=False)
    is_harvest = models.BooleanField(default=False)  # Урожай с полей
    is_resource = models.BooleanField(default=False)  # Ресурсы добычи

    # Где хранится у игрока: Сарай (сельхоз) или Склад (всё остальное)
    STORAGE_BARN = "barn"
    STORAGE_WAREHOUSE = "warehouse"
    STORAGE_CHOICES = [(STORAGE_BARN, "Сарай"), (STORAGE_WAREHOUSE, "Склад")]
    storage = models.CharField(max_length=20, choices=STORAGE_CHOICES, default=STORAGE_WAREHOUSE)

    # Только для семян
    grow_time_minutes = models.PositiveIntegerField(null=True, blank=True)
    # Только для урожая
    harvest_yield = models.PositiveIntegerField(default=2, help_text="Количество урожая при сборе")

    # Связь семя → урожай
    harvest_item = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="seed_item",
        limit_choices_to={"is_harvest": True},
        help_text="Если это семя, то сюда ставим связанный урожай",
    )

    def __str__(self):
        type_flags = []
        if self.is_seed:
            type_flags.append("Seed")
        if self.is_harvest:
            type_flags.append("Harvest")
        if self.is_resource:
            type_flags.append("Resource")
        return f"{self.name} ({', '.join(type_flags)})"

    @property
    def buy_price(self):
        """
        Цена покупки в магазине.
        Для семян - равна цене продажи.
        Для остальных - цена продажи * 1.20
        """
        if self.is_seed:
            return self.price_coins
        # Округляем до ближайшего целого (round half to even)
        buy = round(self.price_coins * BUY_PRICE_MARKUP)
        if buy == self.price_coins:
            buy = self.price_coins + 1
        return buy


# =========================
# Инвентарь игрока
# =========================
class InventoryItem(models.Model):
    item = models.ForeignKey(ShopItem, on_delete=models.CASCADE)
    player = models.ForeignKey(PlayerProfile, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("player", "item")
        indexes = [
            models.Index(fields=["player"]),
            models.Index(fields=["item"]),
        ]

    def __str__(self):
        return f"{self.item.name} x{self.quantity}"


# =========================
# Навыки
# =========================
class Skill(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)

    max_level = models.PositiveIntegerField(default=10)

    base_exp = models.PositiveIntegerField(default=50)
    exp_growth = models.FloatField(default=1.3)

    effect_name = models.CharField(max_length=100)
    effect_description = models.TextField(blank=True)
    effect_value_per_level = models.FloatField(default=0.0)

    class Meta:
        verbose_name = "Навык"
        verbose_name_plural = "Навыки"

    def __str__(self):
        return self.name

    def required_exp_for_level(self, level: int) -> int:
        if level >= self.max_level:
            return 0
        return int(self.base_exp * (self.exp_growth ** level))


class UserSkill(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)

    level = models.PositiveIntegerField(default=0)
    exp = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("user", "skill")
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["skill"]),
        ]

    def add_exp(self, amount: int) -> None:
        if amount <= 0 or self.level >= self.skill.max_level:
            return

        self.exp += amount

        while self.level < self.skill.max_level:
            need = self.skill.required_exp_for_level(self.level)
            if self.exp < need or need == 0:
                break
            self.exp -= need
            self.level += 1

        if self.level >= self.skill.max_level:
            self.exp = 0

        self.save()

    @property
    def exp_to_next(self) -> int:
        if self.level >= self.skill.max_level:
            return 0
        return self.skill.required_exp_for_level(self.level)


def ensure_user_skills(user):
    existing_ids = set(
        UserSkill.objects.filter(user=user).values_list("skill_id", flat=True)
    )
    skills = Skill.objects.exclude(id__in=existing_ids)

    UserSkill.objects.bulk_create([UserSkill(user=user, skill=skill) for skill in skills])

    return (
        UserSkill.objects.select_related("skill")
        .filter(user=user)
        .order_by("skill__id")
    )


# =========================
# Типы зданий
# =========================
class BuildingType(models.Model):
    # Типы зданий
    TYPE_FIELD = "field"  # Поле - посев и рост урожая
    TYPE_AGROPRODUCTION = "agroproduction"  # Сельхозпроизводство
    TYPE_EXTRACTION = "extraction"  # Добыча ресурсов
    TYPE_PROCESSING = "processing"  # Переработка
    TYPE_PRODUCTION = "production"  # Производство
    TYPE_STORAGE = "storage"  # Хранилище (Склад, Сарай)
    TYPE_SHOP = "shop"  # Магазин — покупка товаров
    TYPE_MARKET = "market"  # Рынок — продажа товаров

    TYPE_CHOICES = [
        (TYPE_FIELD, "Поле"),
        (TYPE_AGROPRODUCTION, "Сельхозпроизводство"),
        (TYPE_EXTRACTION, "Добыча ресурсов"),
        (TYPE_PROCESSING, "Переработка"),
        (TYPE_PRODUCTION, "Производство"),
        (TYPE_STORAGE, "Хранилище"),
        (TYPE_SHOP, "Магазин"),
        (TYPE_MARKET, "Рынок"),
    ]
    # Служебные здания: даются на старте, одно на игрока, не строятся, не продаются, без уровней
    SERVICE_TYPES = (TYPE_SHOP, TYPE_MARKET)

    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    building_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_FIELD)

    width = models.PositiveIntegerField()   # cols
    height = models.PositiveIntegerField()  # rows

    price = models.PositiveIntegerField()

    # Уровни. Цена улучшения с уровня L на L+1 = price × upgrade_price_growth^(L-1)
    max_level = models.PositiveIntegerField(default=10)
    upgrade_price_growth = models.FloatField(default=1.6)
    upgrade_seconds = models.PositiveIntegerField(
        default=0, help_text="Время улучшения на один уровень, сек. 0 — мгновенно"
    )

    # Хранилища (Склад, Сарай): вместимость = capacity × (1 + capacity_bonus_per_level × (L-1))
    storage = models.CharField(
        max_length=20, choices=ShopItem.STORAGE_CHOICES, blank=True,
        help_text="Для хранилищ: какие товары хранит",
    )
    capacity = models.PositiveIntegerField(default=0, help_text="Вместимость на 1 уровне")
    capacity_bonus_per_level = models.FloatField(default=0.5)

    # Бонусы уровня: выход продукции ×(1 + yield × (L-1)), время −speed × (L-1)
    yield_bonus_per_level = models.FloatField(default=0.0)
    speed_bonus_per_level = models.FloatField(default=0.0)

    # Картинки лежат на фронте: src/assets/buildings/<slug>.svg — тут ничего не храним.

    class Meta:
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["building_type"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.width}x{self.height})"

    @property
    def is_service(self) -> bool:
        return self.building_type in self.SERVICE_TYPES

    def upgrade_price(self, level: int) -> int:
        """Цена улучшения с уровня level на level+1."""
        return round(self.price * self.upgrade_price_growth ** (level - 1))

    def capacity_at(self, level: int) -> int:
        return round(self.capacity * (1 + self.capacity_bonus_per_level * (level - 1)))

    def yield_factor(self, level: int) -> float:
        return 1 + self.yield_bonus_per_level * (level - 1)

    def speed_reduction(self, level: int) -> float:
        """Доля сокращения времени от уровня (складывается с бонусом навыка)."""
        return self.speed_bonus_per_level * (level - 1)


class FieldChunk(models.Model):
    """
    Купленный участок поля 10x10.
    chunk_row/chunk_col — координаты чанка (не клетки!).
    Клетки внутри чанка: row in [chunk_row*10 .. chunk_row*10+9]
    """
    profile = models.ForeignKey(PlayerProfile, on_delete=models.CASCADE, related_name="field_chunks")
    chunk_row = models.PositiveIntegerField()
    chunk_col = models.PositiveIntegerField()
    size = models.PositiveIntegerField(default=CHUNK_SIZE)

    # 0 = бесплатный стартовый чанк, >0 = реально купленный
    price_paid = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("profile", "chunk_row", "chunk_col")
        indexes = [
            models.Index(fields=["profile", "chunk_row", "chunk_col"]),
            models.Index(fields=["profile", "price_paid"]),
        ]

    def __str__(self):
        return f"Chunk({self.profile_id}:{self.chunk_row},{self.chunk_col})"


class BuildingPlacement(models.Model):
    """
    Размещённое здание в координатах клеток (row/col).
    Это отдельная сущность, не Cell (так проще для 1000x1000).
    """
    profile = models.ForeignKey(PlayerProfile, on_delete=models.CASCADE, related_name="building_placements")
    building_type = models.ForeignKey(BuildingType, on_delete=models.CASCADE, related_name="placements")

    row = models.PositiveIntegerField()
    col = models.PositiveIntegerField()

    width = models.PositiveIntegerField()   # snapshot
    height = models.PositiveIntegerField()  # snapshot
    price_paid = models.PositiveIntegerField(default=0)

    level = models.PositiveIntegerField(default=1)
    # Заготовка под улучшение по времени: пока улучшение мгновенное и поле всегда пустое
    upgrade_finishes_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["profile", "row", "col"]),
            models.Index(fields=["profile", "building_type"]),
        ]

    def __str__(self):
        return f"Placement({self.profile_id}:{self.building_type.slug}@{self.row},{self.col})"


class PlayerBuildingAppearance(models.Model):
    """
    Внешний вид типа здания, выбранный игроком. Действует на все его здания этого типа,
    включая будущие. Нет записи — стандартный вид. Картинку по параметрам рисует фронтенд
    (src/features/farm/buildingArt): {"v": 2, "shape": зерно формы (0 — исходная), "details": зерно деталей,
    "colors": {"wall", "roof", "window"} | null} — см. services/appearance.py.
    """
    profile = models.ForeignKey(PlayerProfile, on_delete=models.CASCADE, related_name="building_appearances")
    building_type = models.ForeignKey(BuildingType, on_delete=models.CASCADE, related_name="appearances")
    appearance = models.JSONField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Внешний вид здания игрока"
        verbose_name_plural = "Внешний вид зданий игроков"
        unique_together = ("profile", "building_type")

    def __str__(self):
        return f"Appearance({self.profile_id}:{self.building_type.slug})"


class FarmPlot(models.Model):
    """
    Посаженная культура на фермерском поле.
    Связано с BuildingPlacement (полем 2x2), но посадка идёт на конкретную клетку внутри.
    """
    profile = models.ForeignKey(PlayerProfile, on_delete=models.CASCADE, related_name="farm_plots")
    building = models.ForeignKey(BuildingPlacement, on_delete=models.CASCADE, related_name="plots")

    # Позиция внутри здания (0..width-1, 0..height-1)
    cell_row = models.PositiveIntegerField()  # относительно building.row
    cell_col = models.PositiveIntegerField()  # относительно building.col

    seed = models.ForeignKey(ShopItem, on_delete=models.CASCADE, limit_choices_to={"is_seed": True})
    planted_at = models.DateTimeField(auto_now_add=True)

    # Ожидаемая дата готовности
    ready_at = models.DateTimeField(null=True, blank=True)

    # Статус: growing, ready, harvested
    status = models.CharField(
        max_length=20,
        choices=[
            ("growing", "Растёт"),
            ("ready", "Готов к сбору"),
            ("harvested", "Собран"),
        ],
        default="growing",
    )

    class Meta:
        unique_together = ("profile", "building", "cell_row", "cell_col")
        indexes = [
            models.Index(fields=["profile", "status"]),
            models.Index(fields=["building", "cell_row", "cell_col"]),
        ]

    def __str__(self):
        return f"FarmPlot({self.profile_id}:{self.seed.name}@{self.building_id}:{self.cell_row},{self.cell_col})"


# =========================
# Рецепты
# =========================
class Recipe(models.Model):
    """Рецепты для зданий (добыча, переработка, производство)"""
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

    # Группа рецепта (тип здания для которого применим)
    recipe_group = models.CharField(
        max_length=20,
        choices=RECIPE_GROUP_CHOICES,
        default=RECIPE_GROUP_PRODUCTION,
    )

    # Связь с типом здания (для переработки и производства)
    building_type = models.ForeignKey(
        "BuildingType",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="recipes",
    )

    price = models.PositiveIntegerField(default=0)  # Цена запуска рецепта
    duration_seconds = models.PositiveIntegerField(default=60)  # Время выполнения в секундах

    # Результат
    output_item = models.ForeignKey(
        ShopItem,
        on_delete=models.CASCADE,
        related_name="recipes_as_output",
        help_text="Готовый продукт",
    )
    output_quantity = models.PositiveIntegerField(default=1)

    # Навык для опыта
    skill = models.ForeignKey(
        Skill,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recipes",
    )
    skill_exp = models.PositiveIntegerField(default=0, help_text="Опыт навыка за один цикл")

    class Meta:
        verbose_name = "Рецепт"
        verbose_name_plural = "Рецепты"
        indexes = [
            models.Index(fields=["recipe_group"]),
            models.Index(fields=["slug"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.recipe_group})"


class RecipeIngredient(models.Model):
    """Ингредиенты для рецепта"""
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="ingredients")
    item = models.ForeignKey(ShopItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("recipe", "item")

    def __str__(self):
        return f"{self.item.name} x{self.quantity} для {self.recipe.name}"


# =========================
# Выполненные рецепты (процессы)
# =========================
class RecipeProcess(models.Model):
    """Выполняемый рецепт - процесс в здании"""
    profile = models.ForeignKey(PlayerProfile, on_delete=models.CASCADE, related_name="recipe_processes")
    building = models.ForeignKey(BuildingPlacement, on_delete=models.CASCADE, related_name="recipe_processes")
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)

    started_at = models.DateTimeField(auto_now_add=True)
    ready_at = models.DateTimeField(null=True, blank=True)

    # Количество запусков и выполнено
    quantity = models.PositiveIntegerField(default=1)  # Сколько всего запусков
    quantity_done = models.PositiveIntegerField(default=0)  # Сколько уже выполнено

    # Статус: running, ready, completed
    status = models.CharField(
        max_length=20,
        choices=[
            ("running", "Выполняется"),
            ("ready", "Готов"),
            ("completed", "Завершён"),
        ],
        default="running",
    )

    class Meta:
        indexes = [
            models.Index(fields=["profile", "status"]),
            models.Index(fields=["building", "status"]),
        ]

    def __str__(self):
        return f"Process({self.recipe.name}@{self.building_id}:{self.status})"


# =========================
# Ресурсы добычи (для зданий типа extraction)
# =========================
class ExtractionResource(models.Model):
    """Ресурсы для зданий добычи"""
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

    # Связанное здание (BuildingType)
    building_type = models.ForeignKey(
        BuildingType,
        on_delete=models.CASCADE,
        limit_choices_to={"building_type": "extraction"},
        related_name="extraction_resources",
    )

    # Результат добычи
    output_item = models.ForeignKey(
        ShopItem,
        on_delete=models.CASCADE,
        related_name="extraction_sources",
    )

    duration_seconds = models.PositiveIntegerField(default=60)  # Время одного цикла добычи
    output_quantity = models.PositiveIntegerField(default=1)  # Количество за цикл

    class Meta:
        verbose_name = "Ресурс добычи"
        verbose_name_plural = "Ресурсы добычи"
        indexes = [
            models.Index(fields=["building_type"]),
        ]

    def __str__(self):
        return f"{self.name} -> {self.output_item.name} ({self.duration_seconds}сек)"


# =========================
# Процессы добычи
# =========================
class ExtractionProcess(models.Model):
    """Процесс добычи в здании"""
    profile = models.ForeignKey(PlayerProfile, on_delete=models.CASCADE, related_name="extraction_processes")
    building = models.ForeignKey(BuildingPlacement, on_delete=models.CASCADE, related_name="extraction_processes")
    resource = models.ForeignKey(ExtractionResource, on_delete=models.CASCADE)

    started_at = models.DateTimeField(auto_now_add=True)
    next_harvest_at = models.DateTimeField(null=True, blank=True)

    # Статус: running, paused
    status = models.CharField(
        max_length=20,
        choices=[
            ("running", "Работает"),
            ("paused", "Приостановлен"),
        ],
        default="running",
    )

    class Meta:
        indexes = [
            models.Index(fields=["profile", "status"]),
            models.Index(fields=["building", "status"]),
        ]

    def __str__(self):
        return f"Extraction({self.resource.name}@{self.building_id}:{self.status})"
