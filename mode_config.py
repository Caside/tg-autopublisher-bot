"""
Конфигурация режимов работы бота.
Позволяет переключаться между классическими постами и диалогами мыслителей.
"""

import os

# Режимы работы бота
class PostMode:
    CLASSIC = "classic"        # Старый режим с одиночными постами
    DIALOGUE = "dialogue"      # Режим с диалогами мыслителей (в одном посте)
    THREADS = "threads"        # Режим с цепочками диалогов (отдельные посты)
    MIXED = "mixed"           # Смешанный режим (50/50)

# Текущий режим (можно переопределить через переменную окружения)
CURRENT_MODE = os.getenv('POST_MODE', PostMode.THREADS)

# Настройки для каждого режима
MODE_CONFIG = {
    PostMode.CLASSIC: {
        "name": "Классические посты",
        "description": "Одиночные философские посты в оригинальном стиле",
        "use_dialogues": False,
        "dialogue_probability": 0.0
    },
    
    PostMode.DIALOGUE: {
        "name": "Диалоги мыслителей",
        "description": "Философские дискуссии между мыслителями разных школ",
        "use_dialogues": True,
        "dialogue_probability": 1.0
    },
    
    PostMode.THREADS: {
        "name": "Цепочки диалогов",
        "description": "Последовательные посты-ответы между мыслителями во времени",
        "use_threads": True,
        "use_dialogues": False,
        "dialogue_probability": 0.0
    },
    
    PostMode.MIXED: {
        "name": "Смешанный режим",
        "description": "50% диалоги, 50% классические посты",
        "use_dialogues": True,
        "dialogue_probability": 0.5
    }
}

def get_current_mode_config():
    """Возвращает конфигурацию текущего режима."""
    return MODE_CONFIG.get(CURRENT_MODE, MODE_CONFIG[PostMode.CLASSIC])

def is_dialogue_mode():
    """Проверяет, включен ли режим диалогов."""
    config = get_current_mode_config()
    if not config.get('use_dialogues', False):
        return False
    
    if config['dialogue_probability'] == 1.0:
        return True
    elif config['dialogue_probability'] == 0.0:
        return False
    else:
        # Смешанный режим - случайный выбор
        import random
        return random.random() < config['dialogue_probability']

def is_threads_mode():
    """Проверяет, включен ли режим цепочек диалогов."""
    config = get_current_mode_config()
    return config.get('use_threads', False)

def set_mode(mode: str):
    """Устанавливает режим работы (для тестирования)."""
    global CURRENT_MODE
    if mode in MODE_CONFIG:
        CURRENT_MODE = mode
        return True
    return False

def get_available_modes():
    """Возвращает список доступных режимов."""
    return list(MODE_CONFIG.keys())

def get_mode_info(mode: str = None):
    """Возвращает информацию о режиме."""
    if mode is None:
        mode = CURRENT_MODE
    
    config = MODE_CONFIG.get(mode)
    if not config:
        return None
    
    return {
        "mode": mode,
        "name": config["name"],
        "description": config["description"],
        "is_current": mode == CURRENT_MODE
    } 