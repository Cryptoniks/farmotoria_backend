from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import auth, field, production, shop

urlpatterns = [
    # служебное
    path("farmotoria/ping/", auth.FarmotoriaPingView.as_view(), name="ping"),

    # авторизация и профиль
    path("auth/register/", auth.RegisterView.as_view(), name="register"),
    path("auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("me/", auth.MeView.as_view(), name="me"),

    # магазин, инвентарь, рынок
    path("shop/items/", shop.ShopItemListView.as_view(), name="shop-items"),
    path("shop/seeds/", shop.ShopSeedsListView.as_view(), name="shop-seeds"),
    path("shop/harvest/", shop.ShopHarvestListView.as_view(), name="shop-harvest"),
    path("shop/buy/", shop.BuyItemView.as_view(), name="shop-buy"),
    path("inventory/", shop.InventoryView.as_view(), name="inventory"),
    path("inventory/resources/", shop.ResourcesInventoryView.as_view(), name="resources-inventory"),
    path("storage/", shop.StorageView.as_view(), name="storage"),
    path("market/inventory/", shop.MarketInventoryView.as_view(), name="market-inventory"),
    path("market/sell/", shop.SellItemView.as_view(), name="market-sell"),

    # изометрическое поле
    path("iso/field/", field.IsoFieldStateView.as_view(), name="iso-field"),
    path("iso/available-chunks/", field.IsoAvailableChunksView.as_view(), name="iso-available-chunks"),
    path("iso/expand-chunk/", field.IsoExpandChunkView.as_view(), name="iso-expand-chunk"),
    path("iso/place-building/", field.IsoPlaceBuildingView.as_view(), name="iso-place-building"),
    path("iso/remove-building/", field.IsoRemoveBuildingView.as_view(), name="iso-remove-building"),
    path("iso/move-building/", field.IsoMoveBuildingView.as_view(), name="iso-move-building"),
    path("iso/upgrade-building/", field.IsoUpgradeBuildingView.as_view(), name="iso-upgrade-building"),
    path("iso/move-buildings/", field.IsoMoveBuildingsBatchView.as_view(), name="iso-move-buildings"),
    path("iso/plant-seed/", field.IsoPlantSeedView.as_view(), name="iso-plant-seed"),
    path("iso/harvest/", field.IsoHarvestView.as_view(), name="iso-harvest"),
    path("iso/plots/", field.IsoFieldPlotsView.as_view(), name="iso-plots"),

    # добыча
    path("extraction/start/", production.ExtractionStartView.as_view(), name="extraction-start"),
    path("extraction/status/", production.ExtractionStatusView.as_view(), name="extraction-status"),
    path("extraction/collect/", production.ExtractionCollectView.as_view(), name="extraction-collect"),
    path("extraction/stop/", production.ExtractionStopView.as_view(), name="extraction-stop"),

    # переработка, производство, животноводство
    path("processing/recipes/", production.ProcessingRecipesView.as_view(), name="processing-recipes"),
    path("processing/start/", production.ProcessingStartView.as_view(), name="processing-start"),
    path("processing/status/", production.ProcessingStatusView.as_view(), name="processing-status"),
    path("processing/collect/", production.ProcessingCollectView.as_view(), name="processing-collect"),
    path("processing/stop/", production.ProcessingStopView.as_view(), name="processing-stop"),
]
