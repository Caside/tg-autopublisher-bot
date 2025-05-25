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
import json

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
        # Генерируем новый пост с использованием метагенерации
        post_text = await deepseek_client.generate_post(use_meta_generation=True)
        
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
        # Генерируем новый пост с указанной темой с использованием метагенерации
        post_text = await deepseek_client.generate_post(theme=theme, use_meta_generation=True)
        
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
async def debug_prompt(message: Message):
    """Отладочная команда для проверки генерации промпта."""
    try:
        logger.info(f"Запущена отладка промпта по команде от пользователя: user_id={message.from_user.id}, username=@{message.from_user.username}")
        
        # Получаем только JSON-ответ от API
        meta_response = await deepseek_client.generate_meta_prompt()
        
        # Отправляем ответ
        await message.answer(f"🔧 Ответ API:\n{meta_response}")
        
        logger.info(f"Промпт успешно сгенерирован в режиме отладки для пользователя user_id={message.from_user.id}, username=@{message.from_user.username}")
        
    except Exception as e:
        error_message = f"⚠️ Ошибка при генерации промпта: {str(e)}"
        logger.error(f"{error_message} для пользователя user_id={message.from_user.id}, username=@{message.from_user.username}")
        await message.answer(error_message)

@dp.message(Command("debug_post"))
async def cmd_debug_post(message: Message):
    """Показывает сгенерированный мета-промпт, финальный промпт и пост без публикации."""
    user_info = f"user_id={message.from_user.id}, username=@{message.from_user.username}"
    logger.info(f"Запущена отладка поста по команде от пользователя: {user_info}")
    
    # Получаем тему из аргументов команды
    theme = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else None
    
    status_msg = await message.answer(
        f"Генерирую мета-промпт и пост{f' для темы «{theme}»' if theme else ''}... Это может занять несколько секунд."
    )
    
    try:
        # Генерируем мета-промпт
        meta_prompt, meta_response, final_prompt = await deepseek_client.generate_meta_prompt(theme)
        
        # Красиво форматируем JSON для отображения
        try:
            # Очищаем ответ от возможных блоков кода
            cleaned_response = deepseek_client._clean_json_response(meta_response)
            json_data = json.loads(cleaned_response)
            formatted_json = json.dumps(json_data, ensure_ascii=False, indent=2)
        except:
            formatted_json = meta_response
        
        # Генерируем пост с использованием метагенерации
        post_text = await deepseek_client.generate_post(theme=theme, use_meta_generation=True)
        
        if not post_text:
            await status_msg.edit_text(
                "Не удалось сгенерировать пост. Пожалуйста, проверьте настройки API DeepSeek "
                "или попробуйте позже."
            )
            return
        
        # Отправляем мета-промпт
        await status_msg.edit_text("Результаты генерации:")
        await message.answer(f"🔍 Мета-промпт:\n```\n{meta_prompt}\n```")
        
        # Отправляем ответ API
        await message.answer(f"🔧 Ответ API:\n```json\n{formatted_json}\n```")
        
        # Отправляем финальный промпт, если он есть
        if final_prompt:
            await message.answer(f"📝 Финальный промпт:\n```\n{final_prompt}\n```")
        
        # Форматируем пост для HTML
        formatted_text = format_post(post_text)
        
        # Отправляем сгенерированный пост
        await message.answer(f"📊 Сгенерированный пост:\n\n{post_text}")
        
        # Отправляем пост с HTML-форматированием
        await message.answer(
            f"📊 С HTML-форматированием:\n\n{formatted_text}",
            parse_mode="HTML"
        )
        
        logger.info(f"Пост успешно сгенерирован в режиме отладки для пользователя {user_info}")
        
    except Exception as e:
        error_msg = f"Произошла ошибка при генерации поста: {str(e)}"
        logger.error(error_msg)
        await status_msg.edit_text(
            f"⚠️ Ошибка при генерации поста: {str(e)}\n"
            f"Пожалуйста, проверьте настройки API DeepSeek."
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
    """Публикует запланированный пост в канал."""
    global last_publication_time
    
    logger.info(f"Публикация запланированного поста...")
    
    try:
        # Генерируем новый пост с использованием метагенерации
        post_text = await deepseek_client.generate_post(use_meta_generation=True)
        
        if not post_text:
            logger.error("Не удалось сгенерировать пост для запланированной публикации")
            return
        
        # Добавляем форматирование HTML
        formatted_text = format_post(post_text)
        
        # Отправляем в канал с HTML форматированием
        await bot.send_message(
            CHANNEL_ID, 
            formatted_text,
            parse_mode="HTML"
        )
        
        # Обновляем время последней публикации
        last_publication_time = datetime.now(tz)
        
        logger.info(f"Запланированный пост успешно опубликован в канале {CHANNEL_ID}")
        
    except TelegramNetworkError as e:
        logger.error(f"Ошибка сети Telegram при публикации запланированного поста: {str(e)}")
    except Exception as e:
        logger.error(f"Ошибка при публикации запланированного поста: {str(e)}")

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
