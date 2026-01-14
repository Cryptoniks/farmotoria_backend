from django.contrib import admin
from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from game.views import (
    FarmotoriaPingView, RegisterView, MeView,
    CellListView, CellActionView, InventoryView,
    ShopSeedsListView, ShopHarvestListView, PlantListView,
    SellItemView, market_inventory, ShopByCategoryView, buy_item,
)

urlpatterns = [
    path("admin/", admin.site.urls),

    # ping
    path("api/farmotoria/ping/", FarmotoriaPingView.as_view()),

    # auth
    path("api/auth/register/", RegisterView.as_view()),
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # profile
    path("api/me/", MeView.as_view()),

    # field
    path("api/field/cells/", CellListView.as_view()),
    path("api/field/cells/action/", CellActionView.as_view()),
    path("api/plants/", PlantListView.as_view()),

    # inventory
    path("api/inventory/", InventoryView.as_view()),

    # ✅ SHOP - ТОЧНЫЕ МАРШРУТЫ ПЕРЕД параметрическими!
    path("api/shop/seeds/", ShopSeedsListView.as_view()),
    path("api/shop/harvest/", ShopHarvestListView.as_view()),
    path("api/shop/buy/", buy_item),  # ✅ ВЕРХУ перед <str:category>!!!

    # ✅ ПАРАМЕТРИЧЕСКИЙ - В КОНЦЕ (ловит Seeds, Products, Resources)
    path('api/shop/<str:category>/', ShopByCategoryView.as_view(), name='shop-category'),

    # market
    path("api/market/inventory/", market_inventory, name="market-inventory"),
    path("api/market/sell/", SellItemView.as_view()),
]