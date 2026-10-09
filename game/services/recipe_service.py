"""
Recipe service - handles recipe operations.
Manages recipe execution, ingredients, and outputs.
"""

from django.db import transaction
from django.utils import timezone
from game.models import (
    Recipe,
    RecipeIngredient,
    ShopItem,
    InventoryItem,
    BuildingPlacement,
)
import logging

logger = logging.getLogger(__name__)


class RecipeServiceError(Exception):
    """Base exception for recipe service errors."""
    pass


class RecipeService:
    """Service for managing recipes and processing."""

    @staticmethod
    def get_recipes_for_building(building_type_slug: str) -> list:
        """Get all recipes available for a building type."""
        recipes = Recipe.objects.filter(
            building_type__slug=building_type_slug
        ).select_related('output_item').prefetch_related('ingredients__item')

        result = []
        for recipe in recipes:
            ingredients = []
            for ing in recipe.ingredients.all():
                ingredients.append({
                    'item_id': ing.item.id,
                    'item_name': ing.item.name,
                    'item_slug': ing.item.slug,
                    'quantity': ing.quantity,
                })

            result.append({
                'id': recipe.id,
                'name': recipe.name,
                'slug': recipe.slug,
                'duration_seconds': recipe.duration_seconds,
                'output_item': {
                    'id': recipe.output_item.id,
                    'name': recipe.output_item.name,
                    'slug': recipe.output_item.slug,
                },
                'output_quantity': recipe.output_quantity,
                'ingredients': ingredients,
            })

        return result

    @staticmethod
    def can_execute_recipe(profile, recipe: Recipe, quantity: int = 1) -> tuple[bool, str]:
        """Check if a recipe can be executed with current inventory."""
        ingredients = recipe.ingredients.all()

        for ing in ingredients:
            inventory_item = InventoryItem.objects.filter(
                player=profile,
                item=ing.item,
            ).first()

            if not inventory_item or inventory_item.quantity < ing.quantity * quantity:
                return False, f"Not enough {ing.item.name}"

        return True, ""

    @staticmethod
    @transaction.atomic
    def execute_recipe(profile, building_id: int, recipe_id: int, quantity: int = 1) -> dict:
        """Execute a recipe (consume ingredients, create processing job)."""
        recipe = Recipe.objects.filter(id=recipe_id).first()

        if not recipe:
            raise RecipeServiceError("Recipe not found")

        # Check if building matches recipe
        building = BuildingPlacement.objects.filter(
            id=building_id,
            profile=profile,
        ).select_related('building_type').first()

        if not building:
            raise RecipeServiceError("Building not found")

        if recipe.building_type and recipe.building_type != building.building_type:
            raise RecipeServiceError("Building type doesn't match recipe")

        # Check ingredients
        can_execute, error = RecipeService.can_execute_recipe(profile, recipe, quantity)
        if not can_execute:
            raise RecipeServiceError(error)

        # Consume ingredients
        for ing in recipe.ingredients.all():
            inventory_item = InventoryItem.objects.filter(
                player=profile,
                item=ing.item,
            ).first()

            if inventory_item:
                inventory_item.quantity -= ing.quantity * quantity
                if inventory_item.quantity <= 0:
                    inventory_item.delete()
                else:
                    inventory_item.save(update_fields=['quantity'])

        # Create processing job (simplified - in production use APScheduler)
        from game.models import ProcessingJob
        job = ProcessingJob.objects.create(
            building=building,
            recipe=recipe,
            status='processing',
            started_at=timezone.now(),
            completed_at=timezone.now() + timezone.timedelta(seconds=recipe.duration_seconds * quantity),
            quantity=quantity,
        )

        logger.info(f"User {profile.user.username} started recipe {recipe.name}")

        return {
            'success': True,
            'job_id': job.id,
            'completed_at': job.completed_at.isoformat(),
        }

    @staticmethod
    @transaction.atomic
    def collect_recipe_output(profile, job_id: int) -> dict:
        """Collect output from a completed processing job."""
        job = ProcessingJob.objects.filter(
            id=job_id,
            building__profile=profile,
            status='processing',
        ).select_related('recipe').first()

        if not job:
            raise RecipeServiceError("Processing job not found or not ready")

        if job.completed_at and job.completed_at > timezone.now():
            raise RecipeServiceError("Processing not complete")

        # Add output to inventory
        output_item = job.recipe.output_item
        output_quantity = job.recipe.output_quantity * job.quantity

        inventory_item, created = InventoryItem.objects.get_or_create(
            player=profile,
            item=output_item,
            defaults={'quantity': 0}
        )
        inventory_item.quantity += output_quantity
        inventory_item.save(update_fields=['quantity'])

        # Update job status
        job.status = 'completed'
        job.collected_at = timezone.now()
        job.save()

        logger.info(f"User {profile.user.username} collected {output_item.name}")

        return {
            'success': True,
            'item': output_item.name,
            'quantity': output_quantity,
        }
