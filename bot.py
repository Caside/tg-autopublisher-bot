import asyncio
from datetime import datetime
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

@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_info = f"user_id={message.from_user.id}, username=@{message.from_user.username}"
    logger.info(f"Получена команда /start от пользователя: {user_info}")
    
    await message.answer(
        "Привет! Я бот для отложенной публикации постов.\n"
        "Используйте команду /schedule чтобы запланировать пост.\n"
        "Формат: /schedule YYYY-MM-DD HH:MM текст поста"
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
        "Пример:\n"
        "===\n"
        "2024-03-20 15:30\n"
        "Первый пост\n"
        "с переносом строки\n"
        "===\n"
        "2024-03-21 12:00\n"
        "Второй пост\n"
        "тоже с переносом"
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
    # Запускаем бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main()) 