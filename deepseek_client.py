"""
Клиент для работы с DeepSeek API для генерации текста.
"""

import requests
import json
import logging
import random
from config import DEEPSEEK_API_KEY
from prompt_template import DEEPSEEK_PROMPT, DEEPSEEK_API_PARAMS, POST_THEMES, POST_FORMATS, POST_ENDINGS

# Настройка логирования
logger = logging.getLogger('deepseek_client')
logger.setLevel(logging.INFO)

class DeepSeekClient:
    """Клиент для работы с DeepSeek API."""
    
    def __init__(self):
        self.api_key = DEEPSEEK_API_KEY
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        self.prompt_template = DEEPSEEK_PROMPT
        self.api_params = DEEPSEEK_API_PARAMS.copy()
        
        if not self.api_key or self.api_key == "your_deepseek_api_key_here":
            logger.error("DeepSeek API ключ не настроен. Пожалуйста, добавьте его в .env файл.")
            raise ValueError("DeepSeek API ключ не настроен")
    
    async def generate_post(self):
        """Генерирует пост, используя DeepSeek API."""
        try:
            # Выбираем случайные параметры для поста
            theme = random.choice(POST_THEMES)
            format_type = random.choice(POST_FORMATS)
            ending = random.choice(POST_ENDINGS)
            
            # Заполняем шаблон промпта
            prompt = self.prompt_template.format(
                theme=theme,
                format=format_type,
                ending=ending
            )
            
            # Подготавливаем запрос
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            payload = {
                "messages": [{"role": "user", "content": prompt}],
                **self.api_params
            }
            
            # Отправляем запрос
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                post_text = result["choices"][0]["message"]["content"].strip()
                logger.info("Пост успешно сгенерирован")
                return post_text
            else:
                logger.error(f"Ошибка API: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка при генерации поста: {str(e)}")
            return None
