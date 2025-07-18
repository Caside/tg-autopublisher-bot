"""
Система управления цепочками диалогов.
Создает последовательные посты-ответы между мыслителями во времени.
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
    get_philosopher_prompt
)

logger = logging.getLogger(__name__)

class DialogueThread:
    """Представляет цепочку связанных постов-диалогов."""
    
    def __init__(self, thread_id: str, theme: str, starter_philosopher: str):
        self.thread_id = thread_id
        self.theme = theme
        self.posts = []
        self.participants = set([starter_philosopher])
        self.created_at = datetime.now()
        self.last_post_at = datetime.now()
        self.is_active = True
    
    def add_post(self, philosopher: str, content: str, post_type: str = "response", message_id: int = None):
        """Добавляет пост в цепочку."""
        post = {
            'philosopher': philosopher,
            'content': content,
            'post_type': post_type,  # 'starter', 'response'
            'timestamp': datetime.now().isoformat(),
            'post_number': len(self.posts) + 1,
            'message_id': message_id  # ID сообщения в Telegram для реплаев
        }
        self.posts.append(post)
        self.participants.add(philosopher)
        self.last_post_at = datetime.now()
    
    def get_last_message_id(self) -> Optional[int]:
        """Возвращает message_id последнего поста для реплая."""
        if self.posts:
            return self.posts[-1].get('message_id')
        return None
    
    def update_last_message_id(self, message_id: int):
        """Обновляет message_id последнего поста после публикации."""
        if self.posts:
            self.posts[-1]['message_id'] = message_id
    
    def get_context_for_response(self) -> str:
        """Возвращает контекст для создания ответа."""
        if not self.posts:
            return ""
        
        # Берем последние 2-3 поста для контекста
        recent_posts = self.posts[-3:]
        context_parts = []
        
        for post in recent_posts:
            philosopher_name = PHILOSOPHERS[post['philosopher']]['name']
            content_preview = post['content'][:150] + "..." if len(post['content']) > 150 else post['content']
            context_parts.append(f"{philosopher_name}: {content_preview}")
        
        return "\n\n".join(context_parts)
    
    def should_continue(self) -> bool:
        """Определяет, стоит ли продолжать цепочку."""
        # Не продолжаем если:
        # 1. Более 5 постов в цепочке
        # 2. Последний пост более 2 дней назад
        # 3. Все доступные мыслители уже участвовали
        
        if len(self.posts) >= 5:
            return False
        
        if (datetime.now() - self.last_post_at).days > 2:
            return False
        
        if len(self.participants) >= len(get_philosopher_names()):
            return False
        
        return True
    
    def get_next_philosopher(self) -> Optional[str]:
        """Выбирает следующего мыслителя для ответа."""
        available = [p for p in get_philosopher_names() if p not in self.participants]
        
        # Если все мыслители участвовали, можем выбрать того, кто давно не отвечал
        if not available:
            # Исключаем только автора последнего поста
            last_philosopher = self.posts[-1]['philosopher'] if self.posts else None
            available = [p for p in get_philosopher_names() if p != last_philosopher]
        
        return random.choice(available) if available else None
    
    def to_dict(self) -> Dict:
        """Сериализует цепочку в словарь."""
        return {
            'thread_id': self.thread_id,
            'theme': self.theme,
            'posts': self.posts,
            'participants': list(self.participants),
            'created_at': self.created_at.isoformat(),
            'last_post_at': self.last_post_at.isoformat(),
            'is_active': self.is_active
        }

class ThreadManager:
    """Управляет всеми цепочками диалогов."""
    
    def __init__(self, max_active_threads=3):
        self.active_threads = {}  # thread_id -> DialogueThread
        self.max_active_threads = max_active_threads
        self.thread_continuation_probability = 0.7  # 70% шанс продолжить цепочку
    
    def should_start_new_thread(self) -> bool:
        """Определяет, нужно ли начинать новую цепочку или продолжить существующую."""
        active_threads = [t for t in self.active_threads.values() if t.should_continue()]
        
        # Если нет активных цепочек, обязательно начинаем новую
        if not active_threads:
            return True
        
        # Если достигли лимита активных цепочек, продолжаем существующую
        if len(active_threads) >= self.max_active_threads:
            return random.random() > self.thread_continuation_probability
        
        # Случайный выбор
        return random.random() > self.thread_continuation_probability
    
    def get_thread_to_continue(self) -> Optional[DialogueThread]:
        """Выбирает цепочку для продолжения."""
        active_threads = [t for t in self.active_threads.values() if t.should_continue()]
        
        if not active_threads:
            return None
        
        # Предпочитаем более свежие цепочки
        active_threads.sort(key=lambda t: t.last_post_at, reverse=True)
        
        # Выбираем с весами: более свежие цепочки имеют больший шанс
        weights = [1.0 / (i + 1) for i in range(len(active_threads))]
        return random.choices(active_threads, weights=weights)[0]
    
    def create_new_thread(self, theme: str = None) -> DialogueThread:
        """Создает новую цепочку диалогов."""
        from themes import POST_THEMES
        
        if not theme:
            # Избегаем недавние темы
            recent_themes = set()
            for thread in self.active_threads.values():
                recent_themes.add(thread.theme)
            
            available_themes = [t for t in POST_THEMES if t not in recent_themes]
            theme = random.choice(available_themes if available_themes else POST_THEMES)
        
        thread_id = f"thread_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{random.randint(100, 999)}"
        starter_philosopher = random.choice(get_philosopher_names())
        
        thread = DialogueThread(thread_id, theme, starter_philosopher)
        self.active_threads[thread_id] = thread
        
        logger.info(f"Создана новая цепочка: {thread_id}, тема: {theme}, автор: {starter_philosopher}")
        return thread
    
    def cleanup_old_threads(self):
        """Очищает старые неактивные цепочки."""
        to_remove = []
        for thread_id, thread in self.active_threads.items():
            if not thread.should_continue():
                thread.is_active = False
                to_remove.append(thread_id)
        
        for thread_id in to_remove:
            logger.info(f"Архивируем цепочку: {thread_id}")
            del self.active_threads[thread_id]
    
    def get_stats(self) -> Dict:
        """Возвращает статистику цепочек."""
        active_count = len([t for t in self.active_threads.values() if t.should_continue()])
        total_posts = sum(len(t.posts) for t in self.active_threads.values())
        
        themes = [t.theme for t in self.active_threads.values()]
        participants = set()
        for thread in self.active_threads.values():
            participants.update(thread.participants)
        
        return {
            'active_threads': active_count,
            'total_threads': len(self.active_threads),
            'total_posts': total_posts,
            'active_themes': themes,
            'active_participants': list(participants)
        }

class ThreadSystem:
    """Основная система управления цепочками диалогов."""
    
    def __init__(self, deepseek_client):
        self.deepseek_client = deepseek_client
        self.thread_manager = ThreadManager()
    
    async def generate_next_post(self, theme: str = None) -> Dict:
        """Генерирует следующий пост в цепочке или создает новую цепочку."""
        try:
            # Очищаем старые цепочки
            self.thread_manager.cleanup_old_threads()
            
            # Решаем: новая цепочка или продолжение
            if self.thread_manager.should_start_new_thread():
                return await self._create_starter_post(theme)
            else:
                thread = self.thread_manager.get_thread_to_continue()
                if thread:
                    return await self._create_response_post(thread)
                else:
                    return await self._create_starter_post(theme)
        
        except Exception as e:
            logger.error(f"Ошибка при генерации поста цепочки: {str(e)}")
            return None
    
    async def _create_starter_post(self, theme: str = None) -> Dict:
        """Создает пост, начинающий новую цепочку."""
        thread = self.thread_manager.create_new_thread(theme)
        philosopher = list(thread.participants)[0]
        
        # Генерируем промпт для стартового поста
        prompt = self._create_starter_prompt(philosopher, thread.theme)
        
        # Генерируем пост
        post_content = await self._generate_with_deepseek(prompt)
        
        if post_content:
            thread.add_post(philosopher, post_content, "starter")
            
            return {
                'type': 'starter',
                'thread_id': thread.thread_id,
                'philosopher': philosopher,
                'theme': thread.theme,
                'content': post_content,
                'formatted_content': self._format_starter_post(philosopher, thread.theme, post_content),
                'reply_to_message_id': None  # Стартовые посты не реплаят
            }
        
        return None
    
    async def _create_response_post(self, thread: DialogueThread) -> Dict:
        """Создает пост-ответ в существующей цепочке."""
        philosopher = thread.get_next_philosopher()
        if not philosopher:
            return await self._create_starter_post()
        
        # Получаем контекст предыдущих постов
        context = thread.get_context_for_response()
        
        # Генерируем промпт для ответа
        prompt = self._create_response_prompt(philosopher, thread.theme, context)
        
        # Генерируем ответ
        post_content = await self._generate_with_deepseek(prompt)
        
        if post_content:
            # Получаем ID последнего сообщения для реплая
            reply_to_message_id = thread.get_last_message_id()
            
            thread.add_post(philosopher, post_content, "response")
            
            return {
                'type': 'response',
                'thread_id': thread.thread_id,
                'philosopher': philosopher,
                'theme': thread.theme,
                'content': post_content,
                'context': context,
                'post_number': len(thread.posts),
                'formatted_content': self._format_response_post(philosopher, thread.theme, post_content, len(thread.posts)),
                'reply_to_message_id': reply_to_message_id  # Реплай на предыдущий пост
            }
        
        return None
    
    def _create_starter_prompt(self, philosopher: str, theme: str) -> str:
        """Создает промпт для стартового поста."""
        philosopher_info = PHILOSOPHERS[philosopher]
        
        return f"""{philosopher_info['system_prompt']}

