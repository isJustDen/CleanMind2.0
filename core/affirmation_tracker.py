#core/affirmation_tracker.py file

import os
import sqlite3
from datetime import date

DB_PATH_AFFIRMATION = os.path.join('db', 'affirmations.db')

class AffirmationTracker:
	# подключение к существующей ДБ
	def __init__(self):
		os.makedirs('db', exist_ok=True)
		self.conn = sqlite3.connect(DB_PATH_AFFIRMATION)
		self._create_table()

	#Создание таблицы для отслеживания пользователей
	def _create_table(self):
		self.conn.execute("""
			CREATE TABLE IF NOT EXISTS affirmations (
			user_id INTEGER,
			day TEXT,
			period TEXT,
			PRIMARY KEY (user_id, day, period))
			""")
		self.conn.commit()

	# возврат ответа по поводу начисляли сегодня или еще нет баллы
	def is_alredy_done(self, user_id: int, period: str) -> bool:
		today = date.today().isoformat()
		cur = self.conn.cursor()
		cur.execute("""
			SELECT 1 FROM affirmations
			WHERE user_id =? AND period = ? AND day = ?""", (user_id, period, today))
		return cur.fetchone() is not None

	#Фиксация выданных баллов по периоду и id пользователя
	def mark_done(self, user_id: int, period: str):
		today = date.today().isoformat()
		self.conn.execute("""
		INSERT OR IGNORE INTO affirmations (user_id, day, period)
		VALUES (?, ?, ?)""", (user_id, today, period))
		self.conn.commit()

# Глобальный экземпляр
affirmation_db = AffirmationTracker()