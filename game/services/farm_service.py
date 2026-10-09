"""
Farm service - handles farm field operations.
Manages chunks, buildings, plots, and field-related business logic.
"""

from django.db import transaction
from django.conf import settings
from game.models import (
    PlayerProfile,
    BuildingPlacement,
    BuildingType,
    FieldChunk,
    FarmPlot,
    Plant,
    InventoryItem,
    ShopItem,
)
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class FarmServiceError(Exception):
    """Base exception for farm service errors."""
    pass


class ChunkService:
    """Service for managing field chunks."""

    @staticmethod
    def get_available_chunks(profile: PlayerProfile):
        """Get chunks available for purchase."""
        from game.models import FieldChunk

        chunks = FieldChunk.objects.filter(profile=profile)
        all_chunk_positions = set()

        # Generate all chunk positions around existing chunks
        for chunk in chunks:
            for dr in [-1, 0, 1]:
                for dc in [-1, 0, 1]:
                    if dr == 0 and dc == 0:
                        continue
                    all_chunk_positions.add((chunk.chunk_row + dr, chunk.chunk_col + dc))

        # Filter out already unlocked chunks
        existing_chunks = set(
            chunks.values_list('chunk_row', 'chunk_col')
        )
        available = all_chunk_positions - existing_chunks

        result = []
        for row, col in available:
            cost = profile.required_exp_for_level(2) // 10  # Simplified cost calculation
            result.append({
                'chunk_row': row,
                'chunk_col': col,
                'cost': cost,
            })

        return result

    @staticmethod
    @transaction.atomic
    def buy_chunk(profile: PlayerProfile, chunk_row: int, chunk_col: int) -> dict:
        """Buy a new chunk."""
        # Check if chunk already exists
        existing = FieldChunk.objects.filter(
            profile=profile,
            chunk_row=chunk_row,
            chunk_col=chunk_col,
        ).first()

        if existing:
            raise FarmServiceError("Chunk already exists")

        # Calculate cost
        cost = profile.required_exp_for_level(2) // 10

        # Check coins
        if profile.coins_balance < cost:
            raise FarmServiceError("Insufficient coins")

        # Deduct coins
        profile.coins_balance -= cost
        profile.save(update_fields=['coins_balance'])

        # Create chunk
        FieldChunk.objects.create(
            profile=profile,
            chunk_row=chunk_row,
            chunk_col=chunk_col,
            is_unlocked=True,
        )

        logger.info(f"User {profile.user.username} bought chunk ({chunk_row}, {chunk_col})")

        return {
            'chunk_row': chunk_row,
            'chunk_col': chunk_col,
            'paid': cost,
            'coins_balance': profile.coins_balance,
            'next_cost': cost,
        }

    @staticmethod
    def get_field_state(profile: PlayerProfile) -> dict:
        """Get complete field state for a player."""
        chunks = FieldChunk.objects.filter(profile=profile)
        buildings = BuildingPlacement.objects.filter(profile=profile).select_related('building_type')
        available_buildings = BuildingType.objects.all()

        return {
            'field': {
                'chunk_size': 10,
                'max_size': 250,
                'next_chunk_cost': profile.required_exp_for_level(2) // 10,
            },
            'chunks': list(chunks.values('chunk_row', 'chunk_col')),
            'buildings': list(buildings.values(
                'id', 'row', 'col', 'width', 'height',
                'building_type__slug', 'building_type__name',
                'building_type__building_type'
            )),
            'available_buildings': list(available_buildings.values(
                'id', 'name', 'slug', 'width', 'height', 'price'
            )),
            'coins_balance': profile.coins_balance,
        }


