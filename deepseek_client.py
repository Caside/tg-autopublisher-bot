"""
Клиент для работы с DeepSeek API для генерации текста.
Поддерживает автономную генерацию постов с использованием метагенерации.
"""

import requests
import json
import logging
import random
import asyncio
import time
from config import DEEPSEEK_API_KEY
from prompt_template import (
    DEEPSEEK_PROMPT, DEEPSEEK_API_PARAMS, POST_THEMES, POST_FORMATS, POST_ENDINGS,
    META_GENERATION_PROMPT, POST_GENERATION_PROMPT
)
from context_manager import ContextManager

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
        self.context_manager = ContextManager()
        
        if not self.api_key or self.api_key == "your_deepseek_api_key_here":
            logger.error("DeepSeek API ключ не настроен. Пожалуйста, добавьте его в .env файл.")
            raise ValueError("DeepSeek API ключ не настроен")
    
    def _select_theme(self):
        """
        Выбирает тему на основе текущего времени и контекста.
        
        Returns:
            str: Выбранная тема
        """
        # Получаем текущее время в миллисекундах
        current_time_ms = int(time.time() * 1000)
        
        # Получаем контекст для анализа использованных тем
        context = self.context_manager.get_context()
        used_themes = [gen.get('theme') for gen in context.get('last_generations', [])]
        
        # Выбираем тему, избегая недавно использованных
        available_themes = [theme for theme in POST_THEMES if theme not in used_themes]
        
        if not available_themes:
            # Если все темы были использованы, используем все темы
            available_themes = POST_THEMES
        
        # Используем остаток от деления времени на количество доступных тем
        theme_index = current_time_ms % len(available_themes)
        selected_theme = available_themes[theme_index]
        
        # Логируем выбор темы
        logger.info(f"Выбрана тема: {selected_theme}")
        
        return selected_theme
    
    async def generate_post(self, theme=None, use_meta_generation=True):
        """
        Генерирует пост, используя DeepSeek API.
        
        Args:
            theme: Тема поста (опционально). Если не указана и use_meta_generation=False,
                  выбирается случайная тема из списка.
            use_meta_generation: Использовать ли метагенерацию для создания уникального поста.
                               Если False, используется старый метод с предопределенными списками.
        """
        try:
            if use_meta_generation:
                return await self._generate_post_with_meta_generation()
            else:
                return await self._generate_post_classic(theme)
                
        except Exception as e:
            logger.error(f"Ошибка при генерации поста: {str(e)}")
            return None
    
    async def _generate_post_classic(self, theme=None):
        """Генерирует пост классическим способом с предопределенными списками."""
        try:
            # Выбираем случайные параметры для поста
            theme = theme or random.choice(POST_THEMES)
            format_type = random.choice(POST_FORMATS)
            ending = random.choice(POST_ENDINGS)
            
            # Заполняем шаблон промпта
            prompt = self.prompt_template.format(
                theme=theme,
                format=format_type,
                ending=ending
            )
            
            return await self._send_api_request(prompt)
                
        except Exception as e:
            logger.error(f"Ошибка при классической генерации поста: {str(e)}")
            return None
    
    async def _generate_post_with_meta_generation(self):
        """Генерирует пост с использованием метагенерации."""
        try:
            # Выбираем тему
            selected_theme = self._select_theme()
            
            # Получаем контекст
            context = self.context_manager.get_context()
            
            # Формируем мета-промпт с контекстом
            meta_prompt = META_GENERATION_PROMPT.format(
                context=json.dumps(context, ensure_ascii=False)
            )
            
            # Получаем параметры для генерации
            meta_response = await self._send_api_request(meta_prompt)
            
            if not meta_response:
                logger.error("Не удалось сгенерировать мета-промпт")
                return await self._generate_post_classic()
            
            # Парсим JSON и добавляем выбранную тему
            post_params = json.loads(self._clean_json_response(meta_response))
            post_params["theme"] = selected_theme
            
            # Создаем финальный промпт для генерации поста
            post_prompt = POST_GENERATION_PROMPT.format(
                theme=post_params["theme"],
                format=post_params["format"],
                ending=post_params["ending"],
                additional_instructions=post_params.get("additional_instructions", "")
            )
            
            # Генерируем пост
            post_text = await self._send_api_request(post_prompt)
            
            # Сохраняем контекст генерации
            self.context_manager.add_generation(post_params, post_text)
            
            return post_text
            
        except Exception as e:
            logger.error(f"Ошибка при метагенерации поста: {str(e)}")
            return await self._generate_post_classic()
    
    def _clean_json_response(self, response):
        """Очищает ответ API от возможных блоков кода и других форматирований."""
        try:
            # Удаляем маркеры блока кода, если они есть
            if response.startswith("```json"):
                response = response.replace("```json", "").replace("```", "")
            return response.strip()
        except Exception as e:
            logger.error(f"Ошибка при очистке JSON ответа: {str(e)}")
            return response

    async def generate_meta_prompt(self):
        """
        Генерирует мета-промпт для создания уникальных параметров поста.
        
        Returns:
            str: JSON-строка с параметрами для генерации поста
        """
        try:
            # Получаем контекст
            context = self.context_manager.get_context()
            
            # Формируем мета-промпт с контекстом
            meta_prompt = META_GENERATION_PROMPT.format(
                context=json.dumps(context, ensure_ascii=False)
            )
            
            # Получаем параметры для генерации
            meta_response = await self._send_api_request(meta_prompt)
            
            if not meta_response:
                raise ValueError("Не удалось сгенерировать мета-промпт")
            
            # Очищаем и возвращаем ответ
            return self._clean_json_response(meta_response)
            
        except Exception as e:
            logger.error(f"Ошибка при генерации мета-промпта: {str(e)}")
            raise

    async def _send_api_request(self, prompt):
        """
        Отправляет промпт в DeepSeek API и возвращает ответ.
        Args:
            prompt (str): Текст промпта для генерации
        Returns:
            str: Ответ от DeepSeek API
        """
        import aiohttp
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.api_params["model"],
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": self.api_params["temperature"],
            "max_tokens": self.api_params["max_tokens"],
            "top_p": self.api_params["top_p"],
            "stream": self.api_params["stream"],
            "presence_penalty": self.api_params["presence_penalty"],
            "frequency_penalty": self.api_params["frequency_penalty"],
            "top_k": self.api_params["top_k"],
            "seed": self.api_params["seed"]
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(self.api_url, headers=headers, json=payload) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    logger.error(f"Ошибка DeepSeek API: {resp.status} {text}")
                    return None
                data = await resp.json()
                # DeepSeek возвращает ответ в data["choices"][0]["message"]["content"]
                return data["choices"][0]["message"]["content"]
