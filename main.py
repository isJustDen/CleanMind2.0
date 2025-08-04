#main.py file

import asyncio
# import logging
import os

import aiosqlite
from aiogram import Bot, Dispatcher
from bot.handlers import user_router
from bot.scheduler import setup_scheduler
from config import BOT_TOKEN, SQLITE_DB_PATH
from db.database import init_db
from bot.admin import admin_router



# logging.basicConfig(
#     level=logging.DEBUG,
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
# )
async def main():
    bot = None
    try:
        #  проверяем целостность БД
        await check_db_integrity()
        #  инициализируем БД
        await init_db()

        #  создаем бота
        bot = Bot(token=BOT_TOKEN)
        dp = Dispatcher()

        # Подключаем роутеры
        dp.include_router(admin_router)
        dp.include_router(user_router)

        # Инициализация планировщика
        setup_scheduler(bot) # Передаем бота в планировщик

        print('База данных инициализирована. Планировщик запущен.')
        print("🤖 Бот запущен...")
        await dp.start_polling(bot)

    except Exception as e:
        print(f"❌ Ошибка при запуске: {e}")
    finally:
        if bot:
            await bot.session.close()


async def check_db_integrity():
    """Проверка целостности БД"""
    try:
        async with aiosqlite.connect(SQLITE_DB_PATH) as db:
            await db.execute('PRAGMA integrity_check')
    except Exception as e:
        print(f"⚠️ Ошибка проверки целостности БД: {e}")
        if os.path.exists(SQLITE_DB_PATH):
            os.remove(SQLITE_DB_PATH)
        await init_db()
#-------------------------------------------------------------------------------------------------------#
if __name__ == "__main__":
    asyncio.run(main())
