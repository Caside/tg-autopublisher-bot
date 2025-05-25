"""
Клиент для работы с DeepSeek API для генерации текста.
Поддерживает автономную генерацию постов с использованием метагенерации.
"""

import requests
import json
import logging
import random
from config import DEEPSEEK_API_KEY
from prompt_template import (
    DEEPSEEK_PROMPT, DEEPSEEK_API_PARAMS, POST_THEMES, POST_FORMATS, POST_ENDINGS,
    META_GENERATION_PROMPT, POST_GENERATION_PROMPT
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
        
        if not self.api_key or self.api_key == "your_deepseek_api_key_here":
            logger.error("DeepSeek API ключ не настроен. Пожалуйста, добавьте его в .env файл.")
            raise ValueError("DeepSeek API ключ не настроен")
    
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
                return await self._generate_post_with_meta_generation(theme)
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
    
    async def _generate_post_with_meta_generation(self, theme=None):
        """Генерирует пост с использованием метагенерации."""
        try:
            # Если тема указана, используем её, иначе позволяем ИИ создать свою
            if theme:
                # Генерируем только формат и окончание через метагенерацию
                meta_prompt = META_GENERATION_PROMPT.replace(
                    "1. Придумай специфическую тему из одной из следующих областей:",
                    f"1. Используй указанную тему: '{theme}'. Создай для неё подходящий угол зрения:"
                )
            else:
                # Используем полную метагенерацию
                meta_prompt = META_GENERATION_PROMPT
            
            # Получаем параметры для генерации поста
            meta_response = await self._send_api_request(meta_prompt)
            
            if not meta_response:
                logger.error("Не удалось сгенерировать мета-промпт")
                # Откатываемся к классическому методу
                return await self._generate_post_classic(theme)
            
            # Парсим JSON из ответа
            try:
                # Очищаем ответ от возможных блоков кода
                cleaned_response = self._clean_json_response(meta_response)
                post_params = json.loads(cleaned_response)
                
                # Если была указана тема, убеждаемся, что она используется
                if theme:
                    post_params["theme"] = theme
                
                # Создаем финальный промпт для генерации поста
                post_prompt = POST_GENERATION_PROMPT.format(
                    theme=post_params["theme"],
                    format=post_params["format"],
                    ending=post_params["ending"],
                    additional_instructions=post_params.get("additional_instructions", "")
                )
                
                # Генерируем пост с использованием финального промпта
                return await self._send_api_request(post_prompt)
                
            except json.JSONDecodeError as e:
                logger.error(f"Ошибка при разборе JSON из мета-ответа: {str(e)}. Ответ: {meta_response}")
                # Откатываемся к классическому методу
                return await self._generate_post_classic(theme)
                
        except Exception as e:
            logger.error(f"Ошибка при метагенерации поста: {str(e)}")
            # Откатываемся к классическому методу
            return await self._generate_post_classic(theme)
    
    def _clean_json_response(self, response):
        """Очищает ответ API от возможных блоков кода и других форматирований."""
        # Удаляем маркеры блока кода, если они есть
        if response.startswith("```json"):
            # Удаляем открывающий маркер ```json и закрывающий ```
            response = response.replace("```json", "", 1)
            if response.endswith("```"):
                response = response[:-3]
        elif response.startswith("```"):
            # Удаляем открывающий и закрывающий маркеры ```
            response = response.replace("```", "", 1)
            if response.endswith("```"):
                response = response[:-3]
        
        # Удаляем префиксы и суффиксы, которые могут мешать парсингу
        response = response.strip()
        
        return response
    
    async def generate_meta_prompt(self, theme=None):
        """
        Генерирует только мета-промпт для отладки, без создания поста.
        
        Returns:
            tuple: (meta_prompt_text, meta_response_text, final_prompt_text)
        """
        try:
            # Если тема указана, используем её, иначе позволяем ИИ создать свою
            if theme:
                # Генерируем только формат и окончание через метагенерацию
                meta_prompt = META_GENERATION_PROMPT.replace(
                    "1. Придумай специфическую тему из одной из следующих областей:",
                    f"1. Используй указанную тему: '{theme}'. Создай для неё подходящий угол зрения:"
                )
            else:
                # Используем полную метагенерацию
                meta_prompt = META_GENERATION_PROMPT
            
            # Получаем параметры для генерации поста
            meta_response = await self._send_api_request(meta_prompt)
            
            if not meta_response:
                return (meta_prompt, "Ошибка: не удалось получить ответ от API", "")
            
            # Парсим JSON из ответа
            try:
                # Очищаем ответ от возможных блоков кода
                cleaned_response = self._clean_json_response(meta_response)
                post_params = json.loads(cleaned_response)
                
                # Если была указана тема, убеждаемся, что она используется
                if theme:
                    post_params["theme"] = theme
                
                # Создаем финальный промпт для генерации поста
                final_prompt = POST_GENERATION_PROMPT.format(
                    theme=post_params["theme"],
                    format=post_params["format"],
                    ending=post_params["ending"],
                    additional_instructions=post_params.get("additional_instructions", "")
                )
                
                return (meta_prompt, meta_response, final_prompt)
                
            except json.JSONDecodeError as e:
                return (meta_prompt, f"Ошибка при разборе JSON: {str(e)}. Ответ: {meta_response}", "")
                
        except Exception as e:
            return (meta_prompt, f"Ошибка: {str(e)}", "")
    
    async def _send_api_request(self, prompt):
        """Отправляет запрос к DeepSeek API."""
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
            response_text = result["choices"][0]["message"]["content"].strip()
            logger.info("Запрос к API успешно выполнен")
            return response_text
        else:
            logger.error(f"Ошибка API: {response.status_code} - {response.text}")
            return None
