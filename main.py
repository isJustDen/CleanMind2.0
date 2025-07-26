#main.py file

import asyncio
import os
from venv import logger

import aiosqlite
from aiogram import Bot, Dispatcher
from bot.handlers import router
from bot.scheduler import setup_scheduler
from config import BOT_TOKEN, SQLITE_DB_PATH
from db.database import init_db


async def main():
    await check_db_integrity()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    # Инициализация БД и планировщика
    await init_db()
    setup_scheduler(bot) # Передаем бота в планировщик

    print('База данных инициализирована. Планировщик запущен.')
    print("🤖 Бот запущен...")
    await dp.start_polling(bot)


async def check_db_integrity():
    try:
        async with aiosqlite.connect(SQLITE_DB_PATH) as db:
            await db.execute('PRAGMA integrity_check')
    except Exception as e:
        logger.critical(f'Database corruption: {e}')
        os.remove(SQLITE_DB_PATH)
        await init_db()
#-------------------------------------------------------------------------------------------------------#
if __name__ == "__main__":
    asyncio.run(main())
