import pytest
from django.contrib.auth.models import User
from django.db import IntegrityError

from game.models import CHUNK_SIZE, START_UNLOCKED_SIZE, STARTING_COINS, FieldChunk, Skill, UserSkill


@pytest.mark.django_db
class TestNewPlayer:
    def test_profile_created_on_signup(self, game_data):
        user = User.objects.create_user(username="new", password="x")
        assert user.profile.coins_balance == STARTING_COINS
        assert user.profile.level == 1
        side = START_UNLOCKED_SIZE // CHUNK_SIZE
        assert FieldChunk.objects.filter(profile=user.profile, price_paid=0).count() == side * side
        assert UserSkill.objects.filter(user=user).count() == Skill.objects.count()


@pytest.mark.django_db
class TestExperience:
    def test_add_exp_without_level_up(self, user):
        p = user.profile
        p.add_exp(10)
        assert (p.level, p.exp) == (1, 10)

    def test_level_up(self, user):
        p = user.profile
        p.add_exp(p.exp_to_next)
        assert p.level == 2 and p.exp == 0

    def test_required_exp_grows(self, user):
        p = user.profile
        assert p.required_exp_for_level(2) > p.required_exp_for_level(1)

    def test_skill_capped_at_max_level(self, user):
        skill = Skill.objects.create(code="t", name="T", max_level=3, base_exp=10, effect_name="e")
        us = UserSkill.objects.create(user=user, skill=skill)
        for _ in range(50):
            us.add_exp(1000)
        assert us.level == 3 and us.exp_to_next == 0

    def test_skill_code_unique(self, db):
        Skill.objects.create(code="dup", name="A", effect_name="e")
        with pytest.raises(IntegrityError):
            Skill.objects.create(code="dup", name="B", effect_name="e")
