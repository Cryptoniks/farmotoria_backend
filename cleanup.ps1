# Очистка репозитория farmotoria_backend после оптимизации.
# Лишние файлы НЕ удаляются, а переносятся в папку _to_delete (с сохранением структуры),
# чтобы их можно было проверить. Когда убедитесь, что всё работает, удалите _to_delete.
#
# Запуск из корня проекта:
#   powershell -ExecutionPolicy Bypass -File .\cleanup.ps1
# Сразу удалить без переноса:
#   powershell -ExecutionPolicy Bypass -File .\cleanup.ps1 -Purge

param([switch]$Purge)

$root = $PSScriptRoot
$trash = Join-Path $root "_to_delete"

$items = @(
    "conftest.py"
    "farmotoria_backend\settings.py"
    "farmotoria_backend\settings_production.py"
    "farmotoria_backend\settings_render.py"
    "game\management\commands\check_all_recipes.py"
    "game\management\commands\check_buildings.py"
    "game\management\commands\check_chunks.py"
    "game\management\commands\check_feeds.py"
    "game\management\commands\check_inventory.py"
    "game\management\commands\check_items.py"
    "game\management\commands\check_items_skills.py"
    "game\management\commands\check_model.py"
    "game\management\commands\check_original_prices.py"
    "game\management\commands\check_placements.py"
    "game\management\commands\check_prices.py"
    "game\management\commands\check_production_recipes.py"
    "game\management\commands\check_recipe.py"
    "game\management\commands\check_shop.py"
    "game\management\commands\check_skills.py"
    "game\management\commands\clean_migrations.py"
    "game\management\commands\cleanup_old_items.py"
    "game\management\commands\create_agroproduction.py"
    "game\management\commands\create_animals.py"
    "game\management\commands\create_crops.py"
    "game\management\commands\create_production_recipes.py"
    "game\management\commands\create_recipes.py"
    "game\management\commands\create_skill.py"
    "game\management\commands\create_template_recipes.py"
    "game\management\commands\find_profile_get.py"
    "game\management\commands\fix_prices.py"
    "game\management\commands\fix_recipes.py"
    "game\management\commands\link_recipes.py"
    "game\management\commands\list_all.py"
    "game\management\commands\list_buildings.py"
    "game\management\commands\list_items.py"
    "game\management\commands\manage_categories.py"
    "game\management\commands\migrate_is_resource.py"
    "game\management\commands\restore_prices.py"
    "game\management\commands\revert_field.py"
    "game\management\commands\seed_field_chunks.py"
    "game\management\commands\set_resource_prices.py"
    "game\management\commands\setup_processing.py"
    "game\management\commands\test_sell.py"
    "game\management\commands\update_building_types.py"
    "game\management\commands\update_buy_prices.py"
    "game\management\commands\update_prices_to_sell_price.py"
    "game\management\commands\update_resources.py"
    "game\migrations\0001_clean_initial.py"
    "game\migrations\0002_remove_buildingtype_image.py"
    "game\migrations\0003_buildingplacement_fieldchunk.py"
    "game\migrations\0004_farm_plot.py"
    "game\migrations\0005_set_harvest_yield_default.py"
    "game\migrations\0006_add_profile_exp_fields.py"
    "game\migrations\0007_add_building_type.py"
    "game\migrations\0008_add_recipes.py"
    "game\migrations\0009_add_extraction_resources.py"
    "game\migrations\0010_add_is_resource.py"
    "game\migrations\0011_add_building_type_to_recipe.py"
    "game\migrations\0012_add_quantity_to_recipe_process.py"
    "game\migrations\0013_add_skill_to_recipe.py"
    "game\migrations\0014_merge_conflict.py"
    "game\scheduler.py"
    "game\serializers\farm.py"
    "game\services\economy_service.py"
    "game\services\farm_service.py"
    "game\services\inventory_service.py"
    "game\services\recipe_service.py"
    "game\services\skill_service.py"
    "game\tests.py"
    "game\tests\test_serializers.py"
    "game\tests\test_views.py"
    "game\views\farm.py"
    "game\views\helpers.py"
    "game\views\inventory.py"
    "game\views\iso.py"
    "django.log"
    "game\migrations\migrations"
)

$moved = 0
foreach ($rel in $items) {
    $src = Join-Path $root $rel
    if (-not (Test-Path -LiteralPath $src)) { continue }
    if ($Purge) {
        Remove-Item -LiteralPath $src -Recurse -Force
    } else {
        $dst = Join-Path $trash $rel
        New-Item -ItemType Directory -Force -Path (Split-Path $dst) | Out-Null
        Move-Item -LiteralPath $src -Destination $dst -Force
    }
    $moved++
    Write-Host "  - $rel"
}

# Новый CI-конфиг: ci.new.yml -> .github\workflows\ci.yml
$newCi = Join-Path $root "ci.new.yml"
if (Test-Path -LiteralPath $newCi) {
    $ci = Join-Path $root ".github\workflows\ci.yml"
    if ((Test-Path -LiteralPath $ci) -and -not $Purge) {
        $dst = Join-Path $trash ".github\workflows\ci.yml"
        New-Item -ItemType Directory -Force -Path (Split-Path $dst) | Out-Null
        Move-Item -LiteralPath $ci -Destination $dst -Force
    }
    New-Item -ItemType Directory -Force -Path (Split-Path $ci) | Out-Null
    Move-Item -LiteralPath $newCi -Destination $ci -Force
    Write-Host "  * обновлён .github\workflows\ci.yml"
}

# Кэш Python (.pyc) пересоздаётся автоматически
Get-ChildItem -Path $root -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath (Join-Path $root ".pytest_cache") -Recurse -Force -ErrorAction SilentlyContinue

if ($Purge) {
    Write-Host "`nУдалено объектов: $moved"
} else {
    Write-Host "`nПеренесено в _to_delete: $moved"
    Write-Host "Проверьте проект и удалите папку _to_delete вручную."
}
