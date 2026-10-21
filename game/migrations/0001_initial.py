"""Начальная схема приложения game (единая миграция вместо прежних 0001–0013)."""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # =========================
        # Справочники
        # =========================
        migrations.CreateModel(
            name="ItemCategory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=50, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name="Skill",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=50, unique=True)),
                ("name", models.CharField(max_length=100)),
                ("max_level", models.PositiveIntegerField(default=10)),
                ("base_exp", models.PositiveIntegerField(default=50)),
                ("exp_growth", models.FloatField(default=1.3)),
                ("effect_name", models.CharField(max_length=100)),
                ("effect_description", models.TextField(blank=True)),
                ("effect_value_per_level", models.FloatField(default=0.0)),
            ],
            options={
                "verbose_name": "Навык",
                "verbose_name_plural": "Навыки",
            },
        ),
        migrations.CreateModel(
            name="BuildingType",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("slug", models.SlugField(unique=True)),
                ("building_type", models.CharField(
                    choices=[
                        ("field", "Поле"),
                        ("agroproduction", "Сельхозпроизводство"),
                        ("extraction", "Добыча ресурсов"),
                        ("processing", "Переработка"),
                        ("production", "Производство"),
                    ],
                    default="field",
                    max_length=20,
                )),
                ("width", models.PositiveIntegerField()),
                ("height", models.PositiveIntegerField()),
                ("price", models.PositiveIntegerField()),
            ],
            options={
                "indexes": [
                    models.Index(fields=["slug"], name="game_buildi_slug_8a8eb1_idx"),
                    models.Index(fields=["building_type"], name="game_buildi_buildin_cad9b4_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="ShopItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("description", models.TextField(blank=True)),
                ("slug", models.SlugField(max_length=100, unique=True)),
                ("price_coins", models.PositiveIntegerField(default=0, help_text="Цена продажи (игрок продаёт магазину)")),
                ("is_seed", models.BooleanField(default=False)),
                ("is_harvest", models.BooleanField(default=False)),
                ("is_resource", models.BooleanField(default=False)),
                ("grow_time_minutes", models.PositiveIntegerField(blank=True, null=True)),
                ("harvest_yield", models.PositiveIntegerField(default=2, help_text="Количество урожая при сборе")),
                ("category", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="game.itemcategory")),
                ("harvest_item", models.ForeignKey(
                    blank=True,
                    null=True,
                    help_text="Если это семя, то сюда ставим связанный урожай",
                    limit_choices_to={"is_harvest": True},
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="seed_item",
                    to="game.shopitem",
                )),
            ],
        ),

        # =========================
        # Игрок
        # =========================
        migrations.CreateModel(
            name="PlayerProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("coins_balance", models.PositiveIntegerField(default=0)),
                ("level", models.PositiveIntegerField(default=1)),
                ("exp", models.PositiveIntegerField(default=0)),
                ("base_exp", models.PositiveIntegerField(default=100)),
                ("exp_growth", models.FloatField(default=1.5)),
                ("user", models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="profile",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                "verbose_name": "Профиль игрока",
            },
        ),
        migrations.CreateModel(
            name="UserSkill",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("level", models.PositiveIntegerField(default=0)),
                ("exp", models.PositiveIntegerField(default=0)),
                ("skill", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="game.skill")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "unique_together": {("user", "skill")},
                "indexes": [
                    models.Index(fields=["user"], name="game_usersk_user_id_c079af_idx"),
                    models.Index(fields=["skill"], name="game_usersk_skill_i_a16120_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="InventoryItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantity", models.PositiveIntegerField(default=0)),
                ("item", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="game.shopitem")),
                ("player", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="game.playerprofile")),
            ],
            options={
                "unique_together": {("player", "item")},
                "indexes": [
                    models.Index(fields=["player"], name="game_invent_player__c0f460_idx"),
                    models.Index(fields=["item"], name="game_invent_item_id_2ead69_idx"),
                ],
            },
        ),

        # =========================
        # Изометрическое поле: чанки, здания, грядки
        # =========================
        migrations.CreateModel(
            name="FieldChunk",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("chunk_row", models.PositiveIntegerField()),
                ("chunk_col", models.PositiveIntegerField()),
                ("size", models.PositiveIntegerField(default=10)),
                ("price_paid", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("profile", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="field_chunks",
                    to="game.playerprofile",
                )),
            ],
            options={
                "unique_together": {("profile", "chunk_row", "chunk_col")},
                "indexes": [
                    models.Index(fields=["profile", "chunk_row", "chunk_col"], name="game_fieldc_profile_8301ef_idx"),
                    models.Index(fields=["profile", "price_paid"], name="game_fieldc_profile_c5bbc5_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="BuildingPlacement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("row", models.PositiveIntegerField()),
                ("col", models.PositiveIntegerField()),
                ("width", models.PositiveIntegerField()),
                ("height", models.PositiveIntegerField()),
                ("price_paid", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("building_type", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="placements",
                    to="game.buildingtype",
                )),
                ("profile", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="building_placements",
                    to="game.playerprofile",
                )),
            ],
            options={
                "indexes": [
                    models.Index(fields=["profile", "row", "col"], name="game_buildi_profile_7ccf1a_idx"),
                    models.Index(fields=["profile", "building_type"], name="game_buildi_profile_addbb8_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="FarmPlot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("cell_row", models.PositiveIntegerField()),
                ("cell_col", models.PositiveIntegerField()),
                ("planted_at", models.DateTimeField(auto_now_add=True)),
                ("ready_at", models.DateTimeField(blank=True, null=True)),
                ("status", models.CharField(
                    choices=[("growing", "Растёт"), ("ready", "Готов к сбору"), ("harvested", "Собран")],
                    default="growing",
                    max_length=20,
                )),
                ("building", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="plots",
                    to="game.buildingplacement",
                )),
                ("profile", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="farm_plots",
                    to="game.playerprofile",
                )),
                ("seed", models.ForeignKey(
                    limit_choices_to={"is_seed": True},
                    on_delete=django.db.models.deletion.CASCADE,
                    to="game.shopitem",
                )),
            ],
            options={
                "unique_together": {("profile", "building", "cell_row", "cell_col")},
                "indexes": [
                    models.Index(fields=["profile", "status"], name="game_farmpl_profile_9c25d3_idx"),
                    models.Index(fields=["building", "cell_row", "cell_col"], name="game_farmpl_buildin_2f4e85_idx"),
                ],
            },
        ),

        # =========================
        # Рецепты (переработка / производство)
        # =========================
        migrations.CreateModel(
            name="Recipe",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("slug", models.SlugField(unique=True)),
                ("recipe_group", models.CharField(
                    choices=[
                        ("field", "Поле"),
                        ("processing", "Переработка"),
                        ("production", "Производство"),
                        ("agroproduction", "Животноводство"),
                    ],
                    default="production",
                    max_length=20,
                )),
                ("price", models.PositiveIntegerField(default=0)),
                ("duration_seconds", models.PositiveIntegerField(default=60)),
                ("output_quantity", models.PositiveIntegerField(default=1)),
                ("skill_exp", models.PositiveIntegerField(default=0, help_text="Опыт навыка за один цикл")),
                ("building_type", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="recipes",
                    to="game.buildingtype",
                )),
                ("output_item", models.ForeignKey(
                    help_text="Готовый продукт",
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="recipes_as_output",
                    to="game.shopitem",
                )),
                ("skill", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="recipes",
                    to="game.skill",
                )),
            ],
            options={
                "verbose_name": "Рецепт",
                "verbose_name_plural": "Рецепты",
                "indexes": [
                    models.Index(fields=["recipe_group"], name="game_recipe_recipe__af1df3_idx"),
                    models.Index(fields=["slug"], name="game_recipe_slug_4a5923_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="RecipeIngredient",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantity", models.PositiveIntegerField(default=1)),
                ("item", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="game.shopitem")),
                ("recipe", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="ingredients",
                    to="game.recipe",
                )),
            ],
            options={
                "unique_together": {("recipe", "item")},
            },
        ),
        migrations.CreateModel(
            name="RecipeProcess",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("ready_at", models.DateTimeField(blank=True, null=True)),
                ("quantity", models.PositiveIntegerField(default=1)),
                ("quantity_done", models.PositiveIntegerField(default=0)),
                ("status", models.CharField(
                    choices=[("running", "Выполняется"), ("ready", "Готов"), ("completed", "Завершён")],
                    default="running",
                    max_length=20,
                )),
                ("building", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="recipe_processes",
                    to="game.buildingplacement",
                )),
                ("profile", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="recipe_processes",
                    to="game.playerprofile",
                )),
                ("recipe", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="game.recipe")),
            ],
            options={
                "indexes": [
                    models.Index(fields=["profile", "status"], name="game_recipe_profile_8a850d_idx"),
                    models.Index(fields=["building", "status"], name="game_recipe_buildin_ed9564_idx"),
                ],
            },
        ),

        # =========================
        # Добыча ресурсов
        # =========================
        migrations.CreateModel(
            name="ExtractionResource",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("slug", models.SlugField(unique=True)),
                ("duration_seconds", models.PositiveIntegerField(default=60)),
                ("output_quantity", models.PositiveIntegerField(default=1)),
                ("building_type", models.ForeignKey(
                    limit_choices_to={"building_type": "extraction"},
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="extraction_resources",
                    to="game.buildingtype",
                )),
                ("output_item", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="extraction_sources",
                    to="game.shopitem",
                )),
            ],
            options={
                "verbose_name": "Ресурс добычи",
                "verbose_name_plural": "Ресурсы добычи",
                "indexes": [
                    models.Index(fields=["building_type"], name="game_extrac_buildin_06899c_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="ExtractionProcess",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("next_harvest_at", models.DateTimeField(blank=True, null=True)),
                ("status", models.CharField(
                    choices=[("running", "Работает"), ("paused", "Приостановлен")],
                    default="running",
                    max_length=20,
                )),
                ("building", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="extraction_processes",
                    to="game.buildingplacement",
                )),
                ("profile", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="extraction_processes",
                    to="game.playerprofile",
                )),
                ("resource", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="game.extractionresource")),
            ],
            options={
                "indexes": [
                    models.Index(fields=["profile", "status"], name="game_extrac_profile_8c8ec5_idx"),
                    models.Index(fields=["building", "status"], name="game_extrac_buildin_dc95c9_idx"),
                ],
            },
        ),
    ]
