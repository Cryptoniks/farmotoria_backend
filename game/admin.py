from django.contrib import admin

from .models import (
    BuildingPlacement,
    BuildingType,
    ExtractionProcess,
    ExtractionResource,
    FarmPlot,
    FieldChunk,
    InventoryItem,
    ItemCategory,
    PlayerProfile,
    Recipe,
    RecipeIngredient,
    RecipeProcess,
    ShopItem,
    Skill,
    UserSkill,
)


# --------------------------------------------------------------- справочники ----
@admin.register(ItemCategory)
class ItemCategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


@admin.register(ShopItem)
class ShopItemAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "category", "price_coins", "storage", "is_seed", "is_harvest", "is_resource")
    list_filter = ("category", "storage", "is_seed", "is_harvest", "is_resource")
    search_fields = ("name", "slug")
    list_select_related = ("category",)
    autocomplete_fields = ("harvest_item",)


@admin.register(BuildingType)
class BuildingTypeAdmin(admin.ModelAdmin):
    """Картинки зданий лежат на фронтенде: src/assets/buildings/<slug>.svg"""

    list_display = ("name", "slug", "building_type", "width", "height", "price", "max_level", "capacity")
    list_filter = ("building_type",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    fieldsets = (
        (None, {"fields": ("name", "slug", "building_type", "width", "height", "price")}),
        ("Уровни", {
            "fields": ("max_level", "upgrade_price_growth", "upgrade_seconds",
                       "yield_bonus_per_level", "speed_bonus_per_level"),
            "description": "Цена улучшения с L на L+1 = цена × рост^(L−1). "
                           "Выход ×(1 + бонус × (L−1)), время −бонус × (L−1) (вместе с навыком не меньше 20%).",
        }),
        ("Хранилище (Склад, Сарай)", {
            "fields": ("storage", "capacity", "capacity_bonus_per_level"),
            "description": "Вместимость = вместимость × (1 + бонус × (L−1)).",
        }),
    )


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "max_level", "base_exp", "exp_growth", "effect_name", "effect_value_per_level")
    search_fields = ("code", "name")


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1
    autocomplete_fields = ("item",)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "recipe_group", "building_type", "output_item", "output_quantity", "duration_seconds")
    list_filter = ("recipe_group", "building_type")
    search_fields = ("name", "slug")
    list_select_related = ("building_type", "output_item")
    autocomplete_fields = ("output_item",)
    inlines = [RecipeIngredientInline]


@admin.register(ExtractionResource)
class ExtractionResourceAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "building_type", "output_item", "output_quantity", "duration_seconds")
    list_select_related = ("building_type", "output_item")
    autocomplete_fields = ("output_item",)


# -------------------------------------------------------------------- игроки ----
@admin.register(PlayerProfile)
class PlayerProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "coins_balance", "level", "exp")
    search_fields = ("user__username", "user__email")
    list_select_related = ("user",)


@admin.register(UserSkill)
class UserSkillAdmin(admin.ModelAdmin):
    list_display = ("user", "skill", "level", "exp")
    list_filter = ("skill",)
    search_fields = ("user__username",)
    list_select_related = ("user", "skill")


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ("player", "item", "quantity")
    search_fields = ("player__user__username", "item__name", "item__slug")
    list_select_related = ("player__user", "item")


@admin.register(FieldChunk)
class FieldChunkAdmin(admin.ModelAdmin):
    list_display = ("profile", "chunk_row", "chunk_col", "price_paid", "created_at")
    search_fields = ("profile__user__username",)
    list_select_related = ("profile__user",)


@admin.register(BuildingPlacement)
class BuildingPlacementAdmin(admin.ModelAdmin):
    list_display = ("profile", "building_type", "level", "row", "col", "width", "height", "price_paid", "created_at")
    list_filter = ("building_type",)
    search_fields = ("profile__user__username", "building_type__slug")
    list_select_related = ("profile__user", "building_type")


@admin.register(FarmPlot)
class FarmPlotAdmin(admin.ModelAdmin):
    list_display = ("profile", "building", "cell_row", "cell_col", "seed", "status", "ready_at")
    list_filter = ("status",)
    list_select_related = ("profile__user", "seed", "building__building_type")


@admin.register(RecipeProcess)
class RecipeProcessAdmin(admin.ModelAdmin):
    list_display = ("profile", "building", "recipe", "quantity", "quantity_done", "status", "ready_at")
    list_filter = ("status",)
    list_select_related = ("profile__user", "recipe", "building__building_type")


@admin.register(ExtractionProcess)
class ExtractionProcessAdmin(admin.ModelAdmin):
    list_display = ("profile", "building", "resource", "status", "next_harvest_at")
    list_filter = ("status",)
    list_select_related = ("profile__user", "resource", "building__building_type")