class BuildingService:
    """Service for managing buildings."""

    @staticmethod
    @transaction.atomic
    def place_building(profile: PlayerProfile, building_id: int, row: int, col: int) -> dict:
        """Place a building on the field."""
        building_type = BuildingType.objects.filter(id=building_id).first()

        if not building_type:
            raise FarmServiceError("Building type not found")

        # Check coins
        if profile.coins_balance < building_type.price:
            raise FarmServiceError("Insufficient coins")

        # Check placement validity
        if not BuildingService._can_place(profile, row, col, building_type.width, building_type.height):
            raise FarmServiceError("Cannot place building here")

        # Deduct coins
        profile.coins_balance -= building_type.price
        profile.save(update_fields=['coins_balance'])

        # Create placement
        placement = BuildingPlacement.objects.create(
            profile=profile,
            building_type=building_type,
            row=row,
            col=col,
            width=building_type.width,
            height=building_type.height,
        )

        logger.info(f"User {profile.user.username} placed {building_type.name} at ({row}, {col})")

        return {
            'building': {
                'id': placement.id,
                'name': building_type.name,
                'slug': building_type.slug,
                'row': row,
                'col': col,
                'width': building_type.width,
                'height': building_type.height,
                'building_type': building_type.building_type,
            },
            'coins_balance': profile.coins_balance,
        }

    @staticmethod
    @transaction.atomic
    def remove_building(profile: PlayerProfile, placement_id: int) -> dict:
        """Remove (sell) a building."""
        placement = BuildingPlacement.objects.filter(
            id=placement_id,
            profile=profile,
        ).select_related('building_type').first()

        if not placement:
            raise FarmServiceError("Building not found")

        # Refund 50% of price
        refund = placement.building_type.price // 2
        profile.coins_balance += refund
        profile.save(update_fields=['coins_balance'])

        placement.delete()

        logger.info(f"User {profile.user.username} sold building {placement.building_type.name}")

        return {
            'coins_balance': profile.coins_balance,
            'refund': refund,
        }

    @staticmethod
    @transaction.atomic
    def move_building(profile: PlayerProfile, placement_id: int, row: int, col: int) -> dict:
        """Move a building to a new position."""
        placement = BuildingPlacement.objects.filter(
            id=placement_id,
            profile=profile,
        ).select_related('building_type').first()

        if not placement:
            raise FarmServiceError("Building not found")

        # Check if new position is valid
        if not BuildingService._can_place_at(profile, row, col, placement.width, placement.height, exclude_id=placement_id):
            raise FarmServiceError("Cannot move building here")

        # Update position
        placement.row = row
        placement.col = col
        placement.save(update_fields=['row', 'col'])

        logger.info(f"User {profile.user.username} moved building {placement.id} to ({row}, {col})")

        return {
            'success': True,
            'placement_id': placement_id,
            'row': row,
            'col': col,
        }

    @staticmethod
    def _can_place(profile: PlayerProfile, row: int, col: int, width: int, height: int) -> bool:
        """Check if a building can be placed at position."""
        return BuildingService._can_place_at(profile, row, col, width, height)

    @staticmethod
    def _can_place_at(profile: PlayerProfile, row: int, col: int, width: int, height: int, exclude_id: int = None) -> bool:
        """Check if position is valid for placement."""
        # Check bounds
        if row < 0 or col < 0:
            return False

        # Check if cells are unlocked
        from game.models import FieldChunk
        chunks = FieldChunk.objects.filter(profile=profile)
        unlocked_positions = set()
        for chunk in chunks:
            for r in range(chunk.chunk_row * 10, (chunk.chunk_row + 1) * 10):
                for c in range(chunk.chunk_col * 10, (chunk.chunk_col + 1) * 10):
                    unlocked_positions.add((r, c))

        for r in range(row, row + height):
            for c in range(col, col + width):
                if (r, c) not in unlocked_positions:
                    return False

        # Check collisions with other buildings
        existing = BuildingPlacement.objects.filter(profile=profile)
        if exclude_id:
            existing = existing.exclude(id=exclude_id)

        for building in existing:
            if BuildingService._rects_overlap(row, col, width, height, building.row, building.col, building.width, building.height):
                return False

        return True

    @staticmethod
    def _rects_overlap(r1, c1, w1, h1, r2, c2, w2, h2) -> bool:
        """Check if two rectangles overlap."""
        return not (c1 + w1 <= c2 or c2 + w2 <= c1 or r1 + h1 <= r2 or r2 + h2 <= r1)


