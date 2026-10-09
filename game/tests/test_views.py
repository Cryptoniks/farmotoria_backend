"""Tests for REST API views/endpoints."""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth.models import User
from game.models import PlayerProfile, ShopItem, ItemCategory, InventoryItem


@pytest.mark.django_db
class TestAuthViews:
    """Tests for authentication views."""

    def setUp(self):
        self.client = APIClient()

    def test_ping(self):
        """Test ping endpoint."""
        response = self.client.get('/api/farmotoria/ping/')
        assert response.status_code == status.HTTP_200_OK

    def test_register(self):
        """Test user registration."""
        data = {
            'username': 'newuser',
            'password': 'securepass123',
            'email': 'newuser@test.com',
        }
        response = self.client.post('/api/auth/register/', data, format='json')
        assert response.status_code == status.HTTP_201_CREATED

        user = User.objects.get(username='newuser')
        assert user.check_password('securepass123')

    def test_register_invalid(self):
        """Test registration with invalid data."""
        data = {
            'username': '',
            'password': 'short',
        }
        response = self.client.post('/api/auth/register/', data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login(self):
        """Test JWT token obtain."""
        User.objects.create_user(username='testuser', password='pass123')

        data = {
            'username': 'testuser',
            'password': 'pass123',
        }
        response = self.client.post('/api/auth/token/', data, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert 'refresh' in response.data

    def test_me(self):
        """Test get current user profile."""
        user = User.objects.create_user(username='testuser', password='pass123')
        self.client.force_authenticate(user=user)

        response = self.client.get('/api/me/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['username'] == 'testuser'


@pytest.mark.django_db
class TestShopViews:
    """Tests for shop views."""

    def setUp(self):
        self.client = APIClient()
        self.category = ItemCategory.objects.create(name="Test", slug="test")
        self.item = ShopItem.objects.create(
            slug='test-item',
            name='Test Item',
            category=self.category,
            price_coins=100,
            sell_price=50,
        )

    def test_shop_item_list(self):
        """Test shop item list endpoint."""
        response = self.client.get('/api/shop/items/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

    def test_shop_by_category(self):
        """Test shop by category endpoint."""
        response = self.client.get('/api/shop/test/')
        assert response.status_code == status.HTTP_200_OK

    def test_buy_item(self):
        """Test buying an item."""
        user = User.objects.create_user(username='buyer', password='pass123')
        self.client.force_authenticate(user=user)

        data = {
            'item_slug': 'test-item',
            'quantity': 1,
        }
        response = self.client.post('/api/shop/buy/', data, format='json')
        assert response.status_code == status.HTTP_201_CREATED

        # Check inventory
        inv = InventoryItem.objects.filter(
            player=user.profile,
            item=self.item
        )
        assert inv.exists()
        assert inv.first().quantity == 1


@pytest.mark.django_db
class TestInventoryViews:
    """Tests for inventory views."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='invuser', password='pass123')
        self.client.force_authenticate(user=self.user)
        self.category = ItemCategory.objects.create(name="Test", slug="test")
        self.item = ShopItem.objects.create(
            slug='inv-item',
            name='Inventory Item',
            category=self.category,
            price_coins=50,
        )

    def test_inventory_list(self):
        """Test inventory list endpoint."""
        # Add item to inventory
        InventoryItem.objects.create(
            player=self.user.profile,
            item=self.item,
            quantity=5,
        )

        response = self.client.get('/api/inventory/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

    def test_sell_item(self):
        """Test selling an item."""
        # Add item to inventory
        inv_item = InventoryItem.objects.create(
            player=self.user.profile,
            item=self.item,
            quantity=5,
        )

        initial_coins = self.user.profile.coins_balance

        data = {
            'item_slug': 'inv-item',
            'quantity': 2,
        }
        response = self.client.post('/api/market/sell/', data, format='json')
        assert response.status_code == status.HTTP_200_OK

        # Refresh from DB
        self.user.profile.refresh_from_db()
        assert self.user.profile.coins_balance > initial_coins
