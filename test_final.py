#!/usr/bin/env python3
"""
Финальный тест исправлений: проверка полных LLM ответов и разнообразия источников
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

async def test_fixes():
    """Тестирует исправления токенов и разнообразия"""
    try:
        client = DeepSeekClient()

        print("🔧 ТЕСТИРОВАНИЕ ИСПРАВЛЕНИЙ")
        print("=" * 50)

        # Тест 1: Проверка источников
        print("\n📡 ТЕСТ 1: Новые источники")
        print("-" * 30)

        news_items = await client.news_collector.collect_news()

        if news_items:
            source_stats = {}
            for item in news_items:
                source_stats[item.source] = source_stats.get(item.source, 0) + 1

            print(f"✅ Всего новостей: {len(news_items)}")
            print(f"✅ Рабочих источников: {len(source_stats)}")

            for source, count in sorted(source_stats.items()):
                print(f"  {source}: {count} новостей")

        # Тест 2: Проверка полноты LLM ответов
        print(f"\n🤖 ТЕСТ 2: Полные LLM ответы")
        print("-" * 30)

        for test_num in range(1, 3):
            print(f"\n🔄 Тест {test_num}:")

            post, prompt, headlines = await client.generate_hybrid_post(force_refresh=True)

            if post and headlines:
                # Анализ поста
                sections = post.split('\n\n')
                if len(sections) >= 2:
                    headlines_section = sections[0]
                    commentary_section = '\n\n'.join(sections[1:])

                    print(f"  📏 Общая длина поста: {len(post)} символов")
                    print(f"  📰 Заголовки: {len(headlines_section)} символов")
                    print(f"  💭 Комментарий: {len(commentary_section)} символов")

                    # Проверка на обрывы
                    if commentary_section.endswith(('.', '!', '?')):
                        print(f"  ✅ Комментарий завершен корректно")
                    else:
                        print(f"  ❌ Комментарий обрывается: '{commentary_section[-50:]}'")

                    # Показываем последние 100 символов для проверки
                    print(f"  🔚 Окончание: '...{commentary_section[-100:]}'")

                    # Проверяем разнообразие заголовков
                    ai_headlines = [h for h in headlines if 'ии' in h.lower() or 'искусственный' in h.lower()]
                    print(f"  🧠 ИИ заголовков: {len(ai_headlines)}/{len(headlines)}")

                    if len(ai_headlines) < len(headlines) * 0.6:
                        print(f"  ✅ Хорошее разнообразие тем")
                    else:
                        print(f"  ⚠️ Много ИИ заголовков")

            print()

        print("🎉 ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")

    except Exception as e:
        print(f"❌ Ошибка тестирования: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_fixes())