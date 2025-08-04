#bot//admin.py
import aiosqlite
from aiogram import types, Router
from aiogram.filters import Command

from config import SQLITE_DB_PATH, ADMIN_ID
from core.admin_manager import AdminManager

admin_router = Router()


@admin_router.message(Command('addadmin'))
async def add_admin(message: types.Message):
	"""Добавление новых администраторов в список"""
	if not await AdminManager.is_admin(message.from_user.id):
		return await message.answer('"❌ Доступ запрещен"')

	try:
		_, user_id, username = message.text.split()
		await AdminManager.add_admin(int(user_id), username)
		await message.answer(f"✅ Пользователь {username} добавлен как администратор")

	except:
		await message.answer('Использование: /addadmin <user_id> <username>')
#-------------------------------------------------------------------------------------------------------#

@admin_router.message(Command('broadcast'))
async def broadcast(message: types.Message):
	"""Рассылка сообщений для пользователей"""
	if not await AdminManager.is_admin(message.from_user.id):
		return await message.answer('❌ Доступ запрещен')

	text = message.text.replace('/broadcast', '').strip()
	if not text:
		return await message.answer('Введите сообщение после команды')

	await message.answer("⏳ Рассылка начата...")
	await AdminManager.broadcast_message(message.bot, text, message.from_user.id)
	await message.answer(f"✅ Сообщение отправлено пользователям")
#-------------------------------------------------------------------------------------------------------#

@admin_router.message(Command('admin'))
async def admin_help(message: types.Message):
    """Отображает команды для админа"""
    if not await AdminManager.is_admin(message.from_user.id):
	    return await message.answer("Только для админов 🛠")


    text = """<b>🛠 Административные команды:</b>
    
    <b>Доступные команды:</b>
<b>/addadmin</b> [id] [username] - Добавить администратора
<b>/broadcast</b> [текст] - Рассылка всем пользователям
<b>/feedbacks</b> - Просмотр новых отзывов
<b>/resolve_fb</b> [id] - Пометить отзыв как обработанный

<b>🔜 В разработке:</b>
<b>/stats</b> - Статистика по пользователям
<b>/ban</b> - Заблокировать пользователя
<b>/promo</b> - Создать промокод
<b>/export</b> - Выгрузка данных
"""
    await message.answer(text, parse_mode='HTML')
#-------------------------------------------------------------------------------------------------------#

@admin_router.message(Command('feedbacks'))
async def view_feedbacks(message: types.Message):
	"""Просмотр непрочитанных фидбеков (только для админа)"""
	if message.from_user.id != ADMIN_ID:
		return await message.answer('⛔ Доступ запрещён')

	async with aiosqlite.connect(SQLITE_DB_PATH) as db:
		cursor = await db.execute("SELECT id, user_id, message FROM feedback WHERE status = 'new' LIMIT 10")
		feedbacks = await cursor.fetchall()

	if not feedbacks:
		return await message.answer("📭 Нет новых отзывов")

	response = ['📬 Непрочитанные отзывы:\n"']
	for fb in feedbacks:
		response.append(f'ID: {fb[0]}\nUser: {fb[1]}\nMessage: {fb[2]}\n-----')

		# Разбиваем на несколько сообщений если слишком длинное
	for chunk in [response[i:i+3] for i in range(0, len(response), 3)]:
		await message.answer('\n'.join(chunk))

#Добавим обработку фидбеков
@admin_router.message(Command('resolve_fb'))
async def resolve_feedback(message: types.Message):
	"""Пометить фидбек как обработанный"""
	if message.from_user.id != ADMIN_ID:
		return

	try:
		fb_id = int(message.text.split()[1])
		async with aiosqlite.connect(SQLITE_DB_PATH) as db:
			await db.execute(
				"UPDATE feedback SET status = 'processed' WHERE id = ?",
				(fb_id,)
			)
			await db.commit()
		await message.answer(f"✅ Фидбек #{fb_id} помечен как обработанный")
	except (IndexError, ValueError):
		await message.answer('Использование: /resolve_fb <id_фидбека>')
#-------------------------------------------------------------------------------------------------------#

#@admin_router.message(Command("initadmin"))
async def init_admin(message: types.Message):
	"""Секретная команда, для добавления первого админа, после первого использования закомментировать"""
	if message.from_user.id != ADMIN_ID:
		return

	await AdminManager.add_admin(ADMIN_ID, message.from_user.username, True)
	await message.answer('✅ Первый админ добавлен!')
