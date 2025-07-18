#!/usr/bin/env python3
"""
Тестовый скрипт для проверки системы цепочек диалогов.
Позволяет тестировать новый функционал создания последовательных постов-ответов.
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

async def test_thread_system_basics():
    """Тестирует базовую функциональность системы цепочек."""
    print("\n🧵 === ТЕСТ СИСТЕМЫ ЦЕПОЧЕК ===")
    
    set_mode(PostMode.THREADS)
    mode_info = get_mode_info()
    print(f"Режим: {mode_info['name']}")
    
    client = DeepSeekClient()
    thread_system = client.get_thread_system()
    
    try:
        # Тест создания первого поста (стартер)
        print("\n--- Создание стартового поста ---")
        post = await thread_system.generate_next_post("цифровая зависимость")
        
        if post:
            print(f"✅ Стартовый пост создан")
            print(f"Тип: {post['type']}")
            print(f"Мыслитель: {PHILOSOPHERS[post['philosopher']]['name']}")
            print(f"Тема: {post['theme']}")
            print(f"ID цепочки: {post['thread_id']}")
            print(f"\nТекст поста:")
            print(post['formatted_content'])
        else:
            print("❌ Не удалось создать стартовый пост")
            return
        
        # Тест создания ответного поста
        print("\n--- Создание ответного поста ---")
        response_post = await thread_system.generate_next_post()
        
        if response_post:
            print(f"✅ Ответный пост создан")
            print(f"Тип: {response_post['type']}")
            print(f"Мыслитель: {PHILOSOPHERS[response_post['philosopher']]['name']}")
            print(f"Номер поста: {response_post.get('post_number', 'N/A')}")
            print(f"\nТекст ответа:")
            print(response_post['formatted_content'])
        else:
            print("❌ Не удалось создать ответный пост")
        
        # Показываем статистику
        print("\n--- Статистика цепочек ---")
        stats = thread_system.get_system_stats()
        print(f"Активных цепочек: {stats['active_threads']}")
        print(f"Всего постов: {stats['total_posts']}")
        print(f"Активные темы: {stats['active_themes']}")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

async def test_multiple_threads():
    """Тестирует создание нескольких цепочек диалогов."""
    print("\n🔄 === ТЕСТ МНОЖЕСТВЕННЫХ ЦЕПОЧЕК ===")
    
    set_mode(PostMode.THREADS)
    client = DeepSeekClient()
    thread_system = client.get_thread_system()
    
    themes = ["одиночество в городе", "искусственный интеллект", "смысл творчества"]
    
    for i, theme in enumerate(themes, 1):
        print(f"\n--- Цепочка {i}: {theme} ---")
        try:
            post = await thread_system.generate_next_post(theme)
            if post:
                philosopher_name = PHILOSOPHERS[post['philosopher']]['name']
                print(f"✅ Создана цепочка от {philosopher_name}")
                print(f"Длина поста: {len(post['formatted_content'])} символов")
            else:
                print("❌ Не удалось создать цепочку")
        except Exception as e:
            print(f"❌ Ошибка: {e}")
    
    # Показываем финальную статистику
    try:
        stats = thread_system.get_system_stats()
        print(f"\n📊 Итоговая статистика:")
        print(f"Активных цепочек: {stats['active_threads']}")
        print(f"Всего цепочек: {stats['total_threads']}")
        print(f"Всего постов: {stats['total_posts']}")
        print(f"Участники: {[PHILOSOPHERS[p]['name'] for p in stats['active_participants']]}")
    except Exception as e:
        print(f"❌ Ошибка при получении статистики: {e}")

async def test_conversation_flow():
    """Тестирует полноценный поток диалога с несколькими ответами."""
    print("\n💬 === ТЕСТ ПОТОКА ДИАЛОГА ===")
    
    set_mode(PostMode.THREADS)
    client = DeepSeekClient()
    thread_system = client.get_thread_system()
    
    # Создаем стартовый пост
    print("Создаем стартовый пост...")
    starter_post = await thread_system.generate_next_post("природа времени")
    
    if not starter_post:
        print("❌ Не удалось создать стартовый пост")
        return
    
    print(f"✅ Стартовый пост от {PHILOSOPHERS[starter_post['philosopher']]['name']}")
    
    # Создаем несколько ответов
    for i in range(3):
        print(f"\nСоздаем ответ #{i+1}...")
        response_post = await thread_system.generate_next_post()
        
        if response_post and response_post['type'] == 'response':
            philosopher_name = PHILOSOPHERS[response_post['philosopher']]['name']
            print(f"✅ Ответ #{response_post['post_number']} от {philosopher_name}")
            
            # Показываем краткий контекст
            if 'context' in response_post:
                context_lines = response_post['context'].split('\n')[:2]
                print(f"Контекст: {context_lines[0][:100]}...")
        else:
            print(f"⚠️ Попытка #{i+1}: создан новый стартовый пост вместо ответа")
            if response_post:
                print(f"От {PHILOSOPHERS[response_post['philosopher']]['name']} на тему '{response_post['theme']}'")
    
    # Финальная статистика цепочки
    stats = thread_system.get_system_stats()
    print(f"\n📊 Результат:")
    print(f"Активных цепочек: {stats['active_threads']}")
    print(f"Всего постов в сессии: {stats['total_posts']}")

async def test_thread_vs_dialogue_modes():
    """Сравнивает режимы цепочек и обычных диалогов."""
    print("\n⚖️ === СРАВНЕНИЕ РЕЖИМОВ ===")
    
    client = DeepSeekClient()
    theme = "свобода и ответственность"
    
    # Тест режима цепочек
    print("--- Режим цепочек ---")
    set_mode(PostMode.THREADS)
    try:
        thread_result = await client.generate_post(theme)
        if thread_result[0]:
            print(f"✅ Цепочка: {thread_result[3]} - {len(thread_result[0])} символов")
            print(f"Первые 100 символов: {thread_result[0][:100]}...")
        else:
            print("❌ Не удалось создать пост цепочки")
    except Exception as e:
        print(f"❌ Ошибка в режиме цепочек: {e}")
    
    # Тест режима диалогов
    print("\n--- Режим диалогов ---")
    set_mode(PostMode.DIALOGUE)
    try:
        dialogue_result = await client.generate_post(theme)
        if dialogue_result[0]:
            print(f"✅ Диалог: {dialogue_result[3]} - {len(dialogue_result[0])} символов")
            print(f"Первые 100 символов: {dialogue_result[0][:100]}...")
        else:
            print("❌ Не удалось создать диалог")
    except Exception as e:
        print(f"❌ Ошибка в режиме диалогов: {e}")
    
    # Тест классического режима
    print("\n--- Классический режим ---")
    set_mode(PostMode.CLASSIC)
    try:
        classic_result = await client.generate_post(theme)
        if classic_result[0]:
            print(f"✅ Классика: {classic_result[3]} - {len(classic_result[0])} символов")
            print(f"Первые 100 символов: {classic_result[0][:100]}...")
        else:
            print("❌ Не удалось создать классический пост")
    except Exception as e:
        print(f"❌ Ошибка в классическом режиме: {e}")

async def test_thread_persistence():
    """Тестирует постоянство и управление цепочками."""
    print("\n💾 === ТЕСТ ПОСТОЯНСТВА ЦЕПОЧЕК ===")
    
    set_mode(PostMode.THREADS)
    client = DeepSeekClient()
    thread_system = client.get_thread_system()
    
    # Создаем несколько цепочек
    themes = ["время", "память", "идентичность"]
    created_threads = []
    
    for theme in themes:
        post = await thread_system.generate_next_post(theme)
        if post:
            created_threads.append(post['thread_id'])
            print(f"✅ Создана цепочка {post['thread_id']} на тему '{theme}'")
    
    print(f"\nСоздано цепочек: {len(created_threads)}")
    
    # Тестируем продолжение существующих цепочек
    print("\nТестируем продолжение цепочек...")
    for i in range(5):
        post = await thread_system.generate_next_post()
        if post:
            if post['type'] == 'response':
                print(f"✅ Ответ в цепочке {post['thread_id']} (пост #{post['post_number']})")
            else:
                print(f"✅ Новая цепочка {post['thread_id']} на тему '{post['theme']}'")
        else:
            print(f"❌ Ошибка при создании поста #{i+1}")
    
    # Статистика
    stats = thread_system.get_system_stats()
    print(f"\n📊 Финальная статистика:")
    print(f"Активных цепочек: {stats['active_threads']}")
    print(f"Всего цепочек: {stats['total_threads']}")
    print(f"Всего постов: {stats['total_posts']}")

async def main():
    """Основная функция тестирования."""
    print("🚀 === ТЕСТИРОВАНИЕ СИСТЕМЫ ЦЕПОЧЕК ДИАЛОГОВ ===")
    
    # Проверяем наличие API ключа
    if not DEEPSEEK_API_KEY or DEEPSEEK_API_KEY == "your_deepseek_api_key_here":
        print("❌ DeepSeek API ключ не настроен!")
        print("Добавьте DEEPSEEK_API_KEY в файл .env")
        return
    
    print(f"✅ API ключ настроен: {DEEPSEEK_API_KEY[:10]}...")
    
    # Базовые тесты
    await test_thread_system_basics()
    
    # Тесты множественных цепочек
    await test_multiple_threads()
    
    # Тест потока диалога
    await test_conversation_flow()
    
    # Сравнение режимов
    await test_thread_vs_dialogue_modes()
    
    # Тест постоянства
    await test_thread_persistence()
    
    print("\n✅ === ТЕСТИРОВАНИЕ ЗАВЕРШЕНО ===")

if __name__ == "__main__":
    asyncio.run(main()) 