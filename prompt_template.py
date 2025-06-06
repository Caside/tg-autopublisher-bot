"""
Этот файл содержит шаблон промпта для генерации постов с помощью DeepSeek API.
Вы можете изменить его в соответствии с вашими потребностями.
"""

import random
from themes import POST_THEMES

# Список форматов для постов
POST_FORMATS = [
    "афористичное наблюдение",
    "микро-эссе",
    "мысленный эксперимент",
    "метафорическое сравнение",
    "научная гипотеза",
    "философский вопрос",
    "когнитивный инсайт",
    "культурный анализ",
    "поведенческий паттерн",
    "системное наблюдение",
    "этическая дилемма",
    "футуристический сценарий",
    "психологический принцип",
    "социальный феномен",
    "лингвистический парадокс",
    "архетипический образ",
    "символическое толкование",
    "когнитивное искажение",
    "нейрофизиологический факт",
    "цифровая метафора"
]

# Список вариантов завершения постов (без призывов к комментированию)
POST_ENDINGS = [
    "завершить открытым вопросом",
    "завершить неожиданным выводом",
    "завершить метафорой",
    "завершить парадоксом",
    "завершить инсайтом",
    "завершить гипотезой",
    "завершить наблюдением",
    "завершить принципом",
    "завершить аналогией",
    "завершить закономерностью",
    "завершить противоречием",
    "завершить перспективой",
    "завершить паттерном",
    "завершить феноменом",
    "завершить концепцией",
    "завершить парадигмой",
    "завершить архетипом",
    "завершить символом",
    "завершить принципом",
    "завершить метафорой"
]

def generate_random_seed():
    """Генерирует случайное число для уникализации промпта."""
    return random.randint(1000, 9999)

# Шаблон для генерации постов
DEEPSEEK_PROMPT = """
Сгенерируй пост для публикации в телеграм-канале на тему {theme}.
Пост должен быть в формате: {format}.

Длина: 450-600 символов.

Важные инструкции:
- Используй разговорный, но культурный стиль
- Создавай яркие, запоминающиеся образы и метафоры
- Добавляй элемент неожиданности или абсурда
- Используй контрасты и парадоксы для усиления эффекта
- Включай эмоциональные триггеры (удивление, инсайт, юмор, тревога)
- Создавай ощущение "момента истины" или "открытия"
- Используй необычные сравнения и аналогии
- Добавляй элементы сторителлинга
- Заканчивай сильным, запоминающимся образом
- Используй HTML-форматирование для выделения текста:
  - Заголовок выделяй тегом <b>жирным</b>
  - Важные термины и ключевые моменты выделяй тегом <i>курсивом</i>
- {ending}

Случайное число для уникализации: {random_seed}

ВАЖНО: В канале ОТКЛЮЧЕНЫ комментарии, поэтому НЕ ПРИЗЫВАЙ к обсуждению, комментированию, 
и не задавай вопросы предполагающие ответ в комментариях.
"""

# Диапазоны параметров для API запроса
DEEPSEEK_API_PARAM_RANGES = {
    "temperature": (0.7, 1.0),        # Диапазон температуры для разнообразия
    "top_p": (0.9, 0.98),             # Диапазон top_p для разнообразия
    "presence_penalty": (0.5, 0.9),   # Диапазон штрафа за присутствие
    "frequency_penalty": (0.6, 1.0)   # Диапазон штрафа за частоту
}

# Базовые параметры для API запроса
DEEPSEEK_API_PARAMS = {
    "model": "deepseek-chat",  # Можно заменить на другую модель DeepSeek
    "max_tokens": 600,         # Уменьшенная максимальная длина ответа
    "stream": False,           # Не использовать потоковую передачу для ответа
}
