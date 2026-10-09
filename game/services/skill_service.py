"""
Skill service - handles skill operations.
Manages skills, experience, and leveling.
"""

from django.db import transaction
from game.models import PlayerProfile, Skill, UserSkill
import logging

logger = logging.getLogger(__name__)


class SkillServiceError(Exception):
    """Base exception for skill service errors."""
    pass


class SkillService:
    """Service for managing skills."""

    @staticmethod
    def get_all_skills() -> list:
        """Get all available skills."""
        skills = Skill.objects.all()
        result = []

        for skill in skills:
            result.append({
                'id': skill.id,
                'code': skill.code,
                'name': skill.name,
                'max_level': skill.max_level,
                'base_exp': skill.base_exp,
                'exp_growth': skill.exp_growth,
                'effect_name': skill.effect_name,
                'effect_description': skill.effect_description,
            })

        return result

    @staticmethod
    def get_user_skills(user) -> list:
        """Get user's skills with current levels."""
        user_skills = UserSkill.objects.filter(user=user).select_related('skill')

        result = []
        for us in user_skills:
            result.append({
                'skill_code': us.skill.code,
                'skill_name': us.skill.name,
                'level': us.level,
                'exp': us.exp,
                'max_level': us.skill.max_level,
                'effect_value': us.skill.effect_value_per_level * us.level,
            })

        return result

    @staticmethod
    def get_or_create_user_skill(user, skill_code: str) -> UserSkill:
        """Get or create a user skill."""
        skill = Skill.objects.filter(code=skill_code).first()

        if not skill:
            raise SkillServiceError(f"Skill {skill_code} not found")

        user_skill, created = UserSkill.objects.get_or_create(
            user=user,
            skill=skill,
            defaults={'level': 1, 'exp': 0}
        )

        return user_skill

    @staticmethod
    @transaction.atomic
    def add_exp_to_skill(user, skill_code: str, exp_amount: int) -> dict:
        """Add experience to a user's skill."""
        user_skill = SkillService.get_or_create_user_skill(user, skill_code)

        initial_level = user_skill.level
        user_skill.add_exp(exp_amount)
        final_level = user_skill.level

        level_up = final_level > initial_level

        logger.info(
            f"User {user.username} added {exp_amount} exp to {skill_code} "
            f"(level {initial_level} -> {final_level})"
        )

        return {
            'success': True,
            'skill_code': skill_code,
            'exp_added': exp_amount,
            'level': final_level,
            'max_level': user_skill.skill.max_level,
            'level_up': level_up,
        }

    @staticmethod
    @transaction.atomic
    def add_exp_to_profile(user, exp_amount: int) -> dict:
        """Add experience to user's profile (global exp)."""
        profile = user.profile
        initial_level = profile.level

        profile.add_exp(exp_amount)
        final_level = profile.level

        level_up = final_level > initial_level

        logger.info(
            f"User {user.username} added {exp_amount} profile exp "
            f"(level {initial_level} -> {final_level})"
        )

        return {
            'success': True,
            'exp_added': exp_amount,
            'level': final_level,
            'exp_to_next': profile.exp_to_next,
            'level_up': level_up,
        }

    @staticmethod
    def get_skill_effect(skill_code: str, level: int) -> float:
        """Get the effect value for a skill at a given level."""
        skill = Skill.objects.filter(code=skill_code).first()

        if not skill:
            return 0

        return skill.effect_value_per_level * level
