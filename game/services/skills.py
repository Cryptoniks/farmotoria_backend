"""Навыки: уровень, опыт и бонус к скорости."""
from game.models import Skill, UserSkill

# Насколько уровень навыка сокращает время (за уровень) и максимальное сокращение
FARMING_REDUCTION_PER_LEVEL = 0.01   # Земледелие: -1% за уровень
FARMING_MIN_FACTOR = 0.1             # не быстрее 10% от базового времени
WORK_REDUCTION_PER_LEVEL = 0.02      # Добыча/переработка/производство: -2% за уровень
WORK_MIN_FACTOR = 0.8                # не быстрее 80% от базового времени


def get_user_skill(user, code: str, create: bool = False) -> UserSkill | None:
    try:
        skill = Skill.objects.get(code=code)
    except Skill.DoesNotExist:
        return None
    if create:
        user_skill, _ = UserSkill.objects.get_or_create(user=user, skill=skill)
        return user_skill
    return UserSkill.objects.select_related("skill").filter(user=user, skill=skill).first()


def skill_level(user, code: str) -> int:
    user_skill = get_user_skill(user, code)
    return user_skill.level if user_skill else 0


def add_skill_exp(user, code: str, amount: int) -> int:
    """Начисляет опыт навыку и возвращает его новый уровень (0, если навыка нет)."""
    if amount <= 0:
        return skill_level(user, code)
    user_skill = get_user_skill(user, code, create=True)
    if not user_skill:
        return 0
    user_skill.add_exp(amount)
    return user_skill.level


TOTAL_MIN_FACTOR = 0.2               # навык + уровень здания вместе: не быстрее 20% от базового


def reduced_duration(base_seconds: int, level: int, per_level: float, min_factor: float,
                     building_reduction: float = 0.0) -> int:
    """Сокращение от навыка (со своим потолком) складывается с сокращением от уровня здания."""
    skill_cut = min(level * per_level, 1.0 - min_factor)
    factor = max(TOTAL_MIN_FACTOR, 1.0 - skill_cut - building_reduction)
    return max(1, int(base_seconds * factor))


def work_duration(base_seconds: int, level: int, building_reduction: float = 0.0) -> int:
    return reduced_duration(base_seconds, level, WORK_REDUCTION_PER_LEVEL, WORK_MIN_FACTOR, building_reduction)


def farming_duration(base_seconds: int, level: int, building_reduction: float = 0.0) -> int:
    return reduced_duration(base_seconds, level, FARMING_REDUCTION_PER_LEVEL, FARMING_MIN_FACTOR, building_reduction)
