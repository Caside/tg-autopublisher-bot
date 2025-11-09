"""
Модуль для сбора новостей из RSS фидов.
Собирает актуальные новости для создания контекста времени.
"""

import feedparser
import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pytz
from bs4 import BeautifulSoup
import re

logger = logging.getLogger('news_collector')


class NewsItem:
    """Класс для хранения информации о новости."""

    def __init__(self, title: str, summary: str, link: str, published: datetime, source: str):
        self.title = title
        self.summary = summary
        self.link = link
        self.published = published
        self.source = source

    def __repr__(self):
        return f"NewsItem(title='{self.title[:50]}...', source='{self.source}')"


class NewsCollector:
    """Класс для сбора новостей из различных RSS источников."""

    def __init__(self):
        # Настройка источников новостей с их RSS фидами
        self.sources = {
            'ria': 'https://ria.ru/export/rss2/archive/index.xml',
            'lenta': 'https://lenta.ru/rss',
            'rbc': 'https://rssexport.rbc.ru/rbcnews/news/20/full.rss',
            'vedomosti': 'https://www.vedomosti.ru/rss/news',
            'habr': 'https://habr.com/ru/rss/all/all/',
            'nplus1': 'https://nplus1.ru/rss'
        }

        # Настройка тайм-аутов и ограничений
        self.timeout = 10
        self.max_items_per_source = 5
        self.max_age_hours = 24

        logger.info(f"Инициализирован сборщик новостей с {len(self.sources)} источниками")

    def _clean_html(self, html_text: str) -> str:
        """Очищает HTML теги и лишние символы из текста."""
        if not html_text:
            return ""

        # Удаляем HTML теги
        soup = BeautifulSoup(html_text, 'html.parser')
        text = soup.get_text()

        # Очищаем лишние пробелы и переносы строк
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def _parse_date(self, date_string: str) -> Optional[datetime]:
        """Парсит дату из RSS фида."""
        try:
            import time
            # feedparser возвращает time.struct_time
            return datetime.fromtimestamp(time.mktime(feedparser._parse_date(date_string)))
        except:
            # Если не удалось распарсить, используем текущее время
            return datetime.now()

    def _is_recent(self, published_date: datetime) -> bool:
        """Проверяет, является ли новость достаточно свежей."""
        if not published_date:
            return False

        cutoff_time = datetime.now() - timedelta(hours=self.max_age_hours)
        return published_date > cutoff_time

    async def _fetch_feed(self, source_name: str, url: str) -> List[NewsItem]:
        """Получает и парсит RSS фид от одного источника."""
        news_items = []

        try:
            logger.debug(f"Получение фида от {source_name}: {url}")

            # Получаем RSS фид
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        logger.warning(f"Ошибка получения фида {source_name}: HTTP {response.status}")
                        return news_items

                    content = await response.text()

            # Парсим RSS фид
            feed = feedparser.parse(content)

            if not feed.entries:
                logger.warning(f"Пустой фид от {source_name}")
                return news_items

            # Обрабатываем записи
            for entry in feed.entries[:self.max_items_per_source]:
                try:
                    # Извлекаем данные
                    title = self._clean_html(entry.get('title', ''))
                    summary = self._clean_html(entry.get('summary', ''))
                    link = entry.get('link', '')

                    # Парсим дату публикации
                    published_raw = entry.get('published_parsed') or entry.get('updated_parsed')
                    if published_raw:
                        published = datetime(*published_raw[:6])
                    else:
                        published = datetime.now()

                    # Проверяем свежесть новости
                    if not self._is_recent(published):
                        logger.debug(f"Пропуск старой новости: {title[:50]}...")
                        continue

                    # Создаем объект новости
                    news_item = NewsItem(
                        title=title,
                        summary=summary,
                        link=link,
                        published=published,
                        source=source_name
                    )

                    news_items.append(news_item)
                    logger.debug(f"Добавлена новость от {source_name}: {title[:50]}...")

                except Exception as e:
                    logger.error(f"Ошибка обработки записи от {source_name}: {str(e)}")
                    continue

            logger.info(f"Получено {len(news_items)} новостей от {source_name}")
            return news_items

        except asyncio.TimeoutError:
            logger.warning(f"Тайм-аут при получении фида {source_name}")
        except Exception as e:
            logger.error(f"Ошибка получения фида {source_name}: {str(e)}")

        return news_items

    async def collect_news(self) -> List[NewsItem]:
        """Собирает новости от всех источников."""
        logger.info("Начало сбора новостей от всех источников")

        all_news = []

        # Создаем задачи для параллельного получения фидов
        tasks = []
        for source_name, url in self.sources.items():
            task = asyncio.create_task(self._fetch_feed(source_name, url))
            tasks.append(task)

        # Ждем выполнения всех задач
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Обрабатываем результаты
            for i, result in enumerate(results):
                source_name = list(self.sources.keys())[i]

                if isinstance(result, Exception):
                    logger.error(f"Ошибка от источника {source_name}: {result}")
                    continue

                if isinstance(result, list):
                    all_news.extend(result)

        except Exception as e:
            logger.error(f"Критическая ошибка при сборе новостей: {str(e)}")

        # Сортируем новости по дате публикации (новые первыми)
        all_news.sort(key=lambda x: x.published, reverse=True)

        logger.info(f"Собрано {len(all_news)} новостей от {len(self.sources)} источников")

        # Логируем статистику по источникам
        source_stats = {}
        for news in all_news:
            source_stats[news.source] = source_stats.get(news.source, 0) + 1

        for source, count in source_stats.items():
            logger.info(f"  {source}: {count} новостей")

        return all_news

    async def get_recent_headlines(self, limit: int = 20) -> List[str]:
        """Получает заголовки недавних новостей для анализа."""
        news_items = await self.collect_news()
        headlines = [item.title for item in news_items[:limit] if item.title]

        logger.info(f"Возвращено {len(headlines)} заголовков для анализа")
        return headlines