import sqlite3
from datetime import datetime

class Database:
    def __init__(self):
        self.conn = sqlite3.connect('data/scheduled_posts.db')
        self.create_tables()
    
    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS scheduled_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scheduled_time DATETIME NOT NULL,
            post_text TEXT NOT NULL,
            is_sent BOOLEAN DEFAULT 0,
            is_auto_generated BOOLEAN DEFAULT 0
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS generated_posts_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            generated_time DATETIME NOT NULL,
            post_text TEXT NOT NULL,
            is_used BOOLEAN DEFAULT 0
        )
        ''')
        
        self.conn.commit()
    
    def add_scheduled_post(self, scheduled_time: datetime, post_text: str, is_auto_generated: bool = False):
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO scheduled_posts (scheduled_time, post_text, is_auto_generated) VALUES (?, ?, ?)',
            (scheduled_time.strftime("%Y-%m-%d %H:%M:%S"), post_text, is_auto_generated)
        )
        self.conn.commit()
        return cursor.lastrowid
    
    def get_pending_posts(self):
        cursor = self.conn.cursor()
        cursor.execute(
            'SELECT id, scheduled_time, post_text FROM scheduled_posts WHERE is_sent = 0'
        )
        return cursor.fetchall()
    
    def mark_post_as_sent(self, post_id: int):
        cursor = self.conn.cursor()
        cursor.execute(
            'UPDATE scheduled_posts SET is_sent = 1 WHERE id = ?',
            (post_id,)
        )
        self.conn.commit()
    
    def add_generated_post_to_cache(self, post_text: str):
        """Добавляет сгенерированный пост в кэш для будущего использования."""
        cursor = self.conn.cursor()
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            'INSERT INTO generated_posts_cache (generated_time, post_text) VALUES (?, ?)',
            (current_time, post_text)
        )
        self.conn.commit()
        return cursor.lastrowid
    
    def get_unused_cached_post(self):
        """Получает неиспользованный пост из кэша."""
        cursor = self.conn.cursor()
        cursor.execute(
            'SELECT id, post_text FROM generated_posts_cache WHERE is_used = 0 ORDER BY id ASC LIMIT 1'
        )
        result = cursor.fetchone()
        
        if result:
            post_id, post_text = result
            # Отмечаем пост как использованный
            cursor.execute(
                'UPDATE generated_posts_cache SET is_used = 1 WHERE id = ?',
                (post_id,)
            )
            self.conn.commit()
            return post_text
        return None
    
    def count_cached_posts(self):
        """Подсчитывает количество неиспользованных постов в кэше."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM generated_posts_cache WHERE is_used = 0')
        return cursor.fetchone()[0]
    
    def clean_old_sent_posts(self, days=30):
        """Удаляет старые отправленные посты из базы данных."""
        cursor = self.conn.cursor()
        cursor.execute(
            'DELETE FROM scheduled_posts WHERE is_sent = 1 AND datetime(scheduled_time) < datetime("now", ?)',
            (f"-{days} days",)
        )
        self.conn.commit()
        return cursor.rowcount 