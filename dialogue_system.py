"""
Система управления диалогами между мыслителями.
Создает живые философские дискуссии на основе тем.
"""

import json
import random
import logging
from datetime import datetime, timedelta
from collections import deque
from typing import List, Dict, Optional, Tuple
from philosophers import (
    PHILOSOPHERS, 
    get_philosopher_names, 
    get_random_philosopher_pair, 
    get_philosopher_prompt
)

logger = logging.getLogger(__name__)

class DialogueHistory:
    """Управляет историей диалогов для создания контекста."""
    
    def __init__(self, max_history=10):
        self.max_history = max_history
        self.dialogues = deque(maxlen=max_history)
        self.themes_used = deque(maxlen=20)
    
    def add_dialogue(self, dialogue_data: Dict):
        """Добавляет диалог в историю."""
        dialogue_data['timestamp'] = datetime.now().isoformat()
        self.dialogues.append(dialogue_data)
        self.themes_used.append(dialogue_data.get('theme', ''))
    
    def get_recent_context(self, theme: str, philosopher: str) -> str:
        """Получает релевантный контекст для мыслителя по теме."""
        relevant_dialogues = []
        
        # Ищем диалоги с похожими темами или с участием этого мыслителя
        for dialogue in list(self.dialogues)[-5:]:  # Последние 5 диалогов
            if (theme.lower() in dialogue.get('theme', '').lower() or 
                philosopher in dialogue.get('participants', [])):
                relevant_dialogues.append(dialogue)
        
        if not relevant_dialogues:
            return ""
        
        context_parts = []
        for dialogue in relevant_dialogues[-2:]:  # Максимум 2 предыдущих диалога
            participants = " и ".join([PHILOSOPHERS[p]['name'] for p in dialogue.get('participants', [])])
            context_parts.append(f"Недавно {participants} обсуждали '{dialogue.get('theme', '')}': {dialogue.get('summary', '')[:100]}...")
        
        return "\n".join(context_parts)
    
    def get_theme_freshness(self, theme: str) -> float:
        """Возвращает "свежесть" темы (0-1, где 1 = очень свежая)."""
        recent_themes = list(self.themes_used)[-10:]
        if theme in recent_themes:
            # Чем недавнее была тема, тем меньше свежесть
            last_index = len(recent_themes) - 1 - recent_themes[::-1].index(theme)
            return last_index / len(recent_themes)
        return 1.0  # Новая тема

