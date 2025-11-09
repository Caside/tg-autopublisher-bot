"""
Модуль для обработки новостей и отбора релевантных заголовков.
Упрощенная версия для нового формата: 5 заголовков + философия.
"""

import logging
from typing import List
import random

# Импортируем NewsItem для типизации
from news_collector import NewsItem

logger = logging.getLogger('context_processor')


class ContextProcessor:
    """Класс для обработки и отбора новостных заголовков."""

    def __init__(self):
        # Военные ключевые слова для исключения
        self.military_keywords = [
            # Прямые военные термины
            'всу', 'удар', 'обстрел', 'военный', 'армия', 'конфликт', 'война',
            'боевые действия', 'атака', 'наступление', 'оборона', 'фронт',
            'солдат', 'офицер', 'генерал', 'командование', 'штаб',

            # Географические зоны конфликтов
            'белгород', 'донбасс', 'украина', 'сво', 'луганск', 'донецк',
            'херсон', 'запорожье', 'крым', 'курск',

            # Военная техника и оружие
            'танк', 'бпла', 'ракета', 'дрон', 'артиллерия', 'снаряд',
            'беспилотник', 'истребитель', 'бомбардировщик', 'ввс',
            'корабль', 'подлодка', 'флот', 'крейсер', 'фрегат',

            # Военные операции
            'операция', 'мобилизация', 'призыв', 'резерв', 'батальон',
            'полк', 'дивизия', 'бригада', 'взвод', 'рота',

            # Международные конфликты и политика
            'нато', 'пентагон', 'генштаб', 'минобороны', 'разведка',

            # Дополнительные военно-политические термины
            'лавров', 'активы россии', 'санкции', 'одесса', 'взрывы',
            'подрыв', 'северных потоков', 'обвиняемый', 'долги украины',
            'конфискация', 'геополитика', 'дипломатия', 'посол',
            'МИД', 'внешняя политика', 'международные отношения'
        ]

        # Предпочтительные мирные темы
        self.positive_keywords = [
            # Наука и технологии
            'исследование', 'ученые', 'открытие', 'ии', 'искусственный интеллект',
            'стартап', 'технология', 'инновация', 'разработка', 'изобретение',
            'космос', 'наука', 'эксперимент', 'лаборатория',

            # Экономика и бизнес
            'экономика', 'бизнес', 'инвестиции', 'рынок', 'компания',
            'банк', 'финансы', 'торговля', 'производство', 'промышленность',
            'рост', 'развитие', 'проект', 'инициатива',

            # Культура и образование
            'культура', 'искусство', 'образование', 'музей', 'театр',
            'фестиваль', 'выставка', 'концерт', 'книга', 'литература',
            'кино', 'университет', 'школа', 'студенты',

            # Здоровье и общество
            'здоровье', 'медицина', 'лечение', 'вакцина', 'терапия',
            'экология', 'природа', 'окружающая среда', 'климат',
            'социальный', 'благотворительность', 'помощь', 'поддержка',

            # Спорт
            'спорт', 'олимпиада', 'чемпионат', 'соревнование', 'турнир'
        ]

        logger.info("Инициализирован процессор заголовков с фильтрацией военных новостей")

    def _is_military_news(self, headline: str) -> bool:
        """Проверяет, относится ли заголовок к военной тематике."""
        headline_lower = headline.lower()

        for keyword in self.military_keywords:
            if keyword in headline_lower:
                return True
        return False

    def _has_positive_content(self, headline: str) -> bool:
        """Проверяет, содержит ли заголовок позитивные темы."""
        headline_lower = headline.lower()

        for keyword in self.positive_keywords:
            if keyword in headline_lower:
                return True
        return False

    async def select_top_news_items(self, news_items: List[NewsItem], limit: int = 5) -> List[NewsItem]:
        """
        Отбирает топ новости для поста.

        Args:
            news_items: Список объектов новостей
            limit: Количество новостей для отбора (по умолчанию 5)

        Returns:
            Список отобранных объектов новостей
        """
        if not news_items:
            logger.warning("Нет новостей для отбора")
            return []

        # Фильтруем новости поэтапно
        military_filtered = 0
        positive_items = []
        neutral_items = []

        for item in news_items:
            headline = item.title.strip()

            # Пропускаем слишком короткие заголовки
            if len(headline) < 20:
                continue

            # Пропускаем заголовки с техническими терминами или рекламой
            skip_words = ['реклама', 'спонсор', 'партнер', 'pr', 'промо']
            if any(word in headline.lower() for word in skip_words):
                continue

            # ГЛАВНЫЙ ФИЛЬТР: исключаем военные новости
            if self._is_military_news(headline):
                military_filtered += 1
                logger.debug(f"Отфильтрована военная новость: {headline[:50]}...")
                continue

            # Разделяем на позитивные и нейтральные
            if self._has_positive_content(headline):
                positive_items.append(item)
            else:
                neutral_items.append(item)

        # Приоритизация: сначала позитивные, затем нейтральные
        filtered_items = positive_items + neutral_items

        logger.info(f"Отфильтровано {military_filtered} военных новостей")
        logger.info(f"Найдено {len(positive_items)} позитивных и {len(neutral_items)} нейтральных новостей")

        # Выбираем новости с приоритетом позитивных и балансировкой источников
        selected = self._balance_sources_selection(filtered_items, positive_items, neutral_items, limit)

        return selected

    def _balance_sources_selection(self, all_items: List[NewsItem], positive_items: List[NewsItem],
                                 neutral_items: List[NewsItem], limit: int) -> List[NewsItem]:
        """Выбирает новости с балансировкой источников."""
        if len(all_items) <= limit:
            logger.info(f"Используем все {len(all_items)} доступных новости (после фильтрации военных)")
            return all_items

        # Максимум 2 новости от одного источника
        max_per_source = 2
        selected = []
        source_count = {}

        # Первый проход: приоритет позитивным новостям
        remaining_positive = positive_items.copy()
        remaining_neutral = neutral_items.copy()

        # Балансируем источники для позитивных новостей
        random.shuffle(remaining_positive)
        for item in remaining_positive:
            if len(selected) >= limit:
                break
            if source_count.get(item.source, 0) < max_per_source:
                selected.append(item)
                source_count[item.source] = source_count.get(item.source, 0) + 1

        # Добираем нейтральными новостями, если места еще есть
        random.shuffle(remaining_neutral)
        for item in remaining_neutral:
            if len(selected) >= limit:
                break
            if source_count.get(item.source, 0) < max_per_source:
                selected.append(item)
                source_count[item.source] = source_count.get(item.source, 0) + 1

        # Если все еще не набрали limit, берем любые оставшиеся (игнорируя лимит источников)
        if len(selected) < limit:
            all_remaining = [item for item in all_items if item not in selected]
            needed = limit - len(selected)
            if all_remaining:
                selected.extend(random.sample(all_remaining, min(needed, len(all_remaining))))

        # Логирование статистики
        positive_count = len([item for item in selected if item in positive_items])
        neutral_count = len([item for item in selected if item in neutral_items])

        logger.info(f"Отобрано {len(selected)} новостей: {positive_count} позитивных, {neutral_count} нейтральных")
        logger.info(f"Распределение по источникам: {dict(source_count)}")

        return selected

    async def select_top_headlines(self, headlines: List[str], limit: int = 5) -> List[str]:
        """
        Отбирает топ заголовки для поста.

        Args:
            headlines: Список всех доступных заголовков
            limit: Количество заголовков для отбора (по умолчанию 5)

        Returns:
            Список отобранных заголовков
        """
        if not headlines:
            logger.warning("Нет заголовков для отбора")
            return []

        # Фильтруем заголовки поэтапно
        filtered_headlines = []
        military_filtered = 0
        positive_headlines = []
        neutral_headlines = []

        for headline in headlines:
            headline = headline.strip()

            # Пропускаем слишком короткие заголовки
            if len(headline) < 20:
                continue

            # Пропускаем заголовки с техническими терминами или рекламой
            skip_words = ['реклама', 'спонсор', 'партнер', 'pr', 'промо']
            if any(word in headline.lower() for word in skip_words):
                continue

            # ГЛАВНЫЙ ФИЛЬТР: исключаем военные новости
            if self._is_military_news(headline):
                military_filtered += 1
                logger.debug(f"Отфильтрована военная новость: {headline[:50]}...")
                continue

            # Разделяем на позитивные и нейтральные
            if self._has_positive_content(headline):
                positive_headlines.append(headline)
            else:
                neutral_headlines.append(headline)

        # Приоритизация: сначала позитивные, затем нейтральные
        filtered_headlines = positive_headlines + neutral_headlines

        logger.info(f"Отфильтровано {military_filtered} военных новостей")
        logger.info(f"Найдено {len(positive_headlines)} позитивных и {len(neutral_headlines)} нейтральных новостей")

        if not filtered_headlines:
            logger.warning("После фильтрации не осталось заголовков")
            return headlines[:limit] if headlines else []

        # Выбираем заголовки с приоритетом позитивных
        if len(filtered_headlines) > limit:
            # Стараемся взять больше позитивных новостей
            positive_limit = min(len(positive_headlines), max(3, limit - 2))  # Минимум 3 позитивных
            neutral_limit = limit - positive_limit

            selected_positive = random.sample(positive_headlines, min(positive_limit, len(positive_headlines)))
            selected_neutral = random.sample(neutral_headlines, min(neutral_limit, len(neutral_headlines)))

            selected = selected_positive + selected_neutral

            # Если не хватает, добираем из оставшихся
            if len(selected) < limit and len(filtered_headlines) > len(selected):
                remaining = [h for h in filtered_headlines if h not in selected]
                needed = limit - len(selected)
                selected.extend(random.sample(remaining, min(needed, len(remaining))))

            logger.info(f"Отобрано {len(selected)} заголовков: {len(selected_positive)} позитивных, {len(selected_neutral)} нейтральных")
        else:
            selected = filtered_headlines
            logger.info(f"Используем все {len(selected)} доступных заголовка (после фильтрации военных)")

        return selected