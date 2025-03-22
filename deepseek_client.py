"""
Клиент для работы с DeepSeek API для генерации текста.
"""

import requests
import json
import logging
import time
import random
import uuid
from datetime import datetime
from config import DEEPSEEK_API_KEY
from prompt_template import DEEPSEEK_PROMPT, DEEPSEEK_API_PARAMS, POST_THEMES, POST_FORMATS, POST_ENDINGS

# Настройка логирования
logger = logging.getLogger('deepseek_client')
logger.setLevel(logging.INFO)

class DeepSeekClient:
    """Клиент для работы с DeepSeek API."""
    
    def __init__(self):
        self.api_key = DEEPSEEK_API_KEY
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        self.prompt_template = DEEPSEEK_PROMPT
        self.api_params = DEEPSEEK_API_PARAMS.copy()  # Создаем копию, чтобы не модифицировать оригинал
        self.last_themes = []  # Хранение последних тем для избегания повторений
        self.last_formats = [] # Хранение последних форматов для избегания повторений
        
        if not self.api_key or self.api_key == "your_deepseek_api_key_here":
            logger.error("DeepSeek API ключ не настроен. Пожалуйста, добавьте его в .env файл.")
            raise ValueError("DeepSeek API ключ не настроен")
    
    def _get_random_with_history(self, options, history, max_history=3):
        """Выбирает случайный элемент, избегая недавно использованных."""
        available_options = [opt for opt in options if opt not in history]
        
        # Если все опции уже были использованы, просто выбираем случайную
        if not available_options:
            chosen = random.choice(options)
        else:
            chosen = random.choice(available_options)
        
        # Обновляем историю
        history.append(chosen)
        if len(history) > max_history:
            history.pop(0)  # Удаляем самый старый элемент
        
        return chosen
    
    def generate_post(self):
        """Генерирует пост, используя DeepSeek API."""
        try:
            # Создаем случайные вариации для большего разнообразия, избегая повторений
            theme = self._get_random_with_history(POST_THEMES, self.last_themes)
            format_type = self._get_random_with_history(POST_FORMATS, self.last_formats)
            ending = random.choice(POST_ENDINGS)
            
            # Случайно варьируем temperature для каждого запроса (в пределах разумного)
            temperature = self.api_params["temperature"] + random.uniform(-0.15, 0.1)
            temperature = max(0.5, min(temperature, 1.0))  # Ограничиваем от 0.5 до 1.0
            
            # Аналогично для других параметров
            top_p = self.api_params["top_p"] + random.uniform(-0.05, 0.05)
            top_p = max(0.8, min(top_p, 0.98))
            
            presence_penalty = self.api_params["presence_penalty"] + random.uniform(-0.1, 0.1)
            presence_penalty = max(0.4, min(presence_penalty, 0.9))
            
            frequency_penalty = self.api_params["frequency_penalty"] + random.uniform(-0.1, 0.1)
            frequency_penalty = max(0.4, min(frequency_penalty, 0.9))
            
            # Создаем уникальный идентификатор запроса
            request_id = str(uuid.uuid4())[:8]
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Заполняем шаблон промпта с вариациями
            prompt = self.prompt_template.format(
                theme=theme,
                format=format_type,
                ending=ending,
                timestamp=timestamp,
                request_id=request_id
            )
            
            # Подготавливаем запрос с измененными параметрами
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            # Копируем параметры и модифицируем их для большего разнообразия
            request_params = self.api_params.copy()
            request_params["temperature"] = temperature
            request_params["top_p"] = top_p
            request_params["presence_penalty"] = presence_penalty
            request_params["frequency_penalty"] = frequency_penalty
            
            payload = {
                "messages": [{"role": "user", "content": prompt}],
                **request_params
            }
            
            # Отправляем запрос к API
            logger.info(f"Отправка запроса к DeepSeek API (ID: {request_id}, Тема: {theme}, Формат: {format_type}, Завершение: {ending})...")
            response = requests.post(
                self.api_url, 
                headers=headers, 
                data=json.dumps(payload)
            )
            
            # Обрабатываем ответ
            if response.status_code == 200:
                result = response.json()
                generated_text = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                if not generated_text:
                    logger.error("Пустой ответ от DeepSeek API.")
                    return None
                
                logger.info(f"Успешно сгенерирован пост (ID: {request_id}, {len(generated_text)} символов)")
                return generated_text
            else:
                logger.error(f"Ошибка при запросе к DeepSeek API: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Исключение при генерации поста: {str(e)}")
            return None
    
    def generate_posts_batch(self, count=1, retry_attempts=3, retry_delay=5):
        """Генерирует несколько постов с возможностью повторных попыток."""
        posts = []
        
        for i in range(count):
            for attempt in range(retry_attempts):
                post = self.generate_post()
                
                if post:
                    posts.append(post)
                    break
                else:
                    logger.warning(f"Попытка {attempt+1}/{retry_attempts} не удалась. Ожидание {retry_delay} секунд...")
                    time.sleep(retry_delay)
            
            # Небольшая пауза между запросами для избежания превышения лимитов API
            if i < count - 1:
                time.sleep(3)  # Увеличиваем паузу между запросами
        
        return posts


# Пример использования
if __name__ == "__main__":
    # Настройка логирования для примера
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Тестирование клиента
    client = DeepSeekClient()
    post = client.generate_post()
    
    if post:
        print("\nСгенерированный пост:")
        print("-" * 40)
        print(post)
        print("-" * 40)
    else:
        print("Не удалось сгенерировать пост.") 