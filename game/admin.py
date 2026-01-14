from django.contrib import admin
from .models import (
    PlayerProfile,
    ItemCategory,
    ShopItem,
    Cell,
    InventoryItem,
    Skill,
    UserSkill,
)

# =========================
# Профиль игрока
# =========================
@admin.register(PlayerProfile)
class PlayerProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "coins_balance", "level", "exp")
    search_fields = ("user__username",)
    list_editable = ("coins_balance",)

# =========================
# Категории товаров
# =========================
@admin.register(ItemCategory)
class ItemCategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)

# =========================
# Магазинные товары
# =========================
@admin.register(ShopItem)
class ShopItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "category",
        "price_coins",
        "is_seed",
        "is_harvest",
        "grow_time_minutes",
        "harvest_yield",
        "harvest_item",
    )
    list_filter = ("category", "is_seed", "is_harvest")
    search_fields = ("name", "category__name")
    raw_id_fields = ("harvest_item",)

# =========================
# Клетки с растениями
# =========================
@admin.register(Cell)
class CellAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "row", "col", "shop_item", "planted_at", "is_growing")
    list_filter = ("owner", "shop_item")
    search_fields = ("owner__username", "shop_item__name")
    readonly_fields = ("is_growing",)

# =========================
# Инвентарь игроков
# =========================
@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ("id", "player", "item", "quantity")
    list_filter = ("player", "item")
    search_fields = ("player__user__username", "item__name")
    list_per_page = 50

# =========================
# Навыки
# =========================
@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
        "max_level",
        "base_exp",
        "exp_growth",
        "effect_name",
        "effect_value_per_level",
    )
    list_editable = (
        "max_level",
        "base_exp",
        "exp_growth",
        "effect_value_per_level",
    )
    search_fields = ("name", "code", "effect_name")
    list_filter = ("max_level",)

@admin.register(UserSkill)
class UserSkillAdmin(admin.ModelAdmin):
    list_display = ("user", "skill", "level", "exp")
    list_filter = ("skill", "level")
    search_fields = ("user__username", "skill__name")