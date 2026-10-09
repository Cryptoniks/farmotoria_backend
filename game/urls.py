from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import (
    # auth
    FarmotoriaPingView,
    RegisterView,
    MeView,
    
    # farm
    FarmFieldView,
    ExpandFieldView,
    PlaceObjectView,
    PlaceBuildingView,
    RemoveBuildingView,
    UnlockAreaView,
    CellListView,
    
    # shop
    ShopItemListView,
    ShopSeedsListView,
    ShopHarvestListView,
    PlantListView,
    ShopByCategoryView,
    buy_item,
    
    # inventory
    InventoryView,
    market_inventory,
    resources_inventory,
    SellItemView,
    
    # iso
    IsoFieldStateView,
    IsoExpandChunkView,
    IsoAvailableChunksView,
    IsoPlaceBuildingView,
    IsoRemoveBuildingView,
    IsoPlantSeedView,
    IsoHarvestView,
    IsoFieldPlotsView,
    IsoMoveBuildingView,
    IsoMoveBuildingsBatchView,
    ExtractionStartView,
    ExtractionStatusView,
    ExtractionCollectView,
    ExtractionStopView,
    ProcessingRecipesView,
    ProcessingStartView,
    ProcessingStatusView,
    ProcessingCollectView,
    ProcessingStopView,
)

urlpatterns = [
    # ping
    path("farmotoria/ping/", FarmotoriaPingView.as_view(), name="ping"),

    # auth
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # profile
    path("me/", MeView.as_view(), name="me"),

    # field
    path("field/", FarmFieldView.as_view(), name="farm-field"),
    path("field/expand/", ExpandFieldView.as_view(), name="expand-field"),
    path("field/place/", PlaceObjectView.as_view(), name="place-object"),
    path("field/unlock-area/", UnlockAreaView.as_view(), name="unlock-area"),
    path("field/place-building/", PlaceBuildingView.as_view(), name="place-building"),
    path("field/remove-building/", RemoveBuildingView.as_view(), name="remove-building"),

    # plants
    path("plants/", PlantListView.as_view(), name="plants"),

    # inventory
    path("inventory/", InventoryView.as_view(), name="inventory"),

    # shop (важно: точные маршруты перед параметрическими)
    path("shop/items/", ShopItemListView.as_view(), name="shop-items"),
    path("shop/seeds/", ShopSeedsListView.as_view(), name="shop-seeds"),
    path("shop/harvest/", ShopHarvestListView.as_view(), name="shop-harvest"),
    path("shop/buy/", buy_item, name="shop-buy"),
    path("shop/<str:category>/", ShopByCategoryView.as_view(), name="shop-category"),

    # market
    path("market/inventory/", market_inventory, name="market-inventory"),
    path("market/sell/", SellItemView.as_view(), name="market-sell"),
    path("inventory/resources/", resources_inventory, name="resources-inventory"),

    # ISO field (pixi)
    path("iso/field/", IsoFieldStateView.as_view(), name="iso-field"),
    path("iso/expand-chunk/", IsoExpandChunkView.as_view(), name="iso-expand-chunk"),
    path("iso/available-chunks/", IsoAvailableChunksView.as_view(), name="iso-available-chunks"),
    path("iso/place-building/", IsoPlaceBuildingView.as_view(), name="iso-place-building"),
    path("iso/remove-building/", IsoRemoveBuildingView.as_view(), name="iso-remove-building"),
    path("iso/move-building/", IsoMoveBuildingView.as_view(), name="iso-move-building"),
    path("iso/move-buildings/", IsoMoveBuildingsBatchView.as_view(), name="iso-move-buildings"),
    path("iso/plant-seed/", IsoPlantSeedView.as_view(), name="iso-plant-seed"),
    path("iso/harvest/", IsoHarvestView.as_view(), name="iso-harvest"),
    path("iso/plots/", IsoFieldPlotsView.as_view(), name="iso-plots"),
    
    # extraction (добыча)
    path("extraction/start/", ExtractionStartView.as_view(), name="extraction-start"),
    path("extraction/status/", ExtractionStatusView.as_view(), name="extraction-status"),
    path("extraction/collect/", ExtractionCollectView.as_view(), name="extraction-collect"),
    path("extraction/stop/", ExtractionStopView.as_view(), name="extraction-stop"),
    
    # processing (переработка)
    path("processing/recipes/", ProcessingRecipesView.as_view(), name="processing-recipes"),
    path("processing/start/", ProcessingStartView.as_view(), name="processing-start"),
    path("processing/status/", ProcessingStatusView.as_view(), name="processing-status"),
    path("processing/collect/", ProcessingCollectView.as_view(), name="processing-collect"),
    path("processing/stop/", ProcessingStopView.as_view(), name="processing-stop"),
]
