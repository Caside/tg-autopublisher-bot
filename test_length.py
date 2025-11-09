#!/usr/bin/env python3
"""
Тестовый скрипт для проверки длины генерируемых постов
"""

import asyncio
import logging
import sys
import os

# Добавляем текущую директорию в путь для импорта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from deepseek_client import DeepSeekClient

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

async def test_post_length():
    """Тестирует длину генерируемых постов"""
    try:
        client = DeepSeekClient()

        print("🧪 Тестирование генерации гибридного поста...")

        # Генерируем пост
        post, prompt, headlines = await client.generate_hybrid_post()

        if post:
            print(f"\n📊 РЕЗУЛЬТАТЫ ТЕСТА:")
            print(f"Общая длина поста: {len(post)} символов")

            # Разделяем на секции
            sections = post.split('\n\n')
            if len(sections) >= 2:
                headlines_section = sections[0]
                commentary_section = sections[1] if len(sections) > 1 else ""

                print(f"Длина секции заголовков: {len(headlines_section)} символов")
                print(f"Длина философского комментария: {len(commentary_section)} символов")

                # Проверяем требование 600-700 символов для комментария
                if len(commentary_section) <= 700:
                    print("✅ Комментарий в пределах 700 символов")
                else:
                    print("❌ Комментарий превышает 700 символов")

            print(f"\n📝 СГЕНЕРИРОВАННЫЙ ПОСТ:")
            print("-" * 50)
            print(post)
            print("-" * 50)

            print(f"\n🔍 ЗАГОЛОВКИ ИСПОЛЬЗОВАНЫ:")
            for i, headline in enumerate(headlines, 1):
                print(f"{i}. {headline}")

        else:
            print("❌ Ошибка генерации поста")

    except Exception as e:
        print(f"❌ Ошибка: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_post_length())