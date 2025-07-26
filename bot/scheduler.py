# bot/scheduler.py file
from datetime import datetime

import aiosqlite
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import ADMIN_ID, FEEDBACK_NOTIFY_INTERVAL
from core.content_ai import generate_reply
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
	scheduler.start()
	scheduler.add_job(notify_new_feedbacks, 'interval', seconds = FEEDBACK_NOTIFY_INTERVAL, kwargs={'bot': bot})
	print("✅ Планировщик успешно запущен")
#-------------------------------------------------------------------------------------------------------#

async def notify_new_feedbacks(bot: Bot):
	"""Уведомление админа о новых фидбеках"""
	async with aiosqlite.connect(SQLITE_DB_PATH) as db:
		cursor = await db.execute("SELECT COUNT(*) FROM feedback WHERE status = 'new'")
		count = (await cursor.fetchone())[0]

	if count>0:
		await bot.send_message(ADMIN_ID, f"📭 У вас {count} непрочитанных отзывов. Проверить: /feedbacks")

