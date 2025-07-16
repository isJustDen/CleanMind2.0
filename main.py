#main.py file

import asyncio
from aiogram import Bot, Dispatcher
from bot.handlers import router
from bot.scheduler import setup_scheduler
from config import BOT_TOKEN
from db.database import init_db


async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    # Инициализация БД и планировщика
    await init_db()
    setup_scheduler(bot) # Передаем бота в планировщик

    print('База данных инициализирована. Планировщик запущен.')
    print("🤖 Бот запущен...")
    await dp.start_polling(bot)

#-------------------------------------------------------------------------------------------------------#
if __name__ == "__main__":
    asyncio.run(main())
