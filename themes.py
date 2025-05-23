"""
Модуль для управления темами постов.
Темы могут быть загружены из переменных окружения или использованы по умолчанию.
"""

import os
import json

# Темы по умолчанию
DEFAULT_THEMES = [
    "Память как редактор: что, если воспоминания выживают за счёт своей драматургии?",
    "Сознание без наблюдателя: возможно ли «я», если никто не фиксирует его наличие?",
    "Нейроэкономика веры: почему мозгу выгодно верить в невыгодное?",
    "Алгоритмы идентичности: кто мы, если нас описывают через паттерны поведения?",
    "Функция скуки в эпоху постоянной стимуляции",
    "Цифровой стыд: почему мы ощущаем вину за то, что видят алгоритмы?",
    "Информационная гомеопатия: может ли микродоза смысла лечить хаос?",
    "Иллюзия выбора между иллюзиями: UX мышления в реальности",
    "Парадокс внутренней монетизации: что остаётся от “я” после личного бренда?",
    "Когнитивная синестезия: как запах новостей влияет на вкус реальности",
    "Цифровое просветление и синдром постоянного апдейта",
    "Нейропластичность как философский приговор: нет стабильного 'я'",
    "Психологический фоновый шум: как интернет изменил молчание",
    "Чувство времени после лайка: когда момент перестаёт быть настоящим",
    "Археология будущего: что останется от нас в сознании ИИ?",
    "Сакрализация хаоса: как культ неопределённости стал нормой",
    "Психоанализ в формате сторис: разбор себя за 15 секунд",
    "Самоидентификация как пользовательское соглашение",
    "Можно ли ощущать подлинность в эпоху нейросетевого лицемерия?",
    "Когнитивное выгорание как культурный ритуал постиронии"
]

def get_themes():
    """
    Получает темы из переменной окружения POST_THEMES или возвращает темы по умолчанию.
    Если POST_THEMES установлена, она должна быть JSON-строкой с массивом тем.
    """
    themes_env = os.getenv('POST_THEMES')
    if themes_env:
        try:
            return json.loads(themes_env)
        except json.JSONDecodeError:
            print("Ошибка: POST_THEMES содержит некорректный JSON. Используются темы по умолчанию.")
            return DEFAULT_THEMES
    return DEFAULT_THEMES

# Экспортируем список тем
POST_THEMES = get_themes() 