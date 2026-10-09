# game/admin.py
from django.contrib import admin

from .models import (
    PlayerProfile,
    FarmField,
    Cell,
    ItemCategory,
    ShopItem,
    InventoryItem,
    Skill,
    UserSkill,
    AreaLock,
    BuildingType,
    FieldChunk, 
    BuildingPlacement
)


@admin.register(PlayerProfile)
class PlayerProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "coins_balance", "level", "exp")
    search_fields = ("user__username", "user__email")
    list_select_related = ("user",)


@admin.register(FarmField)
class FarmFieldAdmin(admin.ModelAdmin):
    list_display = ("profile", "level", "grid_size", "max_cells", "expansion_cost_coins")
    search_fields = ("profile__user__username",)
    list_select_related = ("profile",)

    def grid_size(self, obj):
        return obj.level * 5

    grid_size.short_description = "Размер (NxN)"


@admin.register(Cell)
class CellAdmin(admin.ModelAdmin):
    list_display = (
        "profile",
        "object_type",
        "position",
        "coords",
        "is_anchor",
        "anchor_position",
        "size_w",
        "size_h",
        "planted_at",
        "grow_duration_seconds",
        "object_data_short",
    )
    list_filter = ("object_type", "is_anchor", "profile")
    search_fields = ("profile__user__username", "object_type", "object_data")
    list_select_related = ("profile",)
    ordering = ("profile_id", "position")

    def coords(self, obj):
        grid_size = 10
        try:
            if hasattr(obj.profile, "farm_field") and obj.profile.farm_field:
                grid_size = obj.profile.farm_field.level * 5
        except Exception:
            pass
        r, c = divmod(obj.position, grid_size)
        return f"{r}:{c}"

    coords.short_description = "Row:Col"

    def object_data_short(self, obj):
        s = str(obj.object_data) if obj.object_data else ""
        return s[:120] + ("…" if len(s) > 120 else "")

    object_data_short.short_description = "object_data"


@admin.register(BuildingType)
class BuildingTypeAdmin(admin.ModelAdmin):
    """
    Картинки только на фронте:
    src/assets/buildings/<slug>.(png|webp|jpg)

    На бэке храним только slug и параметры размещения.
    """
    list_display = ("name", "slug", "width", "height", "price")
    search_fields = ("name", "slug")
    list_filter = ("width", "height")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("id",)


@admin.register(AreaLock)
class AreaLockAdmin(admin.ModelAdmin):
    list_display = ("profile", "rect", "unlock_cost", "is_unlocked", "building_type")
    list_filter = ("is_unlocked", "profile")
    search_fields = ("profile__user__username", "building_type")
    ordering = ("profile_id", "row_start", "col_start")

    def rect(self, obj):
        return f"({obj.row_start},{obj.col_start}) {obj.rows}x{obj.cols}"

    rect.short_description = "Область"


@admin.register(ItemCategory)
class ItemCategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)
    ordering = ("id",)


@admin.register(ShopItem)
class ShopItemAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "price_coins", "category", "is_seed", "is_harvest")
    list_filter = ("category", "is_seed", "is_harvest")
    search_fields = ("name", "slug")
    ordering = ("id",)


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ("player", "item", "quantity")
    search_fields = ("player__user__username", "item__name", "item__slug")
    list_select_related = ("player", "item")
    ordering = ("player_id", "item_id")


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "max_level", "base_exp", "exp_growth", "effect_name", "effect_value_per_level")
    search_fields = ("code", "name")
    ordering = ("id",)


@admin.register(UserSkill)
class UserSkillAdmin(admin.ModelAdmin):
    list_display = ("user", "skill", "level", "exp")
    list_filter = ("skill",)
    search_fields = ("user__username", "skill__name", "skill__code")
    list_select_related = ("user", "skill")
    ordering = ("user_id", "skill_id")

@admin.register(FieldChunk)
class FieldChunkAdmin(admin.ModelAdmin):
    list_display = ("profile", "chunk_row", "chunk_col", "price_paid", "created_at")
    list_filter = ("profile",)
    search_fields = ("profile__user__username",)
    ordering = ("profile_id", "chunk_row", "chunk_col")


@admin.register(BuildingPlacement)
class BuildingPlacementAdmin(admin.ModelAdmin):
    list_display = ("profile", "building_type", "row", "col", "width", "height", "price_paid", "created_at")
    list_filter = ("profile", "building_type")
    search_fields = ("profile__user__username", "building_type__slug")
    ordering = ("profile_id", "row", "col")