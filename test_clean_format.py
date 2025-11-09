#!/usr/bin/env python3
"""
Тест чистого форматирования LLM части без эмодзи
"""

import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from deepseek_client import DeepSeekClient

async def test_clean_format():
    """Проверяет отсутствие форматирования в LLM части"""
    try:
        client = DeepSeekClient()

        print("🧹 ТЕСТ ЧИСТОГО ФОРМАТИРОВАНИЯ")
        print("=" * 40)

        post, prompt, headlines = await client.generate_hybrid_post(force_refresh=True)

        if post:
            print(f"\n📝 РЕЗУЛЬТАТ ({len(post)} символов):")
            print("-" * 40)
            print(post)
            print("-" * 40)

            # Анализируем структуру
            sections = post.split('\n\n')

            if len(sections) >= 2:
                headlines_section = sections[0]
                commentary = '\n\n'.join(sections[1:])

                print(f"\n🔍 АНАЛИЗ ФОРМАТИРОВАНИЯ:")
                print(f"  📰 Заголовки: {len(headlines_section)} символов")
                print(f"  💭 Комментарий: {len(commentary)} символов")

                # Проверяем наличие эмодзи или HTML тегов в комментарии
                has_emoji = any(ord(char) > 127 for char in commentary if ord(char) in range(128512, 129319))
                has_html = any(tag in commentary for tag in ['<b>', '</b>', '<i>', '</i>', '<a>', '</a>'])

                print(f"  {'❌' if has_emoji else '✅'} Эмодзи в комментарии: {'Есть' if has_emoji else 'Нет'}")
                print(f"  {'❌' if has_html else '✅'} HTML теги в комментарии: {'Есть' if has_html else 'Нет'}")

                # Показываем начало и конец комментария
                print(f"\n📖 КОММЕНТАРИЙ:")
                print(f"  Начало: '{commentary[:50]}...'")
                print(f"  Конец: '...{commentary[-50:]}'")

                if not has_emoji and not has_html:
                    print(f"\n🎉 УСПЕХ: LLM часть чистая, без форматирования!")
                else:
                    print(f"\n⚠️ ВНИМАНИЕ: Найдено форматирование в LLM части")

            else:
                print("❌ Неожиданная структура поста")

        else:
            print("❌ Ошибка генерации поста")

    except Exception as e:
        print(f"❌ Ошибка: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_clean_format())