import asyncio
import logging
from datetime import datetime, timedelta
import pytz
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.exceptions import TelegramNetworkError
from config import BOT_TOKEN, CHANNEL_ID, TIMEZONE, DEEPSEEK_API_KEY
from deepseek_client import DeepSeekClient
from schedule_config import SCHEDULE_CONFIG
from prompt_template import DEEPSEEK_PROMPT, POST_FORMATS, POST_ENDINGS
import random
import re

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Глобальная переменная для отслеживания последней публикации
last_publication_time = None

# Проверка наличия всех необходимых переменных окружения
required_env_vars = {
    'BOT_TOKEN': BOT_TOKEN,
    'CHANNEL_ID': CHANNEL_ID,
    'TIMEZONE': TIMEZONE,
    'DEEPSEEK_API_KEY': DEEPSEEK_API_KEY
}

missing_vars = [var for var, value in required_env_vars.items() if not value]
if missing_vars:
    error_msg = f"Отсутствуют следующие переменные окружения: {', '.join(missing_vars)}"
    logger.error(error_msg)
    raise ValueError(error_msg)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Получаем часовой пояс
tz = pytz.timezone(TIMEZONE)

# Инициализация клиента DeepSeek
deepseek_client = DeepSeekClient()

def escape_markdown(text):
    """Экранирует все специальные символы MarkdownV2."""
    # Экранируем все специальные символы
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    text = re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)
    return text

def format_post(text):
    """Добавляет форматирование HTML к посту."""
    # Разбиваем текст на строки
    lines = text.split('\n')
    formatted_lines = []
    
    for line in lines:
        # Если строка начинается с эмодзи и содержит заголовок
        if line.strip() and any(emoji in line for emoji in ['🧐', '🤔', '💡', '🎯', '✨']):
            # Выделяем заголовок жирным
            formatted_line = f"<b>{line.strip()}</b>"
        # Если строка содержит список (начинается с ✅ или ❌)
        elif line.strip().startswith(('✅', '❌')):
            # Оставляем как есть
            formatted_line = line
        # Если строка содержит вывод или заключение
        elif line.strip().startswith(('Вывод:', 'Заключение:')):
            # Выделяем жирным
            formatted_line = f"<b>{line.strip()}</b>"
        # Если строка содержит важные термины или ключевые моменты
        elif line.strip().startswith(('*', '_')):
            # Выделяем курсивом
            formatted_line = f"<i>{line.strip().strip('*_')}</i>"
        else:
            formatted_line = line
        
        formatted_lines.append(formatted_line)
    
    return '\n'.join(formatted_lines)

@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_info = f"user_id={message.from_user.id}, username=@{message.from_user.username}"
    logger.debug(f"Получена команда /start от пользователя: {user_info}")
    
    await message.answer(
        "Привет! Я бот для автоматической публикации постов.\n\n"
        "Доступные команды:\n"
        "/publish_now - Немедленно сгенерировать и опубликовать пост\n"
        "/publish_theme [тема] - Сгенерировать и опубликовать пост на указанную тему\n"
        "/debug_prompt [тема] - Показать сгенерированный промпт без публикации\n"
        "/debug_post [тема] - Показать промпт и сгенерированный пост без публикации\n"
        "/schedule_status - Просмотр статуса автоматических публикаций"
    )

@dp.message(Command("publish_now"))
async def cmd_publish_now(message: Message):
    """Немедленно генерирует и публикует пост в канал."""
    user_info = f"user_id={message.from_user.id}, username=@{message.from_user.username}"
    logger.info(f"Запущена публикация поста по команде от пользователя: {user_info}")
    
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
        
        # Добавляем форматирование HTML
        formatted_text = format_post(post_text)
        
        # Отправляем в канал с HTML форматированием
        await bot.send_message(
            CHANNEL_ID, 
            formatted_text,
            parse_mode="HTML"
        )
        
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

