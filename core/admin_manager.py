#  core/admin_manager.py

import aiosqlite
from config import SQLITE_DB_PATH

class AdminManager:
    @staticmethod
    async def add_admin(user_id: int, username: str, is_superadmin: bool = False):
        """Добавляем админов в существующую таблицу базы данных"""
        async with aiosqlite.connect(SQLITE_DB_PATH) as db:
            await db.execute(
                "INSERT or REPLACE INTO admins VALUES (?, ?, ?)",
                (user_id, username, is_superadmin)
            )
            await db.commit()

    @staticmethod
    async def is_admin(user_id: int) -> bool:
        """Условный выбор админский привелегий и переключение к ним"""
        async with aiosqlite.connect(SQLITE_DB_PATH) as db:
            cursor = await db.execute(
                "SELECT 1 FROM admins WHERE user_id = ?",
                (user_id,)
            )
            return bool(await cursor.fetchone())

    @staticmethod
    async def get_all_users() -> list[int]:
        async with aiosqlite.connect(SQLITE_DB_PATH) as db:
            cursor = await db.execute(
                "SELECT DISTINCT user_id FROM conversation_history"
            )
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

    @staticmethod
    async def broadcast_message(bot, text: str, from_admin: int):
        users = await AdminManager.get_all_users()
        success = 0
        for user_id in users:
            try:
                await bot.send_message(user_id, f"📢 Администратор сообщает:\n{text}")
                success += 1
            except Exception as e:
                print(f"Не удалось отправить сообщение {user_id}: {e}")

        # Отправляем отчет администратору
        admin_msg = f"""
        📊 Отчет о рассылке:
        Всего пользователей: {len(users)}
        Успешно: {success}
        Не удалось: {len(users) - success}
        """
        await bot.send_message(from_admin, admin_msg)