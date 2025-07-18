#!/usr/bin/env python3
"""
Тестовый скрипт для проверки системы диалогов мыслителей.
Позволяет тестировать функционал без запуска полного бота.
"""

import asyncio
import logging
from config import DEEPSEEK_API_KEY
from deepseek_client import DeepSeekClient
from mode_config import set_mode, PostMode, get_mode_info
from philosophers import get_philosopher_names, PHILOSOPHERS

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_classic_mode():
    """Тестирует классический режим."""
    print("\n🏛️ === ТЕСТ КЛАССИЧЕСКОГО РЕЖИМА ===")
    
    set_mode(PostMode.CLASSIC)
    mode_info = get_mode_info()
    print(f"Режим: {mode_info['name']}")
    
    client = DeepSeekClient()
    
    try:
        result = await client.generate_post("цифровое одиночество")
        if result[0]:  # post_text
            print(f"✅ Пост сгенерирован (длина: {len(result[0])} символов)")
            print(f"Тема: {result[2]}")
            print(f"Формат: {result[3]}")
            print("\nТекст поста:")
            print(result[0])
        else:
            print("❌ Не удалось сгенерировать пост")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

async def test_dialogue_mode():
    """Тестирует режим диалогов."""
    print("\n💭 === ТЕСТ РЕЖИМА ДИАЛОГОВ ===")
    
    set_mode(PostMode.DIALOGUE)
    mode_info = get_mode_info()
    print(f"Режим: {mode_info['name']}")
    
    client = DeepSeekClient()
    
    try:
        result = await client.generate_post("страх будущего")
        if result[0]:  # post_text
            print(f"✅ Диалог сгенерирован (длина: {len(result[0])} символов)")
            print(f"Тема: {result[2]}")
            print(f"Формат: {result[3]}")
            print("\nТекст диалога:")
            print(result[0])
        else:
            print("❌ Не удалось сгенерировать диалог")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

async def test_dialogue_system_directly():
    """Тестирует систему диалогов напрямую."""
    print("\n🎭 === ПРЯМОЙ ТЕСТ СИСТЕМЫ ДИАЛОГОВ ===")
    
    client = DeepSeekClient()
    dialogue_system = client.get_dialogue_system()
    
    try:
        dialogue = await dialogue_system.create_full_dialogue("эмоциональное выгорание")
        
        if dialogue:
            print(f"✅ Диалог создан между: {dialogue['participants']}")
            print(f"Тема: {dialogue['theme']}")
            print(f"Участники: {[PHILOSOPHERS[p]['name'] for p in dialogue['participants']]}")
            
            print("\n--- Введение ---")
            print(dialogue['opening'])
            
            print("\n--- Диалог ---")
            for i, exchange in enumerate(dialogue['exchanges']):
                speaker_name = PHILOSOPHERS[exchange['speaker']]['name']
                print(f"\n{speaker_name}:")
                print(exchange['text'])
            
            print("\n--- Форматированная версия для Telegram ---")
            formatted = dialogue_system.format_dialogue_for_telegram(dialogue)
            print(formatted)
            
        else:
            print("❌ Не удалось создать диалог")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

async def test_philosophers_info():
    """Показывает информацию о мыслителях."""
    print("\n🧠 === ИНФОРМАЦИЯ О МЫСЛИТЕЛЯХ ===")
    
    for key in get_philosopher_names():
        philosopher = PHILOSOPHERS[key]
        emoji = {
            'stoic': '🏛️',
            'existentialist': '🌊', 
            'zen_master': '🍃',
            'cynic': '⚡',
            'mystic': '✨'
        }.get(key, '🧠')
        
        print(f"\n{emoji} {philosopher['name']}")
        print(f"Школа: {philosopher['school']}")
        print(f"Подход: {philosopher['approach']}")
        print(f"Примеры фраз: {', '.join(philosopher['typical_phrases'][:2])}")

async def test_multiple_dialogues():
    """Тестирует создание нескольких диалогов для проверки разнообразия."""
    print("\n🔄 === ТЕСТ МНОЖЕСТВЕННЫХ ДИАЛОГОВ ===")
    
    set_mode(PostMode.DIALOGUE)
    client = DeepSeekClient()
    dialogue_system = client.get_dialogue_system()
    
    themes = ["одиночество", "свобода выбора", "смысл жизни"]
    
    for i, theme in enumerate(themes, 1):
        print(f"\n--- Диалог {i}: {theme} ---")
        try:
            dialogue = await dialogue_system.create_full_dialogue(theme)
            if dialogue:
                participants = [PHILOSOPHERS[p]['name'] for p in dialogue['participants']]
                print(f"Участники: {' и '.join(participants)}")
                print(f"Длина текста: {len(dialogue_system.format_dialogue_for_telegram(dialogue))} символов")
            else:
                print("❌ Не удалось создать диалог")
        except Exception as e:
            print(f"❌ Ошибка: {e}")
    
    # Показываем статистику
    try:
        stats = dialogue_system.get_dialogue_stats()
        print(f"\n📊 Статистика:")
        print(f"Всего диалогов: {stats['total']}")
        print(f"Активность мыслителей: {stats['active_philosophers']}")
    except Exception as e:
        print(f"❌ Ошибка при получении статистики: {e}")

async def main():
    """Основная функция тестирования."""
    print("🚀 === ТЕСТИРОВАНИЕ СИСТЕМЫ ДИАЛОГОВ МЫСЛИТЕЛЕЙ ===")
    
    # Проверяем наличие API ключа
    if not DEEPSEEK_API_KEY or DEEPSEEK_API_KEY == "your_deepseek_api_key_here":
        print("❌ DeepSeek API ключ не настроен!")
        print("Добавьте DEEPSEEK_API_KEY в файл .env")
        return
    
    print(f"✅ API ключ настроен: {DEEPSEEK_API_KEY[:10]}...")
    
    # Информация о мыслителях
    await test_philosophers_info()
    
    # Тест классического режима
    await test_classic_mode()
    
    # Тест режима диалогов
    await test_dialogue_mode()
    
    # Прямой тест системы диалогов
    await test_dialogue_system_directly()
    
    # Тест множественных диалогов
    await test_multiple_dialogues()
    
    print("\n✅ === ТЕСТИРОВАНИЕ ЗАВЕРШЕНО ===")

if __name__ == "__main__":
    asyncio.run(main()) 