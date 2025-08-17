"""
Клиент для работы с DeepSeek API для генерации текста.
Поддерживает только классические посты с системой случайных ключевых слов.
"""

import requests
import json
import logging
import random
import os

from config import DEEPSEEK_API_KEY
from prompt_template import (
    DEEPSEEK_PROMPT, 
    DEEPSEEK_API_PARAMS, 
    DEEPSEEK_API_PARAM_RANGES
)

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
        

        
        # Загружаем ключевые слова
        self.keywords = self._load_keywords()
        
        if not self.api_key or self.api_key == "your_deepseek_api_key_here":
            logger.error("DeepSeek API ключ не настроен. Пожалуйста, добавьте его в .env файл.")
            raise ValueError("DeepSeek API ключ не настроен")
    
    def _load_keywords(self):
        """Загружает ключевые слова из JSON файла."""
        try:
            keywords_file = os.path.join(os.path.dirname(__file__), 'keywords.json')
            with open(keywords_file, 'r', encoding='utf-8') as f:
                keywords = json.load(f)
            logger.info(f"Загружено {len(keywords)} ключевых слов")
            return keywords
        except FileNotFoundError:
            logger.error("Файл keywords.json не найден")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка при чтении keywords.json: {e}")
            return {}
    
    def _get_random_keywords(self):
        """Генерирует 3 случайных ключевых слова."""
        if not self.keywords:
            logger.warning("Ключевые слова не загружены")
            return []
        
        # Генерируем 3 случайных числа от 1 до 100
        random_numbers = [random.randint(1, 100) for _ in range(3)]
        
        # Получаем соответствующие ключевые слова
        selected_keywords = []
        for num in random_numbers:
            keyword = self.keywords.get(str(num), f"ключевое_слово_{num}")
            selected_keywords.append(keyword)
        
        logger.info(f"Выбраны ключевые слова для чисел {random_numbers}: {selected_keywords}")
        return selected_keywords
    

    
    def _get_random_api_params(self):
        """Генерирует случайные параметры API из заданных диапазонов."""
        params = self.api_params.copy()
        for param, (min_val, max_val) in DEEPSEEK_API_PARAM_RANGES.items():
            params[param] = round(random.uniform(min_val, max_val), 2)
        return params
    
    def generate_prompt(self):
        """Генерирует промпт с ключевыми словами."""
        # Получаем случайные ключевые слова
        keywords_list = self._get_random_keywords()
        keywords_string = ", ".join(keywords_list)
        
        # Заполняем шаблон промпта
        prompt = self.prompt_template.format(keywords=keywords_string)
        
        return prompt, keywords_list
    
    async def generate_post(self):
        """Генерирует классический пост, используя DeepSeek API."""
        try:
            # Генерируем промпт
            prompt, keywords_list = self.generate_prompt()
            
            # Подготавливаем запрос с случайными параметрами
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            payload = {
                "messages": [{"role": "user", "content": prompt}],
                **self._get_random_api_params()
            }
            
            # Отправляем запрос
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                post_text = result["choices"][0]["message"]["content"].strip()
                logger.info(f"Классический пост успешно сгенерирован с ключевыми словами: {keywords_list}")
                return post_text, prompt, keywords_list
            else:
                logger.error(f"Ошибка API: {response.status_code} - {response.text}")
                return None, None, None
                
        except Exception as e:
            logger.error(f"Ошибка при генерации поста: {str(e)}")
            return None, None, None