Создай философский пост на тему: "{theme}"

Требования:
- Это начало новой дискуссии, выскажи свою позицию по теме
- Объем: 50-90 слов  
- Используй свой характерный стиль и подход
- Пост должен быть интересным и провокационным
- Можешь поставить вопросы, которые заинтересуют других мыслителей
- НЕ используй призывы к комментированию

Пиши как {philosopher_info['name']}, начинающий важную дискуссию."""
    
    def _create_response_prompt(self, philosopher: str, theme: str, context: str) -> str:
        """Создает промпт для поста-ответа."""
        philosopher_info = PHILOSOPHERS[philosopher]
        
        return f"""{philosopher_info['system_prompt']}

Ты участвуешь в дискуссии на тему: "{theme}"

Предыдущие высказывания в дискуссии:
{context}

Требования:
- Ответь на высказывания других мыслителей
- Выскажи свою позицию, опираясь на свою философскую школу
- Можешь соглашаться, возражать, дополнять
- Объем: 40-70 слов
- Будь respectful, но не бойся интеллектуального столкновения
- Можешь ссылаться на конкретные мысли собеседников

Отвечай как {philosopher_info['name']}, присоединяющийся к дискуссии."""
    
    async def _generate_with_deepseek(self, prompt: str) -> str:
        """Генерирует текст через DeepSeek API."""
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.deepseek_client.api_key}"
            }
            
            payload = {
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 150,
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
                logger.error(f"Ошибка API: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка при генерации: {str(e)}")
            return None
    
    def _format_starter_post(self, philosopher: str, theme: str, content: str) -> str:
        """Форматирует стартовый пост для Telegram."""
        philosopher_info = PHILOSOPHERS[philosopher]
        emoji = self._get_philosopher_emoji(philosopher)
        
        formatted = f"{emoji} <b>{content.split('.')[0] if '.' in content else theme.title()}</b>\n\n"
        
        # Убираем первое предложение если оно стало заголовком
        if '.' in content:
            body = '. '.join(content.split('.')[1:]).strip()
            if body.startswith('.'):
                body = body[1:].strip()
        else:
            body = content
        
        formatted += f"{body}\n\n"
        formatted += f"#философия #{theme.replace(' ', '_')} #{philosopher_info['school'].lower().replace(' ', '_').replace('-', '_')}"
        
        return formatted
    
    def _format_response_post(self, philosopher: str, theme: str, content: str, post_number: int) -> str:
        """Форматирует пост-ответ для Telegram."""
        philosopher_info = PHILOSOPHERS[philosopher]
        emoji = self._get_philosopher_emoji(philosopher)
        
        # Заголовок указывает на то, что это ответ
        if post_number == 2:
            header = f"{emoji} <b>Ответ {philosopher_info['name']}:</b>"
        else:
            header = f"{emoji} <b>{philosopher_info['name']} присоединяется:</b>"
        
        formatted = f"{header}\n\n"
        formatted += f"{content}\n\n"
        formatted += f"↩️ Продолжение дискуссии\n\n"
        formatted += f"#философия #{theme.replace(' ', '_')} #{philosopher_info['school'].lower().replace(' ', '_').replace('-', '_')} #диалог"
        
        return formatted
    
    def _get_philosopher_emoji(self, philosopher: str) -> str:
        """Возвращает эмодзи для мыслителя."""
        emoji_map = {
            'stoic': '🏛️',
            'existentialist': '🌊', 
            'zen_master': '🍃',
            'cynic': '⚡',
            'mystic': '✨'
        }
        return emoji_map.get(philosopher, '🧠')
    
    def update_message_id(self, thread_id: str, message_id: int):
        """Обновляет message_id последнего поста в цепочке после публикации."""
        thread = self.thread_manager.active_threads.get(thread_id)
        if thread:
            thread.update_last_message_id(message_id)
    
    def get_system_stats(self) -> Dict:
        """Возвращает статистику системы цепочек."""
        return self.thread_manager.get_stats() 