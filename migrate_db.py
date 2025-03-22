"""
Скрипт для миграции базы данных.
Добавляет новые столбцы, необходимые для работы обновленной версии бота.
"""

import sqlite3
import logging
import os

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('database_migration')

def migrate_database():
    """Выполняет миграцию базы данных, добавляя недостающие столбцы."""
    
    # Путь к базе данных
    db_path = 'data/scheduled_posts.db'
    
    # Проверяем, существует ли база данных
    if not os.path.exists(db_path):
        logger.warning(f"База данных не найдена по пути {db_path}. Пропускаем миграцию.")
        return
    
    # Подключаемся к базе данных
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Проверяем наличие столбца is_auto_generated в таблице scheduled_posts
        cursor.execute("PRAGMA table_info(scheduled_posts)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        # Добавляем столбец is_auto_generated, если его нет
        if 'is_auto_generated' not in column_names:
            logger.info("Добавление столбца is_auto_generated в таблицу scheduled_posts...")
            cursor.execute(
                'ALTER TABLE scheduled_posts ADD COLUMN is_auto_generated BOOLEAN DEFAULT 0'
            )
            conn.commit()
            logger.info("Столбец is_auto_generated успешно добавлен.")
        else:
            logger.info("Столбец is_auto_generated уже существует.")
        
        # Создаем таблицу для кэширования постов, если её нет
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS generated_posts_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            generated_time DATETIME NOT NULL,
            post_text TEXT NOT NULL,
            is_used BOOLEAN DEFAULT 0
        )
        ''')
        conn.commit()
        logger.info("Таблица generated_posts_cache создана или уже существует.")
        
        logger.info("Миграция базы данных успешно завершена!")
    
    except Exception as e:
        logger.error(f"Ошибка при миграции базы данных: {str(e)}")
    
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database() 