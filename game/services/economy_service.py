"""
Economy service - handles currency and economy operations.
Manages player coins, transactions, and economic activities.
"""

from django.db import transaction
from game.models import PlayerProfile
from django.contrib.auth.models import User
import logging

logger = logging.getLogger(__name__)


class EconomyServiceError(Exception):
    """Base exception for economy service errors."""
    pass


class EconomyService:
    """Service for managing player economy."""

    @staticmethod
    def get_profile_economy(user_or_profile) -> dict:
        """Get economy info for a user or profile."""
        if isinstance(user_or_profile, User):
            profile = user_or_profile.profile
        else:
            profile = user_or_profile

        return {
            'username': profile.user.username,
            'coins_balance': profile.coins_balance,
            'level': profile.level,
            'exp': profile.exp,
            'exp_to_next': profile.exp_to_next,
        }

    @staticmethod
    @transaction.atomic
    def add_coins(profile: PlayerProfile, amount: int, reason: str = "") -> dict:
        """Add coins to player balance."""
        if amount <= 0:
            raise EconomyServiceError("Amount must be positive")

        profile.coins_balance += amount
        profile.save(update_fields=['coins_balance'])

        logger.info(f"Added {amount} coins to {profile.user.username} (reason: {reason})")

        return {
            'success': True,
            'added': amount,
            'reason': reason,
            'new_balance': profile.coins_balance,
        }

    @staticmethod
    @transaction.atomic
    def deduct_coins(profile: PlayerProfile, amount: int, reason: str = "") -> dict:
        """Deduct coins from player balance."""
        if amount <= 0:
            raise EconomyServiceError("Amount must be positive")

        if profile.coins_balance < amount:
            raise EconomyServiceError("Insufficient coins")

        profile.coins_balance -= amount
        profile.save(update_fields=['coins_balance'])

        logger.info(f"Deducted {amount} coins from {profile.user.username} (reason: {reason})")

        return {
            'success': True,
            'deducted': amount,
            'reason': reason,
            'new_balance': profile.coins_balance,
        }

    @staticmethod
    def get_transaction_history(profile: PlayerProfile, limit: int = 50) -> list:
        """Get player's transaction history."""
        # In production, use a Transaction model
        # For now, return simplified version
        return []