class PlotService:
    """Service for managing farm plots."""

    @staticmethod
    def get_plots(profile: PlayerProfile) -> list:
        """Get all plots for a player's field buildings."""
        field_buildings = BuildingPlacement.objects.filter(
            profile=profile,
            building_type__building_type='field',
        )

        plots = []
        for building in field_buildings:
            plot = FarmPlot.objects.filter(building=building).first()
            if plot:
                plots.append({
                    'id': plot.id,
                    'building_id': building.id,
                    'status': plot.status,
                    'is_ready': plot.status == 'ready',
                    'planted_at': plot.planted_at.isoformat() if plot.planted_at else None,
                    'ready_at': plot.ready_at.isoformat() if plot.ready_at else None,
                })
            else:
                plots.append({
                    'id': None,
                    'building_id': building.id,
                    'status': 'empty',
                    'is_ready': False,
                })

        return plots

    @staticmethod
    @transaction.atomic
    def plant_seed(profile: PlayerProfile, building_id: int, seed_id: int) -> dict:
        """Plant a seed in a field building."""
        # Check if plot exists
        building = BuildingPlacement.objects.filter(
            id=building_id,
            profile=profile,
            building_type__building_type='field',
        ).first()

        if not building:
            raise FarmServiceError("Field building not found")

        plot = FarmPlot.objects.filter(building=building).first()

        if plot and plot.status != 'empty':
            raise FarmServiceError("Plot is not empty")

        # Check if player has the seed
        seed_item = ShopItem.objects.filter(id=seed_id, is_seed=True).first()
        if not seed_item:
            raise FarmServiceError("Seed not found")

        inventory_item = InventoryItem.objects.filter(
            player=profile,
            item=seed_item,
            quantity__gt=0,
        ).first()

        if not inventory_item:
            raise FarmServiceError("Seed not in inventory")

        # Get plant from seed
        plant = seed_item.plant  # Assuming reverse relation exists

        # Consume seed
        inventory_item.quantity -= 1
        if inventory_item.quantity <= 0:
            inventory_item.delete()
        else:
            inventory_item.save(update_fields=['quantity'])

        # Create or update plot
        if not plot:
            plot = FarmPlot.objects.create(
                building=building,
                plant=plant,
                status='growing',
            )
        else:
            plot.plant = plant
            plot.status = 'growing'
            plot.planted_at = timezone.now()
            plot.ready_at = plot.planted_at + timezone.timedelta(seconds=plant.grow_duration_seconds)
            plot.save()

        logger.info(f"User {profile.user.username} planted seed {seed_id} in building {building_id}")

        return {
            'success': True,
            'plot_id': plot.id,
            'coins_balance': profile.coins_balance,
        }

    @staticmethod
    @transaction.atomic
    def harvest_plot(profile: PlayerProfile, plot_id: int) -> dict:
        """Harvest a ready plot."""
        plot = FarmPlot.objects.filter(
            id=plot_id,
            building__profile=profile,
            status='ready',
        ).first()

        if not plot:
            raise FarmServiceError("Plot not found or not ready")

        # Get harvest product
        if not plot.plant or not plot.plant.harvest_product:
            raise FarmServiceError("No harvest product for this plant")

        harvest_product = plot.plant.harvest_product

        # Add to inventory
        inventory_item, created = InventoryItem.objects.get_or_create(
            player=profile,
            item=harvest_product,
            defaults={'quantity': 0}
        )
        inventory_item.quantity += harvest_product.harvest_yield
        inventory_item.save(update_fields=['quantity'])

        # Reset plot
        plot.status = 'empty'
        plot.planted_at = None
        plot.ready_at = None
        plot.save()

        logger.info(f"User {profile.user.username} harvested {harvest_product.name}")

        return {
            'success': True,
            'harvested': harvest_product.name,
            'quantity': harvest_product.harvest_yield,
        }
