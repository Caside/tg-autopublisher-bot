import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')
TIMEZONE = os.getenv('TIMEZONE')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')

# Настройки новостной интеграции
NEWS_ENABLED = os.getenv('NEWS_ENABLED', 'true').lower() == 'true'
NEWS_CACHE_HOURS = int(os.getenv('NEWS_CACHE_HOURS', '2'))