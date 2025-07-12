#token_manager.pi file
import os
import sqlite3
from datetime import datetime

# система лимитов токенов через БАЗУ ДАННЫХ

class TokenManager:
    def __init__(self):
        db_path = os.path.join('db', 'tokens.db')
        self.conn = sqlite3.connect(db_path)
        self._create_table()

    def _create_table(self):
        self.conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            tokens_used INTEGER DEFAULT 0,
            last_reset DATE
        )''')
        self.conn.commit()

    def get_tokens(self, user_id: int) -> int:
        """Проверяем, сколько токенов использовано сегодня"""
        today = datetime.now().date()
        cursor = self.conn.cursor()
        cursor.execute('''
        SELECT tokens_used FROM users 
        WHERE user_id = ? AND last_reset = ?
        ''', (user_id, today))
        result = cursor.fetchone()
        return result[0] if result else 0

    def add_tokens(self, user_id: int, tokens: int):
        """Обновляем счётчик"""
        today = datetime.now().date()
        self.conn.execute('''
        INSERT OR REPLACE INTO users (user_id, tokens_used, last_reset)
        VALUES (?, COALESCE(
            (SELECT tokens_used FROM users 
             WHERE user_id = ? AND last_reset = ?), 0) + ?, ?
        )''', (user_id, user_id, today, tokens, today))
        self.conn.commit()

# Глобальный экземпляр
token_db = TokenManager()
