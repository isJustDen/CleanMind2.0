#core/context_manager.py file
#import logging
from datetime import datetime
from typing import Dict

import aiosqlite

from config import SQLITE_DB_PATH

#logger = logging.getLogger(__name__)

class ContextManager:
	@staticmethod
	async def save_message(user_id: int, text: str, role: str):
		"""Сохраняет сообщение в историю"""
		try:
			async with aiosqlite.connect(SQLITE_DB_PATH) as db:
				await db.execute(
					'INSERT INTO conversation_history(user_id, message_text, role) VALUES(?, ?, ?)',
					(user_id, text, role)
				)
				await db.commit()
				# cursor = await db.execute("SELECT datetime('now')")
				# current_time = await cursor.fetchone()
				# logger.debug(f"Current DB time: {current_time[0]}")
				#
				# logger.debug(f'Saved message for user {user_id}')
				# logger.debug(f"Saved message at {datetime.now()}")
		except Exception as e:
			#logger.error(f"Error saving message: {e}")
			raise

	@staticmethod
	async def get_recent_history(user_id: int, hours: int = 24, limit: int = 10) -> list[Dict]:
		"""Получает свежую историю (последние 24 часа по умолчанию)"""
		try:
			async with aiosqlite.connect(SQLITE_DB_PATH) as db:
				cursor = await db.execute(
					"""
					SELECT message_text, role FROM conversation_history
					WHERE user_id = ?
					ORDER BY timestamp DESC
					LIMIT ?""",
					(user_id, limit)
				)
				rows = await cursor.fetchall()
				return [{'role': row[1], 'content': row[0]} for row in reversed(rows)]
		except Exception as e:
			#logger.error(f"Error getting history: {e}")
			return []

	@staticmethod
	async def compress_context(user_id: int):
		"""Сжимает старый контекст"""
		try:
			async with aiosqlite.connect(SQLITE_DB_PATH) as db:
				# 1. Получаем старые сообщения (1-7 дней)
				cursor = await db.execute(
					"""SELECT message_text FROM conversation_history
					WHERE user_id = ? AND timestamp BETWEEN datetime('now', '-7 days') 
					AND datetime('now', '-1 day')""",
					(user_id,)
				)
				old_message = [row[0] for row in await cursor.fetchall()]

				if not old_message:
					return

				# 2. Здесь должна быть логика сжатия (упрощенная версия)
				compressed = "\n".join([msg[:100] for msg in old_message[:5]])  # Берем первые 5 сообщений по 100 символов

				# 3. Сохраняем сжатый контекст
				await db.execute("""
				INSERT OR REPLACE INTO context_cache(user_id, compressed_context, last_updated)
				VALUES(?, ?, datetime('now'))""",
				                 (user_id, compressed))
				await db.commit()
				# logger.debug(f"Compressed context for user {user_id}")
		except Exception as e:
			print(e)
			#logger.error(f"Error compressing context: {e}")

	@staticmethod
	async def get_compressed_context(user_id: int) -> str:
		"""Получает сжатый контекст"""
		try:
			async with aiosqlite.connect(SQLITE_DB_PATH) as db:
				cursor = await db.execute(
					"SELECT compressed_context FROM context_cache WHERE user_id = ?",
					(user_id, )
				)
				row = await cursor.fetchone()
				return row[0] if row else ""
		except Exception as e:
			#logger.error(f"Error getting compressed context: {e}")
			print(e)
			return ""

	@staticmethod
	async def clear_context(user_id: int):
		"""Полная очистка контекста"""
		try:
			async with aiosqlite.connect(SQLITE_DB_PATH) as db:
				await db.execute(
					"DELETE FROM conversation_history WHERE user_id = ?",
				     (user_id, )
				)
				await db.commit()
				# logger.info(f"Cleared context for user {user_id}")
		except Exception as e:
			#logger.error(f"Error clearing context: {e}")
			print(e)

