"""
Этот файл содержит шаблон промпта для генерации постов с помощью DeepSeek API.
Вы можете изменить его в соответствии с вашими потребностями.
"""

from themes import POST_THEMES

# Список форматов для постов
POST_FORMATS = [
    "когнитивное откровение в стиле твита",
    "псевдонаучное объяснение внутреннего конфликта",
    "молчаливая манифестация экзистенциальной тревоги",
    "сравнение философского вопроса с бытовой ситуацией",
    "культурный нейро-факт с непрошенным выводом",
    "внутренний монолог цифрового шамана",
    "мини-сценка в духе чёрного зеркала",
    "поэтическая декомпозиция абсурдной идеи",
    "утопический прогноз, который выглядит как сатира",
    "краткий инструктаж по выживанию в ментальной симуляции",
    "диалог между архетипами (например, Тень и Эго)",
    "разрушение иллюзии через бытовой пример",
    "история из будущего, в которой всё пошло не так",
    "обращение от лица алгоритма к своему пользователю",
    "сенсорное описание абстрактного понятия",
    "мысленный эксперимент с катастрофическим результатом",
    "ироничная переписка с подсознанием",
    "бессмысленная инструкция, в которой проявляется смысл",
    "сравнение человеческого поведения с багом в коде",
    "циничный афоризм в псевдо-коучинговом тоне"
]

# Список вариантов завершения постов (без призывов к комментированию)
POST_ENDINGS = [
    "завершить эффектом недосказанности",
    "завершить внутренним парадоксом без комментариев",
    "завершить неожиданной сменой тона",
    "завершить как будто это был сон",
    "завершить фразой, которую читатель не сможет забыть (и не поймёт почему)",
    "завершить поддельной уверенностью в абсурдной истине",
    "завершить цитатой, которую никто не сможет найти",
    "завершить пафосом на грани неловкости",
    "завершить так, будто это был тизер к продолжению",
    "завершить указанием на банальность, от которой хочется плакать",
    "завершить иллюзией глубокого смысла",
    "завершить будто это последняя строчка письма самому себе из прошлого",
    "завершить обрывом мысли на пике напряжения",
    "завершить ультралаконично, как будто всё сказано одним словом",
    "завершить ощущением, что читатель что-то упустил",
    "завершить как будто речь идёт совсем не о том, о чём был текст",
    "завершить намёком на несуществующую концепцию",
    "завершить так, будто текст не должен был быть опубликован",
    "завершить шёпотом, который слышен в голове",
    "завершить мета-комментарием, ломающим четвёртую стену"
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