class DialogueSystem:
    """Основная система управления диалогами."""
    
    def __init__(self, deepseek_client):
        self.deepseek_client = deepseek_client
        self.history = DialogueHistory()
        self.dialogue_formats = [
            "спор",
            "дружеская беседа", 
            "дебаты",
            "философская дискуссия",
            "столкновение мировоззрений",
            "поиск истины",
            "обмен мнениями"
        ]
    
    def select_theme_and_philosophers(self, theme: str = None) -> Tuple[str, List[str]]:
        """Выбирает тему и участников диалога."""
        from themes import POST_THEMES
        
        if not theme:
            # Выбираем тему с учетом свежести
            themes_with_freshness = [
                (t, self.history.get_theme_freshness(t)) for t in POST_THEMES
            ]
            # Сортируем по свежести и выбираем из топ-50%
            themes_with_freshness.sort(key=lambda x: x[1], reverse=True)
            top_themes = themes_with_freshness[:len(themes_with_freshness)//2]
            theme = random.choice(top_themes)[0]
        
        # Выбираем двух мыслителей
        philosophers = get_random_philosopher_pair()
        
        return theme, philosophers
    
    async def generate_dialogue_opening(self, theme: str, philosophers: List[str]) -> str:
        """Генерирует вводную часть диалога."""
        philosopher_names = [PHILOSOPHERS[p]['name'] for p in philosophers]
        dialogue_format = random.choice(self.dialogue_formats)
        
        opening_prompt = f"""Создай очень краткое введение (1-2 предложения, максимум 50 слов) для диалога между {philosopher_names[0]} и {philosopher_names[1]} на тему "{theme}".

Формат: {dialogue_format}

Введение должно быть лаконичным и интригующим, задать контекст одной фразой."""
        
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.deepseek_client.api_key}"
            }
            
            payload = {
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": opening_prompt}],
                "max_tokens": 80,
                "temperature": 0.8
            }
            
            import requests
            response = requests.post(
                self.deepseek_client.api_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"].strip()
            else:
                logger.error(f"Ошибка при генерации введения: {response.status_code}")
                return f"🎭 {philosopher_names[0]} и {philosopher_names[1]} встречаются для обсуждения темы: {theme}"
                
        except Exception as e:
            logger.error(f"Ошибка при генерации введения: {str(e)}")
            return f"🎭 {philosopher_names[0]} и {philosopher_names[1]} начинают диалог о '{theme}'"
    
    async def generate_philosopher_response(self, philosopher: str, theme: str, context: str = "") -> str:
        """Генерирует ответ одного мыслителя."""
        # Получаем историю для контекста
        historical_context = self.history.get_recent_context(theme, philosopher)
        full_context = f"{historical_context}\n\n{context}".strip()
        
        prompt = get_philosopher_prompt(philosopher, theme, full_context if full_context else None)
        
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.deepseek_client.api_key}"
            }
            
            payload = {
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 120,
                "temperature": 0.9,
                "top_p": 0.95
            }
            
            import requests
            response = requests.post(
                self.deepseek_client.api_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"].strip()
            else:
                logger.error(f"Ошибка API при генерации ответа {philosopher}: {response.status_code}")
                return f"*{PHILOSOPHERS[philosopher]['name']} задумался...*"
                
        except Exception as e:
            logger.error(f"Ошибка при генерации ответа {philosopher}: {str(e)}")
            return f"*{PHILOSOPHERS[philosopher]['name']} размышляет над ответом...*"
    
    async def create_full_dialogue(self, theme: str = None) -> Dict:
        """Создает полный диалог между двумя мыслителями."""
        try:
            # Выбираем тему и участников
            theme, philosophers = self.select_theme_and_philosophers(theme)
            
            logger.info(f"Создаем диалог между {philosophers} на тему: {theme}")
            
            # Генерируем введение
            opening = await self.generate_dialogue_opening(theme, philosophers)
            
            # Генерируем первую реплику
            first_response = await self.generate_philosopher_response(philosophers[0], theme)
            
            # Генерируем ответ второго мыслителя
            context_for_second = f"{PHILOSOPHERS[philosophers[0]]['name']}: {first_response}"
            second_response = await self.generate_philosopher_response(philosophers[1], theme, context_for_second)
            
            # Формируем итоговый диалог (только 2 реплики для краткости)
            dialogue = {
                'theme': theme,
                'participants': philosophers,
                'opening': opening,
                'exchanges': [
                    {'speaker': philosophers[0], 'text': first_response},
                    {'speaker': philosophers[1], 'text': second_response}
                ],
                'summary': f"{first_response[:50]}... → {second_response[:50]}..."
            }
            
            # Добавляем в историю
            self.history.add_dialogue(dialogue)
            
            return dialogue
            
        except Exception as e:
            logger.error(f"Ошибка при создании диалога: {str(e)}")
            return None
    
    def format_dialogue_for_telegram(self, dialogue: Dict) -> str:
        """Форматирует диалог для публикации в Telegram."""
        if not dialogue:
            return "Ошибка при создании диалога"
        
        formatted = f"<b>💭 {dialogue['opening']}</b>\n\n"
        
        for exchange in dialogue['exchanges']:
            speaker_name = PHILOSOPHERS[exchange['speaker']]['name']
            speaker_emoji = self.get_speaker_emoji(exchange['speaker'])
            
            formatted += f"{speaker_emoji} <b>{speaker_name}:</b>\n"
            formatted += f"<i>{exchange['text']}</i>\n\n"
        
        formatted += f"#философия #{dialogue['theme'].replace(' ', '_')}"
        
        return formatted
    
    def get_speaker_emoji(self, philosopher: str) -> str:
        """Возвращает эмодзи для мыслителя."""
        emoji_map = {
            'stoic': '🏛️',
            'existentialist': '🌊', 
            'zen_master': '🍃',
            'cynic': '⚡',
            'mystic': '✨'
        }
        return emoji_map.get(philosopher, '🧠')
    
    def get_dialogue_stats(self) -> Dict:
        """Возвращает статистику диалогов."""
        total_dialogues = len(self.history.dialogues)
        if total_dialogues == 0:
            return {"total": 0, "recent_themes": [], "active_philosophers": []}
        
        recent_themes = list(self.history.themes_used)[-5:]
        
        # Подсчитываем активность мыслителей
        philosopher_counts = {}
        for dialogue in self.history.dialogues:
            for participant in dialogue.get('participants', []):
                philosopher_counts[participant] = philosopher_counts.get(participant, 0) + 1
        
        return {
            "total": total_dialogues,
            "recent_themes": recent_themes,
            "active_philosophers": philosopher_counts,
            "available_philosophers": get_philosopher_names()
        } 