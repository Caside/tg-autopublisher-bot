import asyncio
from datetime import datetime, timedelta
import sqlite3
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from config import BOT_TOKEN, CHANNEL_ID, TIMEZONE
from database import Database
import pytz
import logging.handlers
import csv
from io import StringIO

# Импортируем новые модули
from scheduler import PostScheduler
from deepseek_client import DeepSeekClient

# Настройка расширенного логирования
logger = logging.getLogger('scheduler_bot')
logger.setLevel(logging.INFO)

# Форматтер для логов
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Хендлер для вывода в консоль
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Получаем часовой пояс
tz = pytz.timezone(TIMEZONE)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Инициализация базы данных
db = Database()

# Инициализация планировщика
scheduler = PostScheduler(bot)

@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_info = f"user_id={message.from_user.id}, username=@{message.from_user.username}"
    logger.info(f"Получена команда /start от пользователя: {user_info}")
    
    await message.answer(
        "Привет! Я бот для отложенной публикации постов.\n"
        "Используйте команду /schedule чтобы запланировать пост.\n"
        "Формат: /schedule YYYY-MM-DD HH:MM текст поста\n\n"
        "Также я могу автоматически генерировать и публиковать посты с помощью DeepSeek AI.\n"
        "Используйте /autogen_status для просмотра статуса автоматических публикаций."
    )

@dp.message(Command("schedule"))
async def cmd_schedule(message: Message):
    user_info = f"user_id={message.from_user.id}, username=@{message.from_user.username}"
    logger.info(f"Получена команда /schedule от пользователя: {user_info}")
    
    try:
        # Разбираем сообщение
        parts = message.text.split(maxsplit=3)
        if len(parts) < 4:
            logger.warning(f"Неверный формат команды от пользователя: {user_info}")
            raise ValueError("Неверный формат")
        
        _, date_str, time_str, post_text = parts
        naive_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        scheduled_time = tz.localize(naive_datetime)
        
        # Проверяем, что дата в будущем
        if scheduled_time <= datetime.now(tz):
            logger.warning(f"Попытка запланировать пост в прошлом от пользователя: {user_info}")
            raise ValueError("Дата должна быть в будущем")
        
        # Сохраняем в базу данных
        db.add_scheduled_post(scheduled_time, post_text)
        
        logger.info(
            f"Запланирован новый пост от {user_info}\n"
            f"Дата публикации: {scheduled_time}\n"
            f"Текст: {post_text[:100]}{'...' if len(post_text) > 100 else ''}"
        )
        
        await message.answer(
            f"Пост запланирован на {date_str} {time_str} "
            f"(часовой пояс: {TIMEZONE})"
        )
        
    except ValueError as e:
        logger.error(f"Ошибка при планировании поста от {user_info}: {str(e)}")
        await message.answer(
            "Ошибка! Используйте формат:\n"
            "/schedule YYYY-MM-DD HH:MM текст поста"
        )

@dp.message(Command("help"))
async def cmd_help(message: Message):
    user_info = f"user_id={message.from_user.id}, username=@{message.from_user.username}"
    logger.info(f"Получена команда /help от пользователя: {user_info}")
    
    await message.answer(
        "Доступные команды:\n\n"
        "/schedule - Запланировать одиночный пост\n"
        "Формат: /schedule YYYY-MM-DD HH:MM текст поста\n\n"
        "/bulk_schedule - Запланировать несколько постов\n"
        "Формат: Отправьте команду, а затем посты в формате:\n\n"
        "===\n"
        "YYYY-MM-DD HH:MM\n"
        "Текст поста\n"
        "можно с переносами\n"
        "строк\n"
        "===\n"
        "YYYY-MM-DD HH:MM\n"
        "Текст второго поста\n"
        "тоже с переносами\n"
        "===\n\n"
        "/autogen_status - Просмотр статуса автоматической генерации постов\n\n"
        "/generate_post - Сгенерировать тестовый пост с помощью AI\n\n"
        "/autogen_now - Сгенерировать и запланировать пост на ближайшее время\n\n"
        "/publish_now - Немедленно сгенерировать и опубликовать пост в канал"
    )

