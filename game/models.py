from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

User = settings.AUTH_USER_MODEL

# =========================
# Константы (перед моделями)
# =========================
CHUNK_SIZE = 10           # Размер чанка для покупки (10x10 клеток)
START_UNLOCKED_SIZE = 50  # Стартовое поле 50x50 клеток
MAX_FIELD_SIZE = 250      # Максимальное поле 250x250 клеток
STARTING_COINS = 500      # Стартовый баланс для нового игрока

# Опыт за сбор урожая
PLAYER_EXP_PER_HARVEST = 10   # Опыт профилю за сбор
SKILL_EXP_PER_HARVEST = 20    # Опыт навыку за сбор

# Группы рецептов (по типам зданий)
RECIPE_GROUP_FIELD = "field"           # Поле
RECIPE_GROUP_PROCESSING = "processing" # Переработка
RECIPE_GROUP_PRODUCTION = "production" # Производство

RECIPE_GROUP_CHOICES = [
    (RECIPE_GROUP_FIELD, "Поле"),
    (RECIPE_GROUP_PROCESSING, "Переработка"),
    (RECIPE_GROUP_PRODUCTION, "Производство"),
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
# Поле фермы
# =========================
class FarmField(models.Model):
    profile = models.OneToOneField(
        PlayerProfile,
        on_delete=models.CASCADE,
        related_name="farm_field",
    )
    level = models.PositiveIntegerField(
        default=1,
        help_text="Уровень поля (размер = level * 5)",
    )
    max_cells = models.PositiveIntegerField(
        default=25,
        help_text="Макс. клеток = level^2 * 25",
    )
    expansion_cost_coins = models.PositiveIntegerField(
        default=1000,
        help_text="Стоимость следующего расширения",
    )

    class Meta:
        verbose_name = "Поле фермы"

    def save(self, *args, **kwargs):
        # автоподдержка вычисляемых полей
        self.max_cells = self.level * self.level * 25
        self.expansion_cost_coins = int(1000 * (self.level ** 2))
        super().save(*args, **kwargs)


# =========================
# Клетка на поле
# =========================
class Cell(models.Model):
    OBJECT_FIELD = "field"
    OBJECT_BUILDING = "building"

    profile = models.ForeignKey(PlayerProfile, on_delete=models.CASCADE)
    position = models.PositiveIntegerField(
        help_text="Позиция: row * grid_size + col"
    )

    object_type = models.CharField(
        max_length=20,
        choices=[
            (OBJECT_FIELD, "Поле"),
            (OBJECT_BUILDING, "Здание"),
        ],
        default=OBJECT_FIELD,
    )

    object_data = models.JSONField(default=dict, blank=True)

    # --- multi-cell объекты (в первую очередь здания) ---
    # is_anchor=True только у "главной" клетки; остальные клетки здания — is_anchor=False
    is_anchor = models.BooleanField(default=True)

    # position якоря (левый верх). Для якорной клетки = position.
    anchor_position = models.PositiveIntegerField(null=True, blank=True)

    # размеры прямоугольника, занимаемого объектом (в клетках)
    size_w = models.PositiveIntegerField(null=True, blank=True)  # cols
    size_h = models.PositiveIntegerField(null=True, blank=True)  # rows
    # -----------------------------------------------

    # для посевов
    planted_at = models.DateTimeField(null=True, blank=True)
    grow_duration_seconds = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        unique_together = ("profile", "position")
        indexes = [
            models.Index(fields=["profile", "position"]),
            models.Index(fields=["profile", "anchor_position"]),
            models.Index(fields=["profile", "is_anchor"]),
        ]

    def __str__(self):
        return f"Cell(profile={self.profile_id}, pos={self.position}, type={self.object_type})"

    def clean(self):
        # Нормализация multi-cell метаданных
        if self.object_type == self.OBJECT_BUILDING:
            # для зданий размеры должны быть заданы (обычно на создание)
            if (self.size_w is None) or (self.size_h is None):
                # допускаем пусто только если это "старые" записи; лучше явно валидировать на API
                return

            if self.size_w < 1 or self.size_h < 1:
                raise ValidationError("size_w/size_h должны быть >= 1")

        # anchor_position: если якорь и пусто — приравниваем к position
        if self.is_anchor and self.anchor_position in (None, ""):
            self.anchor_position = self.position

    def save(self, *args, **kwargs):
        # ensure clean() logic applied even if full_clean() не вызывают в коде
        self.clean()
        super().save(*args, **kwargs)

    @property
    def is_ready_for_harvest(self):
        if (
            self.object_type != self.OBJECT_FIELD
            or not self.planted_at
            or not self.grow_duration_seconds
        ):
            return False
        shop_item_id = self.object_data.get("shop_item_id")
        if not shop_item_id:
            return False
        return timezone.now() >= (
            self.planted_at + timezone.timedelta(seconds=self.grow_duration_seconds)
        )

    @property
    def ready_at(self):
        if not self.planted_at or not self.grow_duration_seconds:
            return None
        return self.planted_at + timezone.timedelta(seconds=self.grow_duration_seconds)


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
# Заблокированные области
# =========================
class AreaLock(models.Model):
    profile = models.ForeignKey(PlayerProfile, on_delete=models.CASCADE)

    row_start = models.IntegerField()
    col_start = models.IntegerField()
    rows = models.IntegerField(help_text="Высота зоны в клетках")
    cols = models.IntegerField(help_text="Ширина зоны в клетках")

    is_unlocked = models.BooleanField(default=False)
    unlock_cost = models.PositiveIntegerField(default=1000)

    # опционально: если лок привязан к определённому зданию/условию
    building_type = models.CharField(max_length=50, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["profile", "is_unlocked"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["profile", "row_start", "col_start", "rows", "cols"],
                name="uniq_lock_rect_per_profile",
            )
        ]

    def __str__(self):
        return f"AreaLock(profile={self.profile_id}, r={self.row_start}, c={self.col_start}, {self.rows}x{self.cols}, unlocked={self.is_unlocked})"


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

    TYPE_CHOICES = [
        (TYPE_FIELD, "Поле"),
        (TYPE_AGROPRODUCTION, "Сельхозпроизводство"),
        (TYPE_EXTRACTION, "Добыча ресурсов"),
        (TYPE_PROCESSING, "Переработка"),
        (TYPE_PRODUCTION, "Производство"),
    ]

    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    building_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_FIELD)

    width = models.PositiveIntegerField()   # cols
    height = models.PositiveIntegerField()  # rows

    price = models.PositiveIntegerField()

    # Картинки лежат на фронте: src/assets/buildings/<slug>.png (или .webp)
    # поэтому тут ничего не храним.

    class Meta:
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["building_type"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.width}x{self.height})"


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

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["profile", "row", "col"]),
            models.Index(fields=["profile", "building_type"]),
        ]

    def __str__(self):
        return f"Placement({self.profile_id}:{self.building_type.slug}@{self.row},{self.col})"


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