"""
Клиент для работы с DeepSeek API для генерации текста.
Поддерживает только классические посты с системой случайных ключевых слов.
"""

from openai import OpenAI
import json
import logging
import random
import os
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List

from config import DEEPSEEK_API_KEY, NEWS_ENABLED, NEWS_CACHE_HOURS
from prompt_template import (
    DEEPSEEK_PROMPT,
    DEEPSEEK_API_PARAMS,
    DEEPSEEK_API_PARAM_RANGES
)
from news_collector import NewsCollector
from context_processor import ContextProcessor

# Настройка логирования
logger = logging.getLogger('deepseek_client')
logger.setLevel(logging.INFO)

class DeepSeekClient:
    """Клиент для работы с DeepSeek API."""

    def __init__(self):
        self.api_key = DEEPSEEK_API_KEY
        self.prompt_template = DEEPSEEK_PROMPT
        self.api_params = DEEPSEEK_API_PARAMS.copy()

        # Инициализируем OpenAI клиент для DeepSeek API
        if not self.api_key or self.api_key == "your_deepseek_api_key_here":
            logger.error("DeepSeek API ключ не настроен. Пожалуйста, добавьте его в .env файл.")
            raise ValueError("DeepSeek API ключ не настроен")

        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.deepseek.com"
        )

        # Ключевые слова больше не нужны в новом формате

        # Инициализируем компоненты для работы с новостями
        self.news_enabled = NEWS_ENABLED
        if self.news_enabled:
            self.news_collector = NewsCollector()
            self.context_processor = ContextProcessor()
            logger.info("Новостная интеграция включена")
        else:
            self.news_collector = None
            self.context_processor = None
            logger.info("Новостная интеграция отключена")

        # Кэш для новостей
        self._news_cache = None
        self._news_cache_time = None
    
    

    
    def _get_random_api_params(self):
        """Генерирует случайные параметры API из заданных диапазонов."""
        params = self.api_params.copy()
        for param, (min_val, max_val) in DEEPSEEK_API_PARAM_RANGES.items():
            params[param] = round(random.uniform(min_val, max_val), 2)
        return params
    

    async def _get_headlines(self, force_refresh: bool = False) -> List[str]:
        """Получает 5 заголовков новостей с кэшированием."""
        if not self.news_enabled or not self.news_collector:
            return [
                "Новости недоступны - технические работы",
                "Обновление системы в процессе",
                "Временные сложности с подключением",
                "Ожидайте восстановления сервиса",
                "Приносим извинения за неудобства"
            ]

        try:
            # Проверяем кэш (если не принудительное обновление)
            now = datetime.now()
            cache_hours = NEWS_CACHE_HOURS if 'NEWS_CACHE_HOURS' in globals() else 1

            if (not force_refresh and
                    self._news_cache_time and
                    self._news_cache and
                    (now - self._news_cache_time).total_seconds() < cache_hours * 3600):
                logger.debug("Используем кэшированные новости")
                return await self.context_processor.select_top_headlines(self._news_cache, limit=5)

            # Собираем свежие новости
            logger.info("Сбор свежих новостей")
            headlines = await self.news_collector.get_recent_headlines(limit=20)

            if not headlines:
                logger.warning("Новости не получены, используем fallback")
                fallback_headlines = [
                    "Технологический сектор продолжает развиваться",
                    "Эксперты анализируют текущие экономические тренды",
                    "Исследователи представили новые научные данные",
                    "Обществу предстоит адаптироваться к изменениям",
                    "События развиваются в динамичном ритме"
                ]
                return fallback_headlines

            # Обновляем кэш
            self._news_cache = headlines
            self._news_cache_time = now

            # Используем context_processor для отбора лучших заголовков
            selected_headlines = await self.context_processor.select_top_headlines(headlines, limit=5)

            logger.info(f"Выбрано {len(selected_headlines)} заголовков из {len(headlines)} доступных")
            return selected_headlines

        except Exception as e:
            logger.error(f"Ошибка при получении заголовков: {str(e)}")
            return [
                "Произошла ошибка получения новостей",
                "Система работает над восстановлением",
                "Техническая поддержка уведомлена",
                "Ожидается возобновление работы",
                "Спасибо за ваше терпение"
            ]

    async def _get_news_items(self, force_refresh: bool = False) -> List:
        """Получает 5 объектов новостей с кэшированием."""
        if not self.news_enabled or not self.news_collector:
            return []

        try:
            # Проверяем кэш (если не принудительное обновление)
            now = datetime.now()
            cache_hours = NEWS_CACHE_HOURS if 'NEWS_CACHE_HOURS' in globals() else 1

            if (not force_refresh and
                    self._news_cache_time and
                    self._news_cache and
                    (now - self._news_cache_time).total_seconds() < cache_hours * 3600):
                logger.debug("Используем кэшированные новости")
                return await self.context_processor.select_top_news_items(self._news_cache, limit=5)

            # Собираем свежие новости
            logger.info("Сбор свежих новостей")
            news_items = await self.news_collector.get_recent_news_items(limit=20)

            if not news_items:
                logger.warning("Новости не получены, используем fallback")
                return []

            # Обновляем кэш
            self._news_cache = news_items
            self._news_cache_time = now

            # Используем context_processor для отбора лучших новостей
            selected_items = await self.context_processor.select_top_news_items(news_items, limit=5)

            logger.info(f"Выбрано {len(selected_items)} новостей из {len(news_items)} доступных")
            return selected_items

        except Exception as e:
            logger.error(f"Ошибка при получении новостей: {str(e)}")
            return []

    def _format_headlines_section(self, news_items: List) -> str:
        """Форматирует секцию заголовков с ссылками."""
        headlines_lines = []
        headlines_lines.append("📰 <b>Новости:</b>")

        for item in news_items:
            if hasattr(item, 'link') and item.link:
                # Формат с ссылкой
                headline_line = f"• <a href=\"{item.link}\">{item.title}</a>"
            else:
                # Формат без ссылки (fallback)
                headline_line = f"• {item.title}"
            headlines_lines.append(headline_line)

        return "\n".join(headlines_lines)

    async def generate_prompt_with_context(self):
        """Генерирует промпт с новостными заголовками."""
        # Получаем 5 новостных заголовков
        headlines_list = await self._get_headlines()
        headlines_string = "\n".join([f"• {headline}" for headline in headlines_list])

        # Заполняем шаблон промпта
        prompt = self.prompt_template.format(
            headlines=headlines_string
        )

        logger.debug(f"Сгенерирован промпт с {len(headlines_list)} заголовками")
        return prompt, headlines_list
    
    async def generate_post(self):
        """Генерирует пост с контекстом времени, используя DeepSeek API."""
        try:
            # Генерируем промпт с новостями
            if self.news_enabled:
                prompt, headlines_list = await self.generate_prompt_with_context()
                logger.info(f"Используем {len(headlines_list)} новостных заголовков")
            else:
                # Fallback без новостей
                headlines_list = [
                    "Новости недоступны - работаем в режиме fallback",
                    "Система временно использует базовый режим",
                    "Ожидается восстановление новостной ленты",
                    "Приносим извинения за неудобства",
                    "Работа сервиса продолжается в штатном режиме"
                ]
                headlines_string = "\n".join([f"• {headline}" for headline in headlines_list])
                prompt = self.prompt_template.format(headlines=headlines_string)
                logger.info("Генерация без новостного контекста (fallback режим)")

            # Получаем случайные параметры API
            api_params = self._get_random_api_params()

            # Отправляем запрос через OpenAI SDK
            response = self.client.chat.completions.create(
                model=api_params["model"],
                messages=[{"role": "user", "content": prompt}],
                max_tokens=api_params["max_tokens"],
                temperature=api_params.get("temperature", 0.7),
                top_p=api_params.get("top_p", 0.9),
                presence_penalty=api_params.get("presence_penalty", 0.5),
                frequency_penalty=api_params.get("frequency_penalty", 0.6),
                stream=False
            )

            if response.choices and len(response.choices) > 0:
                post_text = response.choices[0].message.content.strip()
                logger.info(f"Пост сгенерирован на основе {len(headlines_list)} новостных заголовков")
                return post_text, prompt, headlines_list
            else:
                logger.error("API вернул пустой ответ")
                return None, None, None

        except Exception as e:
            logger.error(f"Ошибка при генерации поста: {str(e)}")
            return None, None, None

    async def generate_hybrid_post(self, force_refresh: bool = False):
        """Генерирует пост гибридно: заголовки в коде, комментарий через LLM."""
        try:
            # Получаем новостные объекты
            news_items = await self._get_news_items(force_refresh=force_refresh)

            if not news_items:
                logger.warning("Нет новостей для генерации поста")
                return None, None, None

            # Форматируем заголовки программно
            headlines_section = self._format_headlines_section(news_items)

            # Создаем список разнообразных философских вопросов
            philosophical_questions = [
                "Какой главный инсайт о человеческой природе?",
                "Что это говорит о нашем времени?",
                "Какой парадокс современности здесь проявляется?",
                "Что объединяет эти события?",
                "Какую закономерность можно увидеть?",
                "О чем это говорит в глобальном смысле?",
                "Какой вывод можно сделать о современном мире?",
                "Какую тенденцию это отражает?",
                "Что это показывает о человеческих приоритетах?",
                "Какой глубинный смысл здесь скрыт?"
            ]

            # Выбираем случайный вопрос
            random_question = random.choice(philosophical_questions)

            # Формируем список заголовков для промпта
            headlines_for_prompt = [item.title for item in news_items]
            headlines_list = '\n'.join([f"• {headline}" for headline in headlines_for_prompt])

            # Создаем промпт с полными заголовками
            prompt = f"""Вот 5 новостей:
{headlines_list}

В 2-3 предложениях (максимум 600 символов) найди общую нить между этими событиями. {random_question} НЕ ПОВТОРЯЙ заголовки, БЕЗ форматирования, КРАТКО."""

            # Получаем случайные параметры API
            api_params = self._get_random_api_params()

            # Генерируем только комментарий через LLM
            response = self.client.chat.completions.create(
                model=api_params["model"],
                messages=[{"role": "user", "content": prompt}],
                max_tokens=api_params["max_tokens"],
                temperature=api_params.get("temperature", 0.7),
                top_p=api_params.get("top_p", 0.9),
                presence_penalty=api_params.get("presence_penalty", 0.5),
                frequency_penalty=api_params.get("frequency_penalty", 0.6),
                stream=False
            )

            if response.choices and len(response.choices) > 0:
                commentary = response.choices[0].message.content.strip()

                # Ограничиваем длину комментария
                if len(commentary) > 700:
                    commentary = commentary[:700].rsplit('.', 1)[0] + '.'
                    logger.info(f"Комментарий обрезан до {len(commentary)} символов")

                # Склеиваем пост: заголовки (код) + комментарий (LLM)
                final_post = f"{headlines_section}\n\n{commentary}"

                logger.info(f"Гибридный пост сгенерирован на основе {len(news_items)} новостей")
                return final_post, prompt, [item.title for item in news_items]
            else:
                logger.error("API вернул пустой ответ")
                return None, None, None

        except Exception as e:
            logger.error(f"Ошибка при гибридной генерации поста: {str(e)}")
            return None, None, None
