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
            is_sent BOOLEAN DEFAULT 0
        )
        ''')
        self.conn.commit()
    
    def add_scheduled_post(self, scheduled_time: datetime, post_text: str):
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO scheduled_posts (scheduled_time, post_text) VALUES (?, ?)',
            (scheduled_time.strftime("%Y-%m-%d %H:%M:%S"), post_text)
        )
        self.conn.commit()
    
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