#!/usr/bin/env python3
"""
Тестовый скрипт для проверки разнообразия источников и новостей
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

async def test_news_diversity():
    """Тестирует разнообразие источников и новостей"""
    try:
        client = DeepSeekClient()

        print("🧪 ТЕСТИРОВАНИЕ РАЗНООБРАЗИЯ НОВОСТЕЙ")
        print("=" * 60)

        # Тест 1: Проверка источников новостей
        print("\n📡 ТЕСТ 1: Источники новостей")
        print("-" * 30)

        # Получаем новости напрямую от коллектора
        news_items = await client.news_collector.collect_news()

        if news_items:
            print(f"✅ Собрано {len(news_items)} новостей")

            # Анализ по источникам
            source_stats = {}
            for item in news_items:
                source_stats[item.source] = source_stats.get(item.source, 0) + 1

            print("\n📊 Статистика по источникам:")
            for source, count in sorted(source_stats.items()):
                print(f"  {source}: {count} новостей")
        else:
            print("❌ Не удалось собрать новости")
            return

        # Тест 2: Проверка балансировки (3 прогона)
        print(f"\n🎲 ТЕСТ 2: Балансировка источников (3 прогона)")
        print("-" * 30)

        all_selected_sources = []

        for run in range(1, 4):
            print(f"\n🔄 Прогон {run}:")

            # Генерируем пост с принудительным обновлением
            post, prompt, headlines = await client.generate_hybrid_post(force_refresh=True)

            if post and headlines:
                # Извлекаем источники из логов (приблизительно)
                selected_items = await client._get_news_items(force_refresh=True)

                sources_this_run = [item.source for item in selected_items[:5]]
                all_selected_sources.extend(sources_this_run)

                print(f"  Выбрано источников: {len(set(sources_this_run))}")
                print(f"  Источники: {list(set(sources_this_run))}")

                # Проверяем заголовки
                print(f"  Заголовки:")
                for i, headline in enumerate(headlines[:3], 1):
                    print(f"    {i}. {headline[:60]}...")
            else:
                print(f"  ❌ Ошибка генерации в прогоне {run}")

        # Тест 3: Анализ общего разнообразия
        print(f"\n📈 ТЕСТ 3: Анализ разнообразия")
        print("-" * 30)

        unique_sources_selected = len(set(all_selected_sources))
        total_selections = len(all_selected_sources)

        print(f"✅ Уникальных источников использовано: {unique_sources_selected}")
        print(f"✅ Общих выборов: {total_selections}")
        print(f"✅ Коэффициент разнообразия: {unique_sources_selected/total_selections:.2f}")

        if unique_sources_selected >= 6:
            print("🎉 ОТЛИЧНО: Высокое разнообразие источников!")
        elif unique_sources_selected >= 4:
            print("✅ ХОРОШО: Среднее разнообразие источников")
        else:
            print("⚠️ ВНИМАНИЕ: Низкое разнообразие источников")

        print(f"\n📋 РЕЗУЛЬТАТ: Система использует {unique_sources_selected} разных источников")

    except Exception as e:
        print(f"❌ Ошибка тестирования: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_news_diversity())