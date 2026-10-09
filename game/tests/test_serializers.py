"""Tests for REST API serializers."""

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIRequestFactory
from game.serializers.auth import RegisterSerializer, PlayerProfileSerializer
from game.models import ShopItem, ItemCategory


@pytest.mark.django_db
class TestRegisterSerializer:
    """Tests for RegisterSerializer."""

    def test_valid_registration(self):
        """Test valid registration data."""
        data = {
            'username': 'newuser',
            'password': 'securepass123',
            'email': 'newuser@test.com',
        }

        serializer = RegisterSerializer(data=data)
        assert serializer.is_valid() is True
        serializer.save()

        user = User.objects.get(username='newuser')
        assert user.email == 'newuser@test.com'
        assert user.check_password('securepass123')

    def test_invalid_password_short(self):
        """Test that short password is rejected."""
        data = {
            'username': 'newuser',
            'password': 'short',
            'email': 'newuser@test.com',
        }

        serializer = RegisterSerializer(data=data)
        assert serializer.is_valid() is False
        assert 'password' in serializer.errors

    def test_duplicate_username(self):
        """Test that duplicate username is rejected."""
        User.objects.create_user(username='existing', password='pass123')

        data = {
            'username': 'existing',
            'password': 'securepass123',
            'email': 'other@test.com',
        }

        serializer = RegisterSerializer(data=data)
        assert serializer.is_valid() is False
        assert 'username' in serializer.errors


@pytest.mark.django_db
class TestPlayerProfileSerializer:
    """Tests for PlayerProfileSerializer."""

    def test_serialize_profile(self):
        """Test profile serialization."""
        user = User.objects.create_user(username='testuser', password='pass123')
        profile = PlayerProfileSerializer(user.profile).data

        assert 'username' in profile
        assert 'coins_balance' in profile
        assert 'level' in profile
        assert 'exp' in profile
        assert profile['username'] == 'testuser'

    def test_profile_with_skills(self):
        """Test profile serialization with skills."""
        from game.models import Skill, UserSkill

        user = User.objects.create_user(username='testuser', password='pass123')
        skill = Skill.objects.create(
            code='farming',
            name='Земледелие',
            max_level=10,
        )
        UserSkill.objects.create(user=user, skill=skill, level=3, exp=100)

        data = PlayerProfileSerializer(user.profile).data
        assert 'skills' in data


@pytest.mark.django_db
class TestShopSerializers:
    """Tests for shop-related serializers."""

    def test_shop_item_serialization(self):
        """Test shop item serialization."""
        category = ItemCategory.objects.create(name="Test", slug="test")
        item = ShopItem.objects.create(
            slug='test-item',
            name='Test Item',
            category=category,
            price_coins=100,
            sell_price=50,
        )

        from game.serializers.shop import ShopItemSerializer

        data = ShopItemSerializer(item).data
        assert data['slug'] == 'test-item'
        assert data['name'] == 'Test Item'
        assert data['price_coins'] == 100
