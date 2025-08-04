#core/context_manager.py file
#import logging
from datetime import datetime
from typing import Dict

import aiosqlite
import tiktoken

from openai import AsyncOpenAI

from config import SQLITE_DB_PATH, GPT_TOKEN

#logger = logging.getLogger(__name__)

#-------------------------------------------------------------------------------------------------------#
client = AsyncOpenAI(api_key=GPT_TOKEN)
COMPRESSION_MODEL = "gpt-3.5-turbo"

async def smart_compress(texts: list[str]) -> str:
	"""Сжимает список сообщений, выделяя ключевые моменты с помощью GPT"""
	try:
		# Подготавливаем промпт для сжатия
		messages = [{
			"role": "system",
			"content": "Ты - помощник для сжатия текста. Анализируй историю диалога и выделяй только самое важное: "
                           "ключевые факты, решения, важные детали. Игнорируй приветствия, повторения и несущественные детали. "
                           "Суммируй кратко, сохраняя смысл. Возвращай только сжатый вариант, без пояснений."
		},
			{"role":"user",
			 "content": "Сожми этот диалог, сохраняя только самое важное и факты:\n" + "\n".join(texts)},
		]
		response = await client.chat.completions.create(
			model = COMPRESSION_MODEL,
			messages = messages,
			temperature=0.3,# Минимальная креативность для точности
			max_tokens=500 # Лимит на сжатый вариант
		)
		return response.choices[0].message.content.strip()

	except Exception as e:
		print(f"Ошибка при сжатии контекста: {e}")
		# Возвращаем простое сжатие в случае ошибки
		return "\n".join([msg[:150] for msg in texts[:3]])


#-------------------------------------------------------------------------------------------------------#
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
	async def get_recent_history(user_id: int, limit: int = 15) -> list[Dict]:
		"""Получает историю, автоматически инициируя сжатие при необходимости"""
		try:
			# Проверяем размер истории перед возвратом
			async with aiosqlite.connect(SQLITE_DB_PATH) as db:
				cursor = await db.execute("SELECT message_text FROM conversation_history WHERE user_id = ?", (user_id, ))
				messages = [row[0] for row in await cursor.fetchall()]

				# Проверяем необходимость сжатия
				encoding = tiktoken.encoding_for_model(COMPRESSION_MODEL)
				total_tokens = sum(len(encoding.encode(msg)) for msg in messages)

				if total_tokens > 1500:
					await ContextManager.compress_context(user_id, force = True)

				# Возвращаем актуальную историю
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
			print(f"Ошибка при получении истории: {e}")
			#logger.error(f"Error getting history: {e}")
			return []

	@staticmethod
	async def compress_context(user_id: int, force: bool = False):
		"""Сжимает контекст с помощью NLP, когда достигается лимит токенов"""
		try:
			async with aiosqlite.connect(SQLITE_DB_PATH) as db:
				# 1. Проверяем текущий размер истории
				cursor = await db.execute(
					"SELECT COUNT(*) FROM conversation_history WHERE user_id = ?", (user_id,))
				count = (await cursor.fetchone())[0]

				# 2. Получаем все сообщения для анализа
				cursor = await db.execute(
					"""SELECT message_text FROM conversation_history
					WHERE user_id = ? ORDER BY timestamp DESC""",
					(user_id,)
				)
				messages = [row[0] for row in await cursor.fetchall()]
				# 3. Проверяем условия для сжатия:
				# - Принудительное сжатие (force=True)
				# - Более 20 сообщений в истории
				# - Или если суммарный размер > 1500 токенов
				encoding = tiktoken.encoding_for_model(COMPRESSION_MODEL)
				total_tokens = sum(len(encoding.encode(msg)) for msg in messages)

				if not force and count < 20 and total_tokens <1500:
					print("Условие не выполнено, сжатие будет позже")
					return

				# 4. Применяем умное сжатие
				compressed = await smart_compress(messages)

				# 5. Сохраняем сжатый контекст и очищаем историю
				await db.execute("""
				INSERT OR REPLACE INTO context_cache(user_id, compressed_context, last_updated)
				VALUES(?, ?, datetime('now'))""",
				                 (user_id, compressed))

				# Оставляем только 5 последних сообщений
				await db.execute("""
                DELETE FROM conversation_history
				WHERE user_id = ? AND id NOT IN(
				SELECT id FROM (
				SELECT id FROM conversation_history
				WHERE user_id = ?
				ORDER BY timestamp DESC
				LIMIT 5)
				)""", (user_id, user_id)
				)
				await db.commit()
				print("Сжатие прошло успешно")
		# logger.debug(f"Compressed context for user {user_id}")
		except Exception as e:
			print(f"Ошибка при сжатии контекста: {e}")
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
		"""Полная очистка контекста пользователя с обработкой ошибок и транзакцией"""
		try:
			async with aiosqlite.connect(SQLITE_DB_PATH) as db:
				await db.execute(
					"DELETE FROM conversation_history WHERE user_id = ?",
				     (user_id, )
				)
				print(f"История пользователя {user_id} успешно очищен")
				await db.execute(
					"DELETE FROM context_cache WHERE user_id = ?",
					(user_id,)
				)
				await db.commit()
				print(f"Кэш контекста пользователя {user_id} успешно очищен")

				# logger.info(f"Cleared context for user {user_id}")
		except Exception as e:
			#logger.error(f"Error clearing context: {e}")
			print(e)
#-------------------------------------------------------------------------------------------------------#