@dp.message(Command("bulk_schedule"))
async def cmd_bulk_schedule(message: Message):
    user_info = f"user_id={message.from_user.id}, username=@{message.from_user.username}"
    logger.info(f"Получена команда /bulk_schedule от пользователя: {user_info}")
    
    # Проверяем, есть ли текст после команды
    if len(message.text.split('\n')) < 2:
        await message.answer(
            "Пожалуйста, отправьте посты в формате:\n\n"
            "===\n"
            "YYYY-MM-DD HH:MM\n"
            "Текст поста\n"
            "можно с переносами\n"
            "===\n"
            "YYYY-MM-DD HH:MM\n"
            "Текст второго поста"
        )
        return

    # Получаем данные (пропускаем первую строку с командой)
    content = '\n'.join(message.text.split('\n')[1:])
    
    # Разбиваем на отдельные посты по маркеру ===
    posts_raw = [p.strip() for p in content.split('===') if p.strip()]
    
    successful_posts = 0
    failed_posts = 0
    error_messages = []

    for post_number, post_raw in enumerate(posts_raw, 1):
        try:
            # Разбиваем пост на строки
            lines = [line.strip() for line in post_raw.split('\n') if line.strip()]
            
            if len(lines) < 2:
                raise ValueError("Неверный формат: необходимы дата/время и текст поста")
            
            # Первая строка - дата и время
            datetime_str = lines[0]
            # Остальные строки - текст поста
            post_text = '\n'.join(lines[1:])
            
            # Парсим дату и время
            naive_datetime = datetime.strptime(datetime_str.strip(), "%Y-%m-%d %H:%M")
            scheduled_time = tz.localize(naive_datetime)
            
            # Проверяем, что дата в будущем
            if scheduled_time <= datetime.now(tz):
                raise ValueError("Дата должна быть в будущем")
            
            # Сохраняем в базу данных
            db.add_scheduled_post(scheduled_time, post_text)
            
            logger.info(
                f"Запланирован пост (bulk) от {user_info}\n"
                f"Дата публикации: {scheduled_time}\n"
                f"Текст: {post_text[:100]}{'...' if len(post_text) > 100 else ''}"
            )
            
            successful_posts += 1
            
        except Exception as e:
            failed_posts += 1
            error_messages.append(f"Пост {post_number}: {str(e)}")
            logger.error(f"Ошибка при планировании поста (bulk) от {user_info}, пост {post_number}: {str(e)}")
    
    # Формируем отчет
    report = f"Запланировано постов: {successful_posts}\n"
    if failed_posts > 0:
        report += f"Ошибок: {failed_posts}\n\nДетали ошибок:\n" + "\n".join(error_messages)
    
    await message.answer(report)

@dp.message(Command("autogen_status"))
async def cmd_autogen_status(message: Message):
    """Просмотр статуса автоматической генерации постов."""
    user_info = f"user_id={message.from_user.id}, username=@{message.from_user.username}"
    logger.info(f"Получена команда /autogen_status от пользователя: {user_info}")
    
    # Готовим информацию о статусе
    from schedule_config import SCHEDULE_CONFIG
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
    
    # Кэширование
    cache_count = db.count_cached_posts()
    
    # Следующая публикация
    next_time = scheduler.calculate_next_post_time()
    next_time_str = next_time.strftime("%Y-%m-%d %H:%M:%S") if next_time else "Не определено"
    
    # Формируем ответное сообщение
    status_message = (
        f"Статус автоматических публикаций:\n\n"
        f"Состояние: {enabled}\n"
        f"Дни публикаций: {days}\n"
        f"Расписание: {schedule_info}\n"
        f"Кэшировано постов: {cache_count}\n"
        f"Следующая публикация: {next_time_str}\n\n"
        f"Часовой пояс: {TIMEZONE}"
    )
    
    await message.answer(status_message)

@dp.message(Command("generate_post"))
async def cmd_generate_post(message: Message):
    """Генерирует тестовый пост с помощью DeepSeek API."""
    user_info = f"user_id={message.from_user.id}, username=@{message.from_user.username}"
    logger.info(f"Получена команда /generate_post от пользователя: {user_info}")
    
    # Отправляем сообщение о начале генерации
    await message.answer("Генерирую пост с помощью DeepSeek API... Это может занять несколько секунд.")
    
    # Генерируем пост
    post = await scheduler.generate_post()
    
    if post:
        # Добавляем в кэш
        db.add_generated_post_to_cache(post)
        
        await message.answer(
            f"Сгенерированный пост:\n\n"
            f"{post}\n\n"
            f"Пост также добавлен в кэш для будущего использования."
        )
    else:
        await message.answer(
            "Не удалось сгенерировать пост. Пожалуйста, проверьте настройки API DeepSeek "
            "или попробуйте позже."
        )

