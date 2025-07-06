import asyncio
from aiogram import Bot, Dispatcher
from bot.handlers import router
from config import BOT_TOKEN

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    print("🤖 Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
