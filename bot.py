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
from prompt_template import DEEPSEEK_PROMPT
from mode_config import (
    get_current_mode_config, 
    get_available_modes, 
    get_mode_info, 
    set_mode,
    PostMode
)
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
        "👋 Привет! Я бот для автоматической публикации постов.\n\n"
        "Используйте команду /help для просмотра списка всех доступных команд.\n\n"
        "Бот настроен на автоматическую публикацию постов по расписанию. "
        "Вы можете проверить текущие настройки расписания с помощью команды /schedule_status."
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
        result = await deepseek_client.generate_post()
        if len(result) == 3:
            post_text, prompt, keywords_list = result
        else:
            # Обратная совместимость со старым форматом
            post_text, prompt = result[:2]
            keywords_list = []
        
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
        sent_message = await bot.send_message(
            chat_id=CHANNEL_ID,
            text=formatted_text,
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

@dp.message(Command("publish_custom"))
async def cmd_publish_custom(message: Message):
    """Генерирует и публикует пост (дублирует функцию publish_now)."""
    user_info = f"user_id={message.from_user.id}, username=@{message.from_user.username}"
    logger.info(f"Запущена дополнительная публикация поста по команде от пользователя: {user_info}")
    
    # Отправляем сообщение о начале генерации
    status_msg = await message.answer(f"Генерирую и публикую пост в канал... Это может занять несколько секунд.")
    
    try:
        # Генерируем новый пост
        result = await deepseek_client.generate_post()
        if len(result) == 3:
            post_text, prompt, keywords_list = result
        else:
            # Обратная совместимость со старым форматом
            post_text, prompt = result[:2]
            keywords_list = []
        
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
        sent_message = await bot.send_message(
            chat_id=CHANNEL_ID,
            text=formatted_text,
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

@dp.message(Command("debug_prompt"))
async def cmd_debug_prompt(message: Message):
    """Показывает сгенерированный промпт без публикации поста."""
    user_info = f"user_id={message.from_user.id}, username=@{message.from_user.username}"
    logger.info(f"Запущена отладка промпта по команде от пользователя: {user_info}")
    
    # Отправляем сообщение о начале генерации
    status_msg = await message.answer("Генерирую промпт...")
    
    try:
        # Генерируем промпт
        prompt, keywords_list = deepseek_client.generate_prompt()
        
        # Формируем строку с ключевыми словами
        keywords_string = ", ".join(keywords_list) if keywords_list else "не загружены"
        
        # Отправляем промпт в чат
        await status_msg.edit_text(
            f"🔍 Сгенерированный промпт:\n\n"
            f"Ключевые слова: {keywords_string}\n\n"
            f"Промпт:\n{prompt}"
        )
        
        logger.info(f"Промпт успешно сгенерирован")
        
    except Exception as e:
        error_msg = f"Произошла ошибка при генерации промпта: {str(e)}"
        logger.error(error_msg)
        await status_msg.edit_text(
            f"⚠️ Ошибка при генерации промпта: {str(e)}"
        )

@dp.message(Command("debug_post"))
async def cmd_debug_post(message: Message):
    """Показывает промпт и сгенерированный пост без публикации."""
    user_info = f"user_id={message.from_user.id}, username=@{message.from_user.username}"
    logger.info(f"Запущена отладка поста по команде от пользователя: {user_info}")
    
    # Отправляем сообщение о начале генерации
    status_msg = await message.answer("Генерирую пост... Это может занять несколько секунд.")
    logger.info(f"DEBUG: Начальное сообщение отправлено")
    
    try:
        logger.info(f"DEBUG: Начинаем генерацию поста")
        # Генерируем пост с помощью DeepSeek
        result = await deepseek_client.generate_post()
        logger.info(f"DEBUG: Пост сгенерирован, результат: {type(result)}, длина: {len(result) if result else 'None'}")
        
        if len(result) == 3:
            post_text, prompt, keywords_list = result
            logger.info(f"DEBUG: Распаковали результат в 3 переменные")
        else:
            # Обратная совместимость со старым форматом
            post_text, prompt = result[:2]
            keywords_list = []
            logger.info(f"DEBUG: Распаковали результат в 2 переменные (старый формат)")
        
        logger.info(f"DEBUG: Длина сгенерированного поста: {len(post_text) if post_text else 'None'}")
        logger.info(f"DEBUG: Длина промпта: {len(prompt) if prompt else 'None'}")
        
        if post_text:
            logger.info(f"DEBUG: Первые 200 символов поста: {post_text[:200]}")
            logger.info(f"DEBUG: Последние 100 символов поста: {post_text[-100:]}")
            
            # Проверяем HTML теги в посте
            import re
            open_tags = re.findall(r'<[^/][^>]*>', post_text)
            close_tags = re.findall(r'</[^>]*>', post_text)
            logger.info(f"DEBUG: Открывающие теги в посте: {open_tags}")
            logger.info(f"DEBUG: Закрывающие теги в посте: {close_tags}")
        
        if not post_text:
            logger.info(f"DEBUG: Пост пустой, отправляем сообщение об ошибке")
            await status_msg.edit_text(
                "Не удалось сгенерировать пост. Пожалуйста, проверьте настройки API DeepSeek "
                "или попробуйте позже."
            )
            return
        
        logger.info(f"DEBUG: Начинаем обработку ключевых слов")
        # Формируем строку с ключевыми словами
        keywords_string = ", ".join(keywords_list) if keywords_list else "не удалось определить"
        logger.info(f"DEBUG: Ключевые слова: {keywords_string}")
        
        # Экранируем HTML в промпте для безопасного отображения
        import html
        escaped_prompt = html.escape(prompt)
        logger.info(f"DEBUG: Промпт экранирован, длина: {len(escaped_prompt)}")
        
        # Пробуем также экранировать HTML в посте для тестирования
        escaped_post = html.escape(post_text)
        logger.info(f"DEBUG: Пост экранирован, длина: {len(escaped_post)}")
        logger.info(f"DEBUG: Первые 200 символов экранированного поста: {escaped_post[:200]}")
        
        # Используем экранированный пост для отладки
        formatted_text = escaped_post
        
        total_length = len(escaped_prompt) + len(formatted_text) + 300
        logger.info(f"DEBUG: Готовимся отправить сообщение примерной длиной {total_length} символов")
        
        # Отправляем результат в чат с HTML форматированием
        logger.info(f"DEBUG: Отправляем финальное сообщение...")
        await message.answer(
            f"✅ <b>Сгенерированный пост:</b>\n\n"
            f"<b>Параметры генерации:</b>\n"
            f"• Ключевые слова: {keywords_string}\n\n"
            f"<b>Промпт:</b>\n<code>{escaped_prompt}</code>\n\n"
            f"<b>Результат (экранированный):</b>\n<code>{formatted_text}</code>\n\n"
            f"📊 Длина поста: {len(post_text)} символов",
            parse_mode="HTML"
        )
        
        logger.info(f"DEBUG: Сообщение отправлено успешно")
        
    except Exception as e:
        error_msg = f"Произошла ошибка при генерации поста: {str(e)}"
        logger.error(error_msg)
        logger.error(f"DEBUG: Полная ошибка: {repr(e)}")
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

@dp.message(Command("mode_info"))
async def cmd_mode_info(message: Message):
    """Показывает информацию о текущем режиме работы."""
    user_info = f"user_id={message.from_user.id}, username=@{message.from_user.username}"
    logger.debug(f"Получена команда /mode_info от пользователя: {user_info}")
    
    current_mode = get_mode_info()
    
    mode_text = (
        f"🎭 <b>Текущий режим работы:</b>\n\n"
        f"<b>{current_mode['name']}</b>\n"
        f"{current_mode['description']}\n\n"
        f"Режим: <code>{current_mode['mode']}</code>"
    )
    
    await message.answer(mode_text, parse_mode="HTML")

@dp.message(Command("set_mode"))
async def cmd_set_mode(message: Message):
    """Переключает режим работы бота."""
    user_info = f"user_id={message.from_user.id}, username=@{message.from_user.username}"
    logger.info(f"Получена команда /set_mode от пользователя: {user_info}")
    
    # Получаем режим из аргументов команды
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "Укажите режим работы:\n"
            "• <code>classic</code> - классические посты\n\n"
            "Пример: /set_mode classic",
            parse_mode="HTML"
        )
        return
    
    new_mode = args[1].lower()
    
    if set_mode(new_mode):
        mode_info = get_mode_info(new_mode)
        await message.answer(
            f"✅ Режим успешно подтвержден!\n\n"
            f"<b>{mode_info['name']}</b>\n"
            f"{mode_info['description']}",
            parse_mode="HTML"
        )
        logger.info(f"Режим подтвержден как {new_mode} пользователем {user_info}")
    else:
        await message.answer(
            f"❌ Неизвестный режим: {new_mode}\n\n"
            "Доступный режим: classic"
        )

@dp.message(Command("keywords"))
async def cmd_keywords(message: Message):
    """Показывает случайно выбранные ключевые слова."""
    user_info = f"user_id={message.from_user.id}, username=@{message.from_user.username}"
    logger.debug(f"Получена команда /keywords от пользователя: {user_info}")
    
    try:
        # Генерируем случайные ключевые слова
        keywords_list = deepseek_client._get_random_keywords()
        
        if keywords_list:
            keywords_text = (
                f"🎲 <b>Случайные ключевые слова:</b>\n\n"
                f"• {keywords_list[0]}\n"
                f"• {keywords_list[1]}\n"
                f"• {keywords_list[2]}\n\n"
                f"<i>Эти слова используются для вдохновения при генерации постов</i>"
            )
        else:
            keywords_text = "❌ Ключевые слова не загружены"
        
        await message.answer(keywords_text, parse_mode="HTML")
        
    except Exception as e:
        await message.answer(f"❌ Ошибка при получении ключевых слов: {str(e)}")

@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Показывает список всех доступных команд."""
    user_info = f"user_id={message.from_user.id}, username=@{message.from_user.username}"
    logger.debug(f"Получена команда /help от пользователя: {user_info}")
    
    help_text = (
        "🤖 <b>Список доступных команд:</b>\n\n"
        "<b>Основные:</b>\n"
        "/start - Начать работу с ботом\n"
        "/help - Показать это сообщение\n"
        "/publish_now - Немедленно сгенерировать и опубликовать пост\n"
        "/publish_custom - Дополнительная команда для публикации поста\n"
        "/schedule_status - Просмотр статуса автоматических публикаций\n\n"
        
        "<b>Режим работы:</b>\n"
        "/mode_info - Информация о текущем режиме\n"
        "/set_mode classic - Подтвердить классический режим\n\n"
        
        "<b>Отладка:</b>\n"
        "/debug_prompt - Показать сгенерированный промпт\n"
        "/debug_post - Показать промпт и пост\n"
        "/keywords - Показать случайные ключевые слова\n\n"
        
        "<i>Посты генерируются на основе случайных форматов, завершений и 3 ключевых слов для вдохновения!</i>"
    )
    
    await message.answer(help_text, parse_mode="HTML")

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
            result = await deepseek_client.generate_post()
            if len(result) == 3:
                post_text, prompt, keywords_list = result
            else:
                # Обратная совместимость со старым форматом
                post_text, prompt = result[:2]
                keywords_list = []
            
            if post_text:
                # Добавляем форматирование HTML
                formatted_text = format_post(post_text)
                
                # Отправляем в канал с HTML форматированием
                sent_message = await bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=formatted_text,
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
