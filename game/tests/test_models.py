"""Tests for PlayerProfile, Skill, and UserSkill models."""

import pytest
from django.contrib.auth.models import User
from django.db import IntegrityError
from game.models import PlayerProfile, Skill, UserSkill


@pytest.mark.django_db
class TestPlayerProfile:
    """Tests for PlayerProfile model."""

    def test_create_profile(self):
        """Test that profile is created with user."""
        user = User.objects.create_user(username='testuser', password='testpass')
        profile = PlayerProfile.objects.get(user=user)

        assert profile.user == user
        assert profile.coins_balance == 1000
        assert profile.level == 1
        assert profile.exp == 0

    def test_add_exp(self):
        """Test experience addition."""
        user = User.objects.create_user(username='testuser', password='testpass')
        profile = PlayerProfile.objects.get(user=user)

        profile.add_exp(100)
        assert profile.exp == 100
        assert profile.level == 1  # Not enough for level up

    def test_level_up(self):
        """Test level up when enough exp."""
        user = User.objects.create_user(username='testuser', password='testpass')
        profile = PlayerProfile.objects.get(user=user)

        # Add enough exp to reach level 2
        profile.add_exp(profile.required_exp_for_level(2))
        assert profile.level >= 2

    def test_exp_to_next(self):
        """Test exp_to_next property."""
        user = User.objects.create_user(username='testuser', password='testpass')
        profile = PlayerProfile.objects.get(user=user)

        exp_to_next = profile.exp_to_next
        assert exp_to_next > 0

        profile.add_exp(exp_to_next)
        assert profile.level > 1

    def test_required_exp_for_level(self):
        """Test required exp calculation."""
        user = User.objects.create_user(username='testuser', password='testpass')
        profile = PlayerProfile.objects.get(user=user)

        exp_l1 = profile.required_exp_for_level(1)
        exp_l2 = profile.required_exp_for_level(2)

        assert exp_l2 > exp_l1


@pytest.mark.django_db
class TestSkill:
    """Tests for Skill model."""

    def test_create_skill(self):
        """Test skill creation."""
        skill = Skill.objects.create(
            code='testing',
            name='Тестирование',
            max_level=5,
            base_exp=100,
            exp_growth=1.5,
            effect_name='Test Effect',
            effect_description='A test effect',
            effect_value_per_level=0.1,
        )

        assert skill.code == 'testing'
        assert skill.max_level == 5
        assert skill.base_exp == 100

    def test_unique_code(self):
        """Test that skill code must be unique."""
        Skill.objects.create(code='unique_test', name='Test')

        with pytest.raises(IntegrityError):
            Skill.objects.create(code='unique_test', name='Test 2')


@pytest.mark.django_db
class TestUserSkill:
    """Tests for UserSkill model."""

    def test_create_user_skill(self):
        """Test user skill creation."""
        user = User.objects.create_user(username='testuser', password='testpass')
        skill = Skill.objects.create(
            code='farming',
            name='Земледелие',
            max_level=10,
        )

        user_skill = UserSkill.objects.create(
            user=user,
            skill=skill,
            level=1,
            exp=0,
        )

        assert user_skill.user == user
        assert user_skill.skill == skill
        assert user_skill.level == 1

    def test_add_exp_to_user_skill(self):
        """Test adding exp to user skill."""
        user = User.objects.create_user(username='testuser', password='testpass')
        skill = Skill.objects.create(
            code='farming',
            name='Земледелие',
            max_level=10,
            base_exp=50,
        )

        user_skill = UserSkill.objects.create(
            user=user,
            skill=skill,
            level=1,
            exp=0,
        )

        user_skill.add_exp(50)
        assert user_skill.exp == 50

    def test_user_skill_max_level(self):
        """Test that skill cannot exceed max level."""
        user = User.objects.create_user(username='testuser', password='testpass')
        skill = Skill.objects.create(
            code='farming',
            name='Земледелие',
            max_level=3,
            base_exp=50,
        )

        user_skill = UserSkill.objects.create(
            user=user,
            skill=skill,
            level=1,
            exp=0,
        )

        # Add enough exp to max out
        for _ in range(100):
            user_skill.add_exp(100)

        assert user_skill.level <= skill.max_level
