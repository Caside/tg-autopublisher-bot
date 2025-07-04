"""
Клиент для работы с DeepSeek API для генерации текста.
Поддерживает как классические посты, так и диалоги мыслителей.
"""

import requests
import json
import logging
import random
from collections import deque
from config import DEEPSEEK_API_KEY
from prompt_template import (
    DEEPSEEK_PROMPT, 
    DEEPSEEK_API_PARAMS, 
    DEEPSEEK_API_PARAM_RANGES,
    POST_THEMES, 
    POST_FORMATS, 
    POST_ENDINGS,
    generate_random_seed
)
from mode_config import is_dialogue_mode, get_current_mode_config

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
        
        # История последних использованных элементов
        self.recent_themes = deque(maxlen=3)
        self.recent_formats = deque(maxlen=3)
        self.recent_endings = deque(maxlen=3)
        
        # Система диалогов (инициализируется позже, чтобы избежать циклического импорта)
        self._dialogue_system = None
        
        if not self.api_key or self.api_key == "your_deepseek_api_key_here":
            logger.error("DeepSeek API ключ не настроен. Пожалуйста, добавьте его в .env файл.")
            raise ValueError("DeepSeek API ключ не настроен")
    
    def _get_random_without_recent(self, items, recent_items):
        """Выбирает случайный элемент, исключая недавно использованные."""
        available_items = [item for item in items if item not in recent_items]
        if not available_items:  # Если все элементы были использованы недавно
            available_items = items  # Используем все элементы
        return random.choice(available_items)
    
    def _get_random_api_params(self):
        """Генерирует случайные параметры API из заданных диапазонов."""
        params = self.api_params.copy()
        for param, (min_val, max_val) in DEEPSEEK_API_PARAM_RANGES.items():
            params[param] = round(random.uniform(min_val, max_val), 2)
        return params
    
    def get_dialogue_system(self):
        """Получает или создает систему диалогов."""
        if self._dialogue_system is None:
            from dialogue_system import DialogueSystem
            self._dialogue_system = DialogueSystem(self)
        return self._dialogue_system
    
    def generate_prompt(self, theme=None):
        """Генерирует промпт с случайными параметрами."""
        # Выбираем случайные параметры для поста, избегая недавних повторов
        if theme:
            selected_theme = theme
        else:
            selected_theme = self._get_random_without_recent(POST_THEMES, self.recent_themes)
        
        selected_format = self._get_random_without_recent(POST_FORMATS, self.recent_formats)
        selected_ending = self._get_random_without_recent(POST_ENDINGS, self.recent_endings)
        random_seed = generate_random_seed()
        
        # Обновляем историю
        self.recent_themes.append(selected_theme)
        self.recent_formats.append(selected_format)
        self.recent_endings.append(selected_ending)
        
        # Заполняем шаблон промпта
        prompt = self.prompt_template.format(
            theme=selected_theme,
            format=selected_format,
            ending=selected_ending,
            random_seed=random_seed
        )
        
        return prompt, selected_theme, selected_format, selected_ending, random_seed
    
    async def generate_post(self, theme=None):
        """Генерирует пост, используя DeepSeek API. Поддерживает классические посты и диалоги."""
        try:
            # Проверяем, какой режим активен
            if is_dialogue_mode():
                return await self._generate_dialogue_post(theme)
            else:
                return await self._generate_classic_post(theme)
                
        except Exception as e:
            logger.error(f"Ошибка при генерации поста: {str(e)}")
            return None, None, None, None, None, None
    
    async def _generate_classic_post(self, theme=None):
        """Генерирует классический пост."""
        try:
            # Генерируем промпт
            prompt, selected_theme, selected_format, selected_ending, random_seed = self.generate_prompt(theme)
            
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
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                post_text = result["choices"][0]["message"]["content"].strip()
                logger.info("Классический пост успешно сгенерирован")
                return post_text, prompt, selected_theme, selected_format, selected_ending, random_seed
            else:
                logger.error(f"Ошибка API: {response.status_code} - {response.text}")
                return None, None, None, None, None, None
                
        except Exception as e:
            logger.error(f"Ошибка при генерации классического поста: {str(e)}")
            return None, None, None, None, None, None
    
    async def _generate_dialogue_post(self, theme=None):
        """Генерирует пост в формате диалога мыслителей."""
        try:
            dialogue_system = self.get_dialogue_system()
            dialogue = await dialogue_system.create_full_dialogue(theme)
            
            if dialogue:
                post_text = dialogue_system.format_dialogue_for_telegram(dialogue)
                
                # Формируем информацию для совместимости с классическим форматом
                prompt = f"Диалог между {dialogue['participants']} на тему: {dialogue['theme']}"
                selected_theme = dialogue['theme']
                selected_format = "диалог мыслителей"
                selected_ending = "философская дискуссия"
                random_seed = random.randint(1000, 9999)
                
                logger.info(f"Диалог успешно сгенерирован между {dialogue['participants']}")
                return post_text, prompt, selected_theme, selected_format, selected_ending, random_seed
            else:
                logger.error("Не удалось создать диалог")
                return None, None, None, None, None, None
                
        except Exception as e:
            logger.error(f"Ошибка при генерации диалога: {str(e)}")
            return None, None, None, None, None, None
