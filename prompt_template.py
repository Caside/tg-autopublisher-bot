"""
Этот файл содержит шаблон промпта для генерации постов с помощью DeepSeek API.
Вы можете изменить его в соответствии с вашими потребностями.
"""

from themes import POST_THEMES

# Список форматов для постов
POST_FORMATS = [
    "короткое глубокое размышление",
    "юмористическое наблюдение",
    "вдохновляющий совет",
    "парадоксальный вопрос",
    "метафорическую историю",
    "абсурдно-бюрократическая инструкция",
    "практический совет с юмором",
    "философскую мысль в современном контексте",
    "ироничное наблюдение из повседневной жизни",
    "мысленный эксперимент",
    "абсурдную логику, приводящую к неожиданной мудрости",
    "размышление об очевидном, но незамеченном",
    "короткое опровержение распространенного мифа",
    "саркастичный чек-лист",
    "диалог с внутренним критиком",
    "едкое наблюдение о типичных ошибках"
]

# Список вариантов завершения постов (без призывов к комментированию)
POST_ENDINGS = [
    "завершить сильным утверждением",
    "завершить запоминающейся фразой",
    "завершить риторическим вопросом для размышления",
    "завершить неожиданным поворотом мысли",
    "завершить тонкой иронией",
    "завершить приглашением к внутреннему диалогу",
    "завершить мысль парадоксом",
    "завершить игрой слов",
    "завершить метафорой",
    "завершить указанием на неочевидное следствие",
    "завершить легкой провокационной мыслью",
    "завершить саркастическим афоризмом",
    "завершить циничным выводом",
    "завершить тонким намёком на абсурдность ситуации"
]

# Шаблон для генерации постов
DEEPSEEK_PROMPT = """
Сгенерируй пост для публикации в телеграм-канале на тему {theme}.
Пост должен быть в формате: {format}.

Длина: 225-375 символов.

Важные инструкции:
- Используй разговорный, но культурный стиль
- Избегай банальных фраз и избитых выражений
- Будь оригинальным, не повторяй шаблонные мысли
- Предложи идею, которую можно применить
- Включи элемент неожиданности или новой перспективы
- Используй HTML-форматирование для выделения текста:
  - Заголовок выделяй тегом <b>жирным</b>
  - Важные термины и ключевые моменты выделяй тегом <i>курсивом</i>
- {ending}

ВАЖНО: В канале ОТКЛЮЧЕНЫ комментарии, поэтому НЕ ПРИЗЫВАЙ к обсуждению, комментированию, 
и не задавай вопросы предполагающие ответ в комментариях.
"""

# Параметры для API запроса
DEEPSEEK_API_PARAMS = {
    "model": "deepseek-chat",  # Можно заменить на другую модель DeepSeek
    "temperature": 0.9,        # Высокая температура для максимального разнообразия
    "max_tokens": 600,         # Уменьшенная максимальная длина ответа
    "top_p": 0.94,             # Увеличенный параметр для большего разнообразия
    "stream": False,           # Не использовать потоковую передачу для ответа
    "presence_penalty": 0.7,   # Штраф за повторение уже использованных токенов
    "frequency_penalty": 0.8   # Штраф за повторение часто используемых токенов
}
