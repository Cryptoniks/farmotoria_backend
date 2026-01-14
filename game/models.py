from django.conf import settings
from django.db import models
from django.utils import timezone

User = settings.AUTH_USER_MODEL

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

    class Meta:
        verbose_name = "Профиль игрока"

    def __str__(self):
        return f"Profile({self.user})"

class ItemCategory(models.Model):
    name = models.CharField(max_length=50, unique=True)  # например: 'Seed', 'Resource', 'Harvest', 'ShopProduct'

    def __str__(self):
        return self.name
    
class ShopItem(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    slug = models.SlugField(max_length=100, unique=True)  # для ссылки на иконку
    price_coins = models.PositiveIntegerField(default=0)
    category = models.ForeignKey(ItemCategory, on_delete=models.CASCADE)
    
    # Тип товара
    is_seed = models.BooleanField(default=False)
    is_harvest = models.BooleanField(default=False)

    # Только для семян
    grow_time_minutes = models.PositiveIntegerField(null=True, blank=True)
    # Только для урожая
    harvest_yield = models.PositiveIntegerField(null=True, blank=True)

    # Явная связь семя → урожай
    harvest_item = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='seed_item',
        limit_choices_to={'is_harvest': True},
        help_text="Если это семя, то сюда ставим связанный урожай"
    )

    def __str__(self):
        type_flags = []
        if self.is_seed:
            type_flags.append("Seed")
        if self.is_harvest:
            type_flags.append("Harvest")
        return f"{self.name} ({', '.join(type_flags)})"
    
# ===== Опыт и уровни =====

def exp_for_level(level: int) -> int:
    """
    Общее количество опыта, необходимое для достижения level.
    Формула: 50 * level * (level - 1) / 2
    """
    return 50 * level * (level - 1) // 2


def recalc_level(profile: PlayerProfile) -> None:
    total_exp = profile.exp
    level = 1

    while total_exp >= exp_for_level(level + 1):
        level += 1

    profile.level = level


def add_exp(profile: PlayerProfile, amount: int) -> None:
    if amount <= 0:
        return

    profile.exp += amount
    recalc_level(profile)
    profile.save(update_fields=["exp", "level"])


# =========================
# Растения и ферма
# =========================

class Cell(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    row = models.PositiveIntegerField()
    col = models.PositiveIntegerField()
    shop_item = models.ForeignKey(
        ShopItem,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Что посажено в этой ячейке",
    )
    planted_at = models.DateTimeField(null=True, blank=True)
    grow_duration_seconds = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Фактическое время роста с учетом навыков",
    )

    class Meta:
        unique_together = ("owner", "row", "col")
        indexes = [models.Index(fields=["owner"])]

    @property
    def is_growing(self) -> bool:
        return self.shop_item_id is not None and self.planted_at is not None and self.shop_item.is_seed

    @property
    def ready_at(self):
        if not self.is_growing or not self.grow_duration_seconds:
            return None
        return self.planted_at + timezone.timedelta(seconds=self.grow_duration_seconds)

    @property
    def is_ready_for_harvest(self) -> bool:
        return self.is_growing and self.ready_at and timezone.now() >= self.ready_at

    @property
    def harvest_item(self):
        """
        Возвращает ShopItem урожая, если клетка готова
        """
        if self.is_ready_for_harvest:
            return self.shop_item.harvest_item
        return None

# =========================
# Инвентарь
# =========================

class InventoryItem(models.Model):
    item = models.ForeignKey(ShopItem, on_delete=models.CASCADE, null=True)
    player = models.ForeignKey(PlayerProfile, on_delete=models.CASCADE, null=True)
    quantity = models.PositiveIntegerField(default=0)

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
    """
    Создаёт недостающие навыки для пользователя
    """
    existing_ids = set(
        UserSkill.objects.filter(user=user)
        .values_list("skill_id", flat=True)
    )

    skills = Skill.objects.exclude(id__in=existing_ids)

    UserSkill.objects.bulk_create(
        [UserSkill(user=user, skill=skill) for skill in skills]
    )

    return (
        UserSkill.objects
        .select_related("skill")
        .filter(user=user)
        .order_by("skill__id")
    )