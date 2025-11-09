"""
Модуль для обработки новостей и отбора релевантных заголовков.
Упрощенная версия для нового формата: 5 заголовков + философия.
"""

import logging
from typing import List
import random

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