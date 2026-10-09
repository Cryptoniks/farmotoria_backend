import logging
import sys
from apscheduler.schedulers.background import BackgroundScheduler
from django.utils import timezone
from django.db import transaction

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Глобальный планировщик
scheduler = BackgroundScheduler()


def auto_collect_extraction():
    """
    Автоматический сбор ресурсов добычи.
    Запускается каждые 5 секунд.
    """
    from game.models import ExtractionProcess, PlayerProfile, InventoryItem, Skill, UserSkill
    
    try:
        now = timezone.now()
        
        # Находим все готовые процессы
        ready_processes = ExtractionProcess.objects.filter(
            status="running",
            next_harvest_at__lte=now
        ).select_related(
            "profile", 
            "resource__output_item",
            "building__building_type"
        )
        
        collected_count = 0
        
        for process in ready_processes:
            try:
                with transaction.atomic():
                    # Добавляем ресурс в инвентарь
                    output_item = process.resource.output_item
                    inv_item, _ = InventoryItem.objects.get_or_create(
                        player=process.profile,
                        item=output_item,
                        defaults={"quantity": 0}
                    )
                    inv_item.quantity += process.resource.output_quantity
                    inv_item.save()
                    
                    # Начисляем опыт навыку
                    user_skill = None
                    try:
                        extraction_skill = Skill.objects.get(code='extraction')
                        user_skill = UserSkill.objects.get(
                            user=process.profile.user, 
                            skill=extraction_skill
                        )
                        user_skill.add_exp(1)
                    except (Skill.DoesNotExist, UserSkill.DoesNotExist):
                        pass
                    
                    # Перезапускаем цикл
                    duration = process.resource.duration_seconds
                    
                    # Учёт бонуса навыка
                    skill_level = user_skill.level if user_skill else 0
                    reduction_factor = 1.0 - (skill_level * 0.02)
                    if reduction_factor < 0.8:
                        reduction_factor = 0.8
                    duration = int(duration * reduction_factor)
                    
                    process.next_harvest_at = now + timezone.timedelta(seconds=duration)
                    process.save()
                    
                    collected_count += 1
                    logger.info(f"Auto-collected: {process.resource.name} x{process.resource.output_quantity} for user {process.profile.user.username}")
                    
            except Exception as e:
                logger.error(f"Error collecting extraction {process.id}: {e}")
        
        if collected_count > 0:
            logger.info(f"Auto-collected {collected_count} extraction resources")
            
    except Exception as e:
        logger.error(f"Auto-collect error: {e}")


def start_scheduler():
    """Запуск планировщика"""
    logger.info("Starting scheduler...")
    try:
        scheduler.add_job(
            auto_collect_extraction,
            'interval',
            seconds=5,
            id='auto_collect_extraction',
            replace_existing=True
        )
        scheduler.start()
        logger.info("Scheduler started for auto-collect extraction")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")
