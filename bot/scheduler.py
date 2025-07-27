# bot/scheduler.py file
from datetime import datetime

import aiosqlite
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import ADMIN_ID, FEEDBACK_NOTIFY_INTERVAL
from core.content_ai import generate_reply
from core.context_manager import ContextManager
from core.xp_engine import load_users, XPManager
from db.database import SQLITE_DB_PATH

scheduler = AsyncIOScheduler()

# Утренняя аффирмация
async def morning_affirmation(bot: Bot):
	print(f"⏰ Утренняя рассылка запущена в {datetime.now()}")
	users = load_users()
	for user_id in users:
		user_id_int = int(user_id)

		xp = XPManager(user_id_int)
		xp.add_xp(10)

		prompt = "Дай короткую бодрую аффирмацию мужчине на утро, максимум 15 слов"
		text = await generate_reply(user_id, prompt)

		try:
			await bot.send_message(user_id_int, f'🌅 Утренняя аффирмация:\n{text}\n+10 XP 🌟')

		except Exception as e:
			print(f'[Ошибка отправки]', e)

# Вечерняя рефлексия
async def evening_reflection(bot: Bot):
	print(f"🌙 Вечерняя рассылка запущена в {datetime.now()}")
	users = load_users()
	for user_id in users:
		try:
			await bot.send_message(int(user_id), "🌙 Как прошёл день? Что удалось, что нет?")
		except Exception as e:
			print(f'[Ошибка отправки]: {e}')

def setup_scheduler(bot: Bot):
	# Тестовый триггер - каждые 5 минут (для отладки)
	scheduler.add_job(morning_affirmation, CronTrigger(hour=7, minute=0), kwargs={'bot': bot}, id='morning_affirmation')
	scheduler.add_job(evening_reflection, CronTrigger(hour=21, minute=0), kwargs={'bot': bot},  id='evening_reflection')
	scheduler.add_job(notify_new_feedbacks, 'interval', seconds = FEEDBACK_NOTIFY_INTERVAL, kwargs={'bot': bot})

	scheduler.add_job(check_inactive_users,'cron', day_of_week = 'mon', kwargs={'bot':bot})
	scheduler.add_job(compress_inactive_contexts, 'cron', day_of_week = 'mon')
	scheduler.start()
	print("✅ Планировщик успешно запущен")
#-------------------------------------------------------------------------------------------------------#

async def notify_new_feedbacks(bot: Bot):
	"""Уведомление админа о новых фидбеках"""
	async with aiosqlite.connect(SQLITE_DB_PATH) as db:
		cursor = await db.execute("SELECT COUNT(*) FROM feedback WHERE status = 'new'")
		count = (await cursor.fetchone())[0]

	if count>0:
		await bot.send_message(ADMIN_ID, f"📭 У вас {count} непрочитанных отзывов. Проверить: /feedbacks")
#-------------------------------------------------------------------------------------------------------#

async def check_inactive_users(bot: Bot):
	"""Проверяет неактивных пользователей"""
	async with aiosqlite.connect(SQLITE_DB_PATH) as db:
		#Пользователи, не проявлявшие активность 30+ дней
		cursor = await db.execute(
			"""SELECT user_id FROM conversation_history
			WHERE timestamp < datetime('now', '-30 days')
			GROUP BY user_id"""
		)
		inactive_users = await cursor.fetchall()

		for user_id, in inactive_users:
			try:
				await bot.send_message(user_id,  "🔔 Давно не виделись! Если вы не зайдете в течение недели, "
                    "ваша история диалогов будет сжата для экономии ресурсов.")
			except Exception as e:
				pass # Пользователь заблокировал бота
#-------------------------------------------------------------------------------------------------------#

async def compress_inactive_contexts():
	"""Сжимает контексты неактивных пользователей"""
	async with aiosqlite.connect(SQLITE_DB_PATH) as db:
		# Пользователи без активности 37+ дней (30 + 7 дней предупреждения)
		cursor = await db.execute(
			"""SELECT user_id FROM conversation_history
			WHERE timestamp < datetime('now', '-37 days')
			GROUP BY user_id"""
		)
		users = await cursor.fetchall()

		for user_id, in users:
			await ContextManager.compress_context(user_id)


