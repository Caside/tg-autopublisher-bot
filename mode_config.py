"""
Конфигурация режимов работы бота.
Теперь поддерживается только классический режим генерации постов.
"""

import os

# Режимы работы бота
class PostMode:
    CLASSIC = "classic"        # Единственный поддерживаемый режим

# Текущий режим (всегда classic)
CURRENT_MODE = PostMode.CLASSIC

# Настройки для классического режима
MODE_CONFIG = {
    PostMode.CLASSIC: {
        "name": "Классические посты",
        "description": "Одиночные философские посты в оригинальном стиле",
        "use_dialogues": False,
        "dialogue_probability": 0.0
    }
}

def get_current_mode_config():
    """Возвращает конфигурацию текущего режима."""
    return MODE_CONFIG[PostMode.CLASSIC]

def is_dialogue_mode():
    """Проверяет, включен ли режим диалогов. Всегда False для classic режима."""
    return False

def is_threads_mode():
    """Проверяет, включен ли режим цепочек диалогов. Всегда False для classic режима."""
    return False

def set_mode(mode: str):
    """Устанавливает режим работы. Принимает только 'classic'."""
    return mode == PostMode.CLASSIC

def get_available_modes():
    """Возвращает список доступных режимов."""
    return [PostMode.CLASSIC]

def get_mode_info(mode: str = None):
    """Возвращает информацию о режиме."""
    if mode is None or mode == PostMode.CLASSIC:
        config = MODE_CONFIG[PostMode.CLASSIC]
        return {
            "mode": PostMode.CLASSIC,
            "name": config["name"],
            "description": config["description"],
            "is_current": True
        }
    
    return None 