@dp.message(Command("publish_theme"))
async def cmd_publish_theme(message: Message):
    """Генерирует и публикует пост на указанную тему."""
    user_info = f"user_id={message.from_user.id}, username=@{message.from_user.username}"
    logger.info(f"Запущена публикация поста с темой по команде от пользователя: {user_info}")
    
    # Получаем тему из аргументов команды
    theme = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else None
    
    if not theme:
        await message.answer(
            "Пожалуйста, укажите тему для поста после команды.\n"
            "Пример: /publish_theme психическое благополучие"
        )
        return
    
    # Отправляем сообщение о начале генерации
    status_msg = await message.answer(f"Генерирую и публикую пост на тему '{theme}' в канал... Это может занять несколько секунд.")
    
    try:
        # Генерируем новый пост с указанной темой
        post_text = await deepseek_client.generate_post(theme=theme)
        
        if not post_text:
            await status_msg.edit_text(
                "Не удалось сгенерировать пост. Пожалуйста, проверьте настройки API DeepSeek "
                "или попробуйте позже."
            )
            return
        
        # Публикуем сгенерированный пост напрямую в канал
        await status_msg.edit_text(f"Отправляю пост в канал {CHANNEL_ID}...")
        
        # Добавляем форматирование HTML
        formatted_text = format_post(post_text)
        
        # Отправляем в канал с HTML форматированием
        await bot.send_message(
            CHANNEL_ID, 
            formatted_text,
            parse_mode="HTML"
        )
        
        # Сообщаем об успешной отправке
        await status_msg.edit_text(
            f"✅ Пост на тему '{theme}' успешно опубликован в канале {CHANNEL_ID}!\n\n"
            f"Предварительный просмотр:\n\n"
            f"{post_text[:200]}{'...' if len(post_text) > 200 else ''}"
        )
        
        logger.info(f"Пост на тему '{theme}' успешно опубликован в канале пользователем {user_info}")
        
    except Exception as e:
        error_msg = f"Произошла ошибка при публикации поста: {str(e)}"
        logger.error(error_msg)
        await status_msg.edit_text(
            f"⚠️ Ошибка при публикации поста: {str(e)}\n"
            f"Пожалуйста, проверьте настройки и права бота в канале."
        )

@dp.message(Command("debug_prompt"))
async def cmd_debug_prompt(message: Message):
    """Показывает сгенерированный промпт без публикации поста."""
    user_info = f"user_id={message.from_user.id}, username=@{message.from_user.username}"
    logger.info(f"Запущена отладка промпта по команде от пользователя: {user_info}")
    
    # Получаем тему из аргументов команды
    theme = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else None
    
    if not theme:
        await message.answer(
            "Пожалуйста, укажите тему для промпта после команды.\n"
            "Пример: /debug_prompt психическое благополучие"
        )
        return
    
    try:
        # Генерируем промпт с указанной темой
        format_type = random.choice(POST_FORMATS)
        ending = random.choice(POST_ENDINGS)
        
        # Формируем промпт
        prompt = DEEPSEEK_PROMPT.format(
            theme=theme,
            format=format_type,
            ending=ending
        )
        
        # Отправляем промпт в чат
        await message.answer(
            f"🔍 Сгенерированный промпт для темы '{theme}':\n\n"
            f"Формат: {format_type}\n"
            f"Завершение: {ending}\n\n"
            f"Промпт:\n{prompt}"
        )
        
        logger.info(f"Промпт успешно сгенерирован для темы '{theme}'")
        
    except Exception as e:
        error_msg = f"Произошла ошибка при генерации промпта: {str(e)}"
        logger.error(error_msg)
        await message.answer(
            f"⚠️ Ошибка при генерации промпта: {str(e)}"
        )

