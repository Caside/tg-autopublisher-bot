#!/usr/bin/env python3
"""
Тест разнообразных промптов с полными заголовками новостей
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

async def test_diverse_prompts():
    """Тестирует новые разнообразные промпты с полными заголовками"""
    try:
        client = DeepSeekClient()

        print("🎭 ТЕСТ РАЗНООБРАЗНЫХ ПРОМПТОВ")
        print("=" * 45)

        print("\n📰 ПРОВЕРЯЕМ:")
        print("✅ Полные заголовки передаются в LLM")
        print("✅ Разнообразные философские вопросы")
        print("✅ Заголовки НЕ повторяются в комментарии")

        # Делаем несколько тестов для демонстрации разнообразия
        for test_num in range(1, 6):
            print(f"\n{'='*20} ТЕСТ {test_num} {'='*20}")

            post, prompt, headlines = await client.generate_hybrid_post(force_refresh=True)

            if post and prompt and headlines:
                # Показываем промпт (обрезанно)
                prompt_lines = prompt.split('\n')
                print(f"\n📋 ПРОМПТ:")
                print(f"  Начало: {prompt_lines[0]}")
                if len(prompt_lines) > 6:
                    print("  Заголовки:")
                    for i in range(1, 6):
                        print(f"    {prompt_lines[i]}")
                    print(f"  Вопрос: {prompt_lines[-1]}")

                # Анализируем пост
                sections = post.split('\n\n')
                if len(sections) >= 2:
                    headlines_section = sections[0]
                    commentary = '\n\n'.join(sections[1:]).replace('🤔 ', '')

                    print(f"\n💭 LLM КОММЕНТАРИЙ ({len(commentary)} символов):")
                    print(f"  {commentary}")

                    # Проверяем, не повторяет ли LLM заголовки
                    headlines_repeated = False
                    for headline in headlines:
                        # Проверяем наличие ключевых слов из заголовков в комментарии
                        headline_words = headline.lower().split()
                        for word in headline_words:
                            if len(word) > 5 and word in commentary.lower():
                                headlines_repeated = True
                                break

                    print(f"\n🔍 АНАЛИЗ:")
                    print(f"  ✅ Заголовки в промпте: {len(headlines)}")
                    print(f"  ✅ Длина комментария: {len(commentary)} символов")
                    print(f"  {'❌' if headlines_repeated else '✅'} Повторы заголовков: {'Да' if headlines_repeated else 'Нет'}")
                    print(f"  ✅ Завершен корректно: {'Да' if commentary.strip().endswith(('.', '!', '?')) else 'НЕТ'}")

            else:
                print(f"  ❌ Ошибка в тесте {test_num}")

            # Небольшая пауза между тестами
            if test_num < 5:
                print(f"\n⏳ Пауза перед следующим тестом...")
                await asyncio.sleep(2)

        print(f"\n🎉 ТЕСТИРОВАНИЕ ЗАВЕРШЕНО!")
        print("Проверьте разнообразие вопросов в промптах выше ☝️")

    except Exception as e:
        print(f"❌ Ошибка: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_diverse_prompts())