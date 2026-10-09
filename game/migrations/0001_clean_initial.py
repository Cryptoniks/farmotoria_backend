"""
Clean migration for production deployment.
This migration combines all previous migrations into one.
Run: python manage.py migrate game 0001_initial
     python manage.py migrate game
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        # User Profile
        migrations.CreateModel(
            name='PlayerProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('coins_balance', models.PositiveIntegerField(default=1000)),
                ('level', models.PositiveIntegerField(default=1)),
                ('exp', models.PositiveIntegerField(default=0)),
                ('base_exp', models.PositiveIntegerField(default=100)),
                ('exp_growth', models.FloatField(default=1.5)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='auth.user')),
            ],
        ),

        # Skills
        migrations.CreateModel(
            name='Skill',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.SlugField(unique=True)),
                ('name', models.CharField(max_length=100)),
                ('max_level', models.PositiveIntegerField(default=10)),
                ('base_exp', models.PositiveIntegerField(default=100)),
                ('exp_growth', models.FloatField(default=1.5)),
                ('effect_name', models.CharField(blank=True, max_length=100)),
                ('effect_description', models.TextField(blank=True)),
                ('effect_value_per_level', models.FloatField(default=0.1)),
            ],
        ),

        migrations.CreateModel(
            name='UserSkill',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('level', models.PositiveIntegerField(default=1)),
                ('exp', models.PositiveIntegerField(default=0)),
                ('skill', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='game.skill')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='auth.user')),
            ],
            options={
                'unique_together': {('user', 'skill')},
            },
        ),

        # Building Types
        migrations.CreateModel(
            name='BuildingType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('slug', models.SlugField(unique=True)),
                ('building_type', models.CharField(choices=[('field', 'Field'), ('extraction', 'Extraction'), ('processing', 'Processing'), ('production', 'Production'), ('agroproduction', 'Agroproduction'), ('storage', 'Storage'), ('agriculture', 'Agriculture')], max_length=50)),
                ('width', models.PositiveIntegerField(default=1)),
                ('height', models.PositiveIntegerField(default=1)),
                ('price', models.PositiveIntegerField(default=100)),
            ],
        ),

        # Field Chunks
        migrations.CreateModel(
            name='FieldChunk',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('chunk_row', models.IntegerField()),
                ('chunk_col', models.IntegerField()),
                ('is_unlocked', models.BooleanField(default=False)),
                ('profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='game.playerprofile')),
            ],
            options={
                'unique_together': {('profile', 'chunk_row', 'chunk_col')},
            },
        ),

        # Building Placements
        migrations.CreateModel(
            name='BuildingPlacement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('row', models.IntegerField()),
                ('col', models.IntegerField()),
                ('width', models.PositiveIntegerField(default=1)),
                ('height', models.PositiveIntegerField(default=1)),
                ('building_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='game.buildingtype')),
                ('profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='game.playerprofile')),
            ],
            options={
                'unique_together': {('profile', 'row', 'col')},
            },
        ),

        # Items and Categories
        migrations.CreateModel(
            name='ItemCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('slug', models.SlugField(unique=True)),
                ('description', models.TextField(blank=True)),
            ],
        ),

        migrations.CreateModel(
            name='ShopItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('slug', models.SlugField(unique=True)),
                ('price_coins', models.PositiveIntegerField(default=0)),
                ('sell_price', models.PositiveIntegerField(default=0)),
                ('is_seed', models.BooleanField(default=False)),
                ('is_harvest', models.BooleanField(default=False)),
                ('is_resource', models.BooleanField(default=False)),
                ('harvest_yield', models.PositiveIntegerField(default=1)),
                ('category', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='game.itemcategory')),
            ],
        ),

        # Inventory
        migrations.CreateModel(
            name='InventoryItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField(default=1)),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='game.shopitem')),
                ('player', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='game.playerprofile')),
            ],
            options={
                'unique_together': {('player', 'item')},
            },
        ),

        # Plants
        migrations.CreateModel(
            name='Plant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('slug', models.SlugField(unique=True)),
                ('grow_duration_seconds', models.PositiveIntegerField(default=300)),
                ('description', models.TextField(blank=True)),
                ('harvest_product', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='game.shopitem')),
            ],
        ),

        # Recipes
        migrations.CreateModel(
            name='Recipe',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('slug', models.SlugField(unique=True)),
                ('recipe_group', models.CharField(blank=True, max_length=50)),
                ('price', models.PositiveIntegerField(default=0)),
                ('duration_seconds', models.PositiveIntegerField(default=300)),
                ('output_quantity', models.PositiveIntegerField(default=1)),
                ('building_type', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='game.buildingtype')),
                ('output_item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='game.shopitem')),
            ],
        ),

        migrations.CreateModel(
            name='RecipeIngredient',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField(default=1)),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='game.shopitem')),
                ('recipe', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='game.recipe')),
            ],
            options={
                'unique_together': {('recipe', 'item')},
            },
        ),

        # Farm Plots
        migrations.CreateModel(
            name='FarmPlot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cell_row', models.IntegerField()),
                ('cell_col', models.IntegerField()),
                ('status', models.CharField(choices=[('empty', 'Empty'), ('growing', 'Growing'), ('ready', 'Ready')], default='empty', max_length=20)),
                ('planted_at', models.DateTimeField(auto_now_add=True)),
                ('ready_at', models.DateTimeField(blank=True, null=True)),
                ('building', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='game.buildingplacement')),
                ('plant', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='game.plant')),
            ],
        ),

        # Extraction Resources
        migrations.CreateModel(
            name='ExtractionResource',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('output_item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='game.shopitem')),
            ],
        ),
    ]
