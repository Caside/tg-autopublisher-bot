import asyncio
import logging
from datetime import datetime, timedelta
import pytz
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from config import BOT_TOKEN, CHANNEL_ID, TIMEZONE
from deepseek_client import DeepSeekClient
from schedule_config import SCHEDULE_CONFIG

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Получаем часовой пояс
tz = pytz.timezone(TIMEZONE)

# Инициализация клиента DeepSeek
deepseek_client = DeepSeekClient()

@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_info = f"user_id={message.from_user.id}, username=@{message.from_user.username}"
    logger.info(f"Получена команда /start от пользователя: {user_info}")
    
    await message.answer(
        "Привет! Я бот для автоматической публикации постов.\n\n"
        "Доступные команды:\n"
        "/publish_now - Немедленно сгенерировать и опубликовать пост\n"
        "/schedule_status - Просмотр статуса автоматических публикаций"
    )

@dp.message(Command("publish_now"))
async def cmd_publish_now(message: Message):
    """Немедленно генерирует и публикует пост в канал."""
    user_info = f"user_id={message.from_user.id}, username=@{message.from_user.username}"
    logger.info(f"Получена команда /publish_now от пользователя: {user_info}")
    
    # Отправляем сообщение о начале генерации
    status_msg = await message.answer("Генерирую и публикую пост в канал... Это может занять несколько секунд.")
    
    try:
        # Генерируем новый пост
        post_text = await deepseek_client.generate_post()
        
        if not post_text:
            await status_msg.edit_text(
                "Не удалось сгенерировать пост. Пожалуйста, проверьте настройки API DeepSeek "
                "или попробуйте позже."
            )
            return
        
        # Публикуем сгенерированный пост напрямую в канал
        await status_msg.edit_text(f"Отправляю пост в канал {CHANNEL_ID}...")
        
        # Отправляем в канал
        await bot.send_message(CHANNEL_ID, post_text)
        
        # Сообщаем об успешной отправке
        await status_msg.edit_text(
            f"✅ Пост успешно опубликован в канале {CHANNEL_ID}!\n\n"
            f"Предварительный просмотр:\n\n"
            f"{post_text[:200]}{'...' if len(post_text) > 200 else ''}"
        )
        
        logger.info(f"Пост успешно опубликован в канале пользователем {user_info}")
        
    except Exception as e:
        error_msg = f"Произошла ошибка при публикации поста: {str(e)}"
        logger.error(error_msg)
        await status_msg.edit_text(
            f"⚠️ Ошибка при публикации поста: {str(e)}\n"
            f"Пожалуйста, проверьте настройки и права бота в канале."
        )

@dp.message(Command("schedule_status"))
async def cmd_schedule_status(message: Message):
    """Просмотр статуса автоматических публикаций."""
    user_info = f"user_id={message.from_user.id}, username=@{message.from_user.username}"
    logger.info(f"Получена команда /schedule_status от пользователя: {user_info}")
    
    config = SCHEDULE_CONFIG
    
    enabled = "Включено" if config["enabled"] else "Выключено"
    
    # Дни недели
    days_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    days = ", ".join(days_names[day] for day in config["days_of_week"])
    
    # Время публикаций
    if config["specific_times"]:
        times = ", ".join(f"{t['hour']:02d}:{t['minute']:02d}" for t in config["specific_times"])
        schedule_info = f"В определенное время: {times}"
    else:
        start = f"{config['start_time']['hour']:02d}:{config['start_time']['minute']:02d}"
        end = f"{config['end_time']['hour']:02d}:{config['end_time']['minute']:02d}"
        interval = config["interval_minutes"]
        schedule_info = f"С {start} до {end} каждые {interval} минут"
    
    # Формируем ответное сообщение
    status_message = (
        f"Статус автоматических публикаций:\n\n"
        f"Состояние: {enabled}\n"
        f"Дни публикаций: {days}\n"
        f"Расписание: {schedule_info}\n\n"
        f"Часовой пояс: {TIMEZONE}"
    )
    
    await message.answer(status_message)

async def schedule_posts():
    """Функция для публикации постов по расписанию."""
    logger.info("Запуск планировщика публикаций")
    
    while True:
        try:
            if SCHEDULE_CONFIG["enabled"]:
                current_time = datetime.now(tz)
                
                # Проверяем, нужно ли публиковать пост сейчас
                if SCHEDULE_CONFIG["specific_times"]:
                    # Проверяем конкретные времена
                    for time_spec in SCHEDULE_CONFIG["specific_times"]:
                        if (current_time.hour == time_spec["hour"] and 
                            current_time.minute == time_spec["minute"] and 
                            current_time.weekday() in SCHEDULE_CONFIG["days_of_week"]):
                            await publish_scheduled_post()
                else:
                    # Проверяем интервалы
                    start_time = current_time.replace(
                        hour=SCHEDULE_CONFIG["start_time"]["hour"],
                        minute=SCHEDULE_CONFIG["start_time"]["minute"],
                        second=0,
                        microsecond=0
                    )
                    end_time = current_time.replace(
                        hour=SCHEDULE_CONFIG["end_time"]["hour"],
                        minute=SCHEDULE_CONFIG["end_time"]["minute"],
                        second=0,
                        microsecond=0
                    )
                    
                    if (start_time <= current_time <= end_time and 
                        current_time.weekday() in SCHEDULE_CONFIG["days_of_week"]):
                        # Проверяем, прошло ли нужное количество минут с начала дня
                        minutes_since_start = (current_time - start_time).total_seconds() / 60
                        if minutes_since_start % SCHEDULE_CONFIG["interval_minutes"] == 0:
                            await publish_scheduled_post()
            
            # Ждем 1 минуту перед следующей проверкой
            await asyncio.sleep(60)
            
        except Exception as e:
            logger.error(f"Ошибка в планировщике: {str(e)}")
            await asyncio.sleep(60)

async def publish_scheduled_post():
    """Публикует пост по расписанию."""
    try:
        logger.info("Генерация и публикация поста по расписанию")
        
        # Генерируем новый пост
        post_text = await deepseek_client.generate_post()
        
        if post_text:
            # Публикуем в канал
            await bot.send_message(CHANNEL_ID, post_text)
            logger.info("Пост успешно опубликован по расписанию")
        else:
            logger.error("Не удалось сгенерировать пост для публикации по расписанию")
            
    except Exception as e:
        logger.error(f"Ошибка при публикации поста по расписанию: {str(e)}")

async def main():
    logger.info(f"Бот запущен. Часовой пояс: {TIMEZONE}")
    
    # Запускаем планировщик публикаций
    asyncio.create_task(schedule_posts())
    
    # Запускаем бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