@dp.message(Command("autogen_now"))
async def cmd_autogen_now(message: Message):
    """Генерирует и планирует пост на ближайшее время."""
    user_info = f"user_id={message.from_user.id}, username=@{message.from_user.username}"
    logger.info(f"Получена команда /autogen_now от пользователя: {user_info}")
    
    # Отправляем сообщение о начале генерации
    await message.answer("Генерирую и планирую пост... Это может занять несколько секунд.")
    
    # Устанавливаем время публикации через 2 минуты
    scheduled_time = datetime.now(tz) + timedelta(minutes=2)
    
    # Пытаемся получить пост из кэша или генерируем новый
    post_text = db.get_unused_cached_post()
    
    if not post_text:
        # Генерируем пост
        post_text = await scheduler.generate_post()
    
    if post_text:
        # Добавляем в расписание
        post_id = db.add_scheduled_post(scheduled_time, post_text, is_auto_generated=True)
        
        await message.answer(
            f"Пост успешно запланирован на {scheduled_time.strftime('%Y-%m-%d %H:%M:%S')}.\n\n"
            f"Предварительный просмотр:\n\n"
            f"{post_text[:200]}{'...' if len(post_text) > 200 else ''}"
        )
    else:
        await message.answer(
            "Не удалось сгенерировать пост. Пожалуйста, проверьте настройки API DeepSeek "
            "или попробуйте позже."
        )

@dp.message(Command("publish_now"))
async def cmd_publish_now(message: Message):
    """Немедленно генерирует и публикует пост в канал."""
    user_info = f"user_id={message.from_user.id}, username=@{message.from_user.username}"
    logger.info(f"Получена команда /publish_now от пользователя: {user_info}")
    
    # Отправляем сообщение о начале генерации
    status_msg = await message.answer("Генерирую и публикую пост в канал... Это может занять несколько секунд.")
    
    try:
        # Пытаемся получить пост из кэша или генерируем новый
        post_text = db.get_unused_cached_post()
        
        if not post_text:
            # Сообщаем о генерации
            await status_msg.edit_text("Кэш пуст. Генерирую новый пост с помощью DeepSeek API...")
            
            # Генерируем новый пост
            post_text = await scheduler.generate_post()
        
        if not post_text:
            await status_msg.edit_text(
                "Не удалось сгенерировать пост. Пожалуйста, проверьте настройки API DeepSeek "
                "или попробуйте позже."
            )
            return
        
        # Публикуем сгенерированный пост напрямую в канал
        await status_msg.edit_text(f"Отправляю пост в канал {CHANNEL_ID}...")
        
        # Отправляем в канал
        sent_message = await bot.send_message(CHANNEL_ID, post_text)
        
        # Сообщаем об успешной отправке
        await status_msg.edit_text(
            f"✅ Пост успешно опубликован в канале {CHANNEL_ID}!\n\n"
            f"Предварительный просмотр:\n\n"
            f"{post_text[:200]}{'...' if len(post_text) > 200 else ''}"
        )
        
        # Записываем в базу как уже отправленный (для истории)
        current_time = datetime.now(tz)
        post_id = db.add_scheduled_post(current_time, post_text, is_auto_generated=True)
        db.mark_post_as_sent(post_id)
        
        logger.info(f"Пост успешно опубликован в канале пользователем {user_info}")
        
    except Exception as e:
        error_msg = f"Произошла ошибка при публикации поста: {str(e)}"
        logger.error(error_msg)
        await status_msg.edit_text(
            f"⚠️ Ошибка при публикации поста: {str(e)}\n"
            f"Пожалуйста, проверьте настройки и права бота в канале."
        )

async def check_scheduled_posts():
    while True:
        try:
            posts = db.get_pending_posts()
            current_time = datetime.now(tz)
            
            for post in posts:
                post_time = datetime.strptime(post[1], "%Y-%m-%d %H:%M:%S")
                post_time = tz.localize(post_time)
                
                if post_time <= current_time:
                    try:
                        logger.info(f"Отправка запланированного поста (id={post[0]}) в канал {CHANNEL_ID}")
                        await bot.send_message(CHANNEL_ID, post[2])
                        db.mark_post_as_sent(post[0])
                        logger.info(f"Пост успешно отправлен (id={post[0]})")
                    except Exception as e:
                        logger.error(f"Ошибка при отправке поста (id={post[0]}): {str(e)}")
        
        except Exception as e:
            logger.error(f"Ошибка в процессе проверки постов: {str(e)}")
        
        await asyncio.sleep(60)

async def main():
    logger.info(f"Бот запущен. Часовой пояс: {TIMEZONE}")
    
    # Запускаем фоновую задачу проверки постов
    asyncio.create_task(check_scheduled_posts())
    
    # Запускаем планировщик
    asyncio.create_task(scheduler.start())
    
    # Запускаем бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main()) 