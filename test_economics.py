#!/usr/bin/env python3
"""
Тест новой конфигурации: российские источники + экономика
"""

import asyncio
import logging
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from deepseek_client import DeepSeekClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

async def test_russian_sources():
    """Тестирует новые российские источники с экономикой"""
    try:
        client = DeepSeekClient()

        print("🇷🇺 ТЕСТ РОССИЙСКИХ ИСТОЧНИКОВ С ЭКОНОМИКОЙ")
        print("=" * 55)

        # Тест источников
        print("\n📊 АНАЛИЗ ИСТОЧНИКОВ:")
        print("-" * 30)

        news_items = await client.news_collector.collect_news()

        if news_items:
            source_stats = {}
            economic_news = 0
            tech_news = 0
            science_news = 0

            for item in news_items:
                source_stats[item.source] = source_stats.get(item.source, 0) + 1

                # Классификация по тематике
                title_lower = item.title.lower()
                if any(word in title_lower for word in ['бизнес', 'экономик', 'рубль', 'банк', 'финанс', 'рынок', 'инвестици']):
                    economic_news += 1
                elif any(word in title_lower for word in ['технолог', 'программ', 'разработ', 'ии', 'искусственный']):
                    tech_news += 1
                elif any(word in title_lower for word in ['наук', 'исследован', 'ученые', 'открыти']):
                    science_news += 1

            print(f"✅ Всего новостей: {len(news_items)}")
            print(f"✅ Рабочих источников: {len(source_stats)}")
            print()

            print("📈 Тематическое распределение:")
            print(f"  💼 Экономика/бизнес: {economic_news}")
            print(f"  💻 Технологии/IT: {tech_news}")
            print(f"  🔬 Наука/исследования: {science_news}")
            print()

            print("📡 По источникам:")
            for source, count in sorted(source_stats.items()):
                source_type = "💼" if any(x in source for x in ['vedomosti', 'rbc', 'kommersant', 'interfax']) else "💻" if 'vc_tech' in source or 'cnews' in source else "🔬"
                print(f"  {source_type} {source}: {count} новостей")

        # Тест генерации постов
        print(f"\n🤖 ТЕСТ ГЕНЕРАЦИИ ПОСТОВ:")
        print("-" * 30)

        for test_num in range(1, 3):
            print(f"\n🔄 Тест {test_num}:")

            post, prompt, headlines = await client.generate_hybrid_post(force_refresh=True)

            if post and headlines:
                # Анализ тематики заголовков
                economic_headlines = 0
                tech_headlines = 0
                science_headlines = 0

                for headline in headlines:
                    headline_lower = headline.lower()
                    if any(word in headline_lower for word in ['бизнес', 'экономик', 'рубль', 'банк', 'финанс', 'рынок']):
                        economic_headlines += 1
                    elif any(word in headline_lower for word in ['технолог', 'программ', 'разработ', 'ии']):
                        tech_headlines += 1
                    elif any(word in headline_lower for word in ['наук', 'исследован', 'ученые']):
                        science_headlines += 1

                print(f"  📊 Тематика заголовков:")
                print(f"    💼 Экономика: {economic_headlines}")
                print(f"    💻 Технологии: {tech_headlines}")
                print(f"    🔬 Наука: {science_headlines}")

                # Показать примеры заголовков
                print(f"  📰 Примеры заголовков:")
                for i, headline in enumerate(headlines[:3], 1):
                    print(f"    {i}. {headline[:70]}...")

                # Проверка полноты LLM
                sections = post.split('\n\n')
                if len(sections) >= 2:
                    commentary = '\n\n'.join(sections[1:])
                    print(f"  💭 LLM часть: {len(commentary)} символов")
                    print(f"  ✅ Завершено корректно: {'Да' if commentary.strip().endswith(('.', '!', '?')) else 'НЕТ'}")

        print(f"\n🎉 ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
        print(f"Система готова с российскими источниками и экономическими новостями!")

    except Exception as e:
        print(f"❌ Ошибка: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_russian_sources())