@dp.message(Command("debug_post"))
async def cmd_debug_post(message: Message):
    """Показывает промпт и сгенерированный пост без публикации."""
    user_info = f"user_id={message.from_user.id}, username=@{message.from_user.username}"
    logger.info(f"Запущена отладка поста по команде от пользователя: {user_info}")
    
    # Получаем тему из аргументов команды
    theme = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else None
    
    if not theme:
        await message.answer(
            "Пожалуйста, укажите тему для поста после команды.\n"
            "Пример: /debug_post когнитивные искажения"
        )
        return
    
    # Отправляем сообщение о начале генерации
    status_msg = await message.answer(f"Генерирую пост на тему '{theme}'... Это может занять несколько секунд.")
    
    try:
        # Генерируем промпт с указанной темой
        format_type = random.choice(POST_FORMATS)
        ending = random.choice(POST_ENDINGS)
        
        # Формируем промпт
        prompt = DEEPSEEK_PROMPT.format(
            theme=theme,
            format=format_type,
            ending=ending
        )
        
        # Отправляем промпт в чат
        await status_msg.edit_text(
            f"🔍 Сгенерированный промпт для темы '{theme}':\n\n"
            f"Формат: {format_type}\n"
            f"Завершение: {ending}\n\n"
            f"Промпт:\n{prompt}\n\n"
            f"Генерирую пост..."
        )
        
        # Генерируем пост с помощью DeepSeek
        post_text = await deepseek_client.generate_post(theme=theme)
        
        if not post_text:
            await status_msg.edit_text(
                "Не удалось сгенерировать пост. Пожалуйста, проверьте настройки API DeepSeek "
                "или попробуйте позже."
            )
            return
        
        # Добавляем форматирование HTML
        formatted_text = format_post(post_text)
        
        # Отправляем результат в чат с HTML форматированием
        await message.answer(
            f"✅ Сгенерированный пост:\n\n"
            f"{formatted_text}\n\n"
            f"Длина поста: {len(post_text)} символов",
            parse_mode="HTML"
        )
        
        logger.info(f"Пост успешно сгенерирован для темы '{theme}'")
        
    except Exception as e:
        error_msg = f"Произошла ошибка при генерации поста: {str(e)}"
        logger.error(error_msg)
        await status_msg.edit_text(
            f"⚠️ Ошибка при генерации поста: {str(e)}"
        )

@dp.message(Command("schedule_status"))
async def cmd_schedule_status(message: Message):
    """Просмотр статуса автоматических публикаций."""
    user_info = f"user_id={message.from_user.id}, username=@{message.from_user.username}"
    logger.debug(f"Получена команда /schedule_status от пользователя: {user_info}")
    
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
    global last_publication_time
    
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
                            # Проверяем, не публиковали ли мы пост в последние 5 минут
                            if (last_publication_time is None or 
                                (current_time - last_publication_time).total_seconds() > 300):
                                logger.info("Найдено время для публикации по расписанию")
                                await publish_scheduled_post()
                                last_publication_time = current_time
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
                        
                        # Проверяем, находится ли текущее время в пределах 1 минуты от времени публикации
                        interval = SCHEDULE_CONFIG["interval_minutes"]
                        if abs(minutes_since_start % interval) < 1:
                            # Проверяем, не публиковали ли мы пост в последние 5 минут
                            if (last_publication_time is None or 
                                (current_time - last_publication_time).total_seconds() > 300):
                                logger.info("Найдено время для публикации по интервалу")
                                await publish_scheduled_post()
                                last_publication_time = current_time
            
            # Ждем 30 секунд перед следующей проверкой
            await asyncio.sleep(30)
            
        except Exception as e:
            logger.error(f"Ошибка в планировщике: {str(e)}")
            await asyncio.sleep(30)

async def publish_scheduled_post():
    """Публикует пост по расписанию."""
    max_retries = 3
    retry_delay = 5  # секунды
    
    for attempt in range(max_retries):
        try:
            logger.info("Генерация и публикация поста по расписанию")
            
            # Генерируем новый пост
            post_text = await deepseek_client.generate_post()
            
            if post_text:
                # Добавляем форматирование HTML
                formatted_text = format_post(post_text)
                
                # Публикуем в канал с HTML форматированием
                await bot.send_message(
                    CHANNEL_ID, 
                    formatted_text,
                    parse_mode="HTML"
                )
                logger.info("Пост успешно опубликован по расписанию")
                return
            else:
                logger.error("Не удалось сгенерировать пост для публикации по расписанию")
                return
                
        except TelegramNetworkError as e:
            logger.error(f"Ошибка сети при публикации поста по расписанию (попытка {attempt + 1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                continue
            else:
                logger.error("Превышено максимальное количество попыток публикации поста")
                return
                
        except Exception as e:
            logger.error(f"Ошибка при публикации поста по расписанию: {str(e)}")
            return

async def main():
    logger.info(f"Бот запущен. Часовой пояс: {TIMEZONE}")
    
    # Запускаем планировщик публикаций
    asyncio.create_task(schedule_posts())
    
    # Запускаем бота с обработкой ошибок
    while True:
        try:
            await dp.start_polling(bot)
        except TelegramNetworkError as e:
            logger.error(f"Ошибка подключения к Telegram API: {str(e)}")
            logger.info("Повторная попытка подключения через 5 секунд...")
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"Неожиданная ошибка: {str(e)}")
            logger.info("Повторная попытка подключения через 5 секунд...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
