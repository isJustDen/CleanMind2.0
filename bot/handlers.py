#bot/handlers.py file
import sqlite3
import random
from zoneinfo import ZoneInfo


import aiosqlite
from aiogram import Router, types, F
from aiogram.filters import CommandStart, Command
import json
import os
from datetime import datetime

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ReplyKeyboardMarkup, \
	KeyboardButton, ReplyKeyboardRemove
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from config import ADMIN_ID, SQLITE_DB_PATH, DB_DIR, is_admin
from core.affirmation_tracker import affirmation_db
from core.content_ai import generate_reply, generate_affirmations
from core.xp_engine import XPManager

router = Router()
os.makedirs("db", exist_ok=True)
USERS_JSON_PATH = os.path.join(DB_DIR, 'users.json')
#-------------------------------------------------------------------------------------------------------#

#Функция Загрузка параметров пользователя из JSON файла
def load_users():
	if not os.path.exists(USERS_JSON_PATH) or os.path.getsize(USERS_JSON_PATH) == 0:
		return {}
	try:
		with open(USERS_JSON_PATH, 'r', encoding='utf-8') as f:
			return json.load(f)
	except json.JSONDecodeError:
		return {}
#-------------------------------------------------------------------------------------------------------#

# Функция сохранение параметров пользователя
def save_user(user_id, data):
	users = load_users()
	users[str(user_id)] = data
	with open(USERS_JSON_PATH, 'w', encoding='utf-8') as f:
		json.dump(users, f, ensure_ascii = False, indent = 4 )
#-------------------------------------------------------------------------------------------------------#

# Функция Определитель времени
def get_period() -> str:
	tz = ZoneInfo("Asia/Almaty")
	hour = datetime.now(tz).hour
	if hour < 12:
		return 'morning'
	elif hour < 18:
		return 'day'
	else:
		return 'evening'
#-------------------------------------------------------------------------------------------------------#


#-------------------------------------------------------------------------------------------------------#
#-------------------------------------------------------------------------------------------------------#
#-------------------------------------------------------------------------------------------------------#

# Команда /start. Сохранение пользователя в JSON и отображение о его статусе в регистрации
@router.message(CommandStart())
async def start_cmd(message: types.Message):
	user = message.from_user
	user_data = {
		'id': user.id,
		'name': user.full_name,
		'username': user.username,
		'registered': datetime.now().isoformat(),
		'experience': 0,
		'level': 1,
		'tone': 'soft' # Стиль общения ( мягкий по умолчанию): soft, strict, funny
	}
	if str(user.id) in load_users():
		await message.answer("Вы уже зарегистрированы!")
		return
	else:
		save_user(user.id, user_data)
		await message.answer(f'Привет, {user.first_name}! Добро пожаловаться в 🌿 Чистый Ум.\nТы зарегистрирован."')
#-------------------------------------------------------------------------------------------------------#

# Команда /gainxp — добавить XP вручную
@router.message(Command('gainxp'))
async def gain_xp_handler(message: types.Message):
	xp_manager = XPManager(user_id=message.from_user.id)
	xp_manager.add_xp(50)
	await message.answer(f"💪 Получено 50 XP!\n{xp_manager.status()}")
#-------------------------------------------------------------------------------------------------------#

# Команда /me — показать статус
@router.message(Command('me'))
async def show_profile(message: types.Message):
	xp_manager = XPManager(user_id=message.from_user.id)
	await message.answer(xp_manager.status())
#-------------------------------------------------------------------------------------------------------#

#Команда для выбора стиля общения
@router.message(Command('style'))
async def choose_style(message: types.Message):
	keyboard = InlineKeyboardMarkup(inline_keyboard=[
	[
		InlineKeyboardButton(text='🧘 МЯГКИЙ', callback_data='style_soft'),
		InlineKeyboardButton(text = '🪖 СТРОГИЙ', callback_data='style_strict'),
		InlineKeyboardButton(text = '😅 ЮМОРНОЙ', callback_data='style_funny'),
		InlineKeyboardButton(text = '😐 СТАНДАРТ', callback_data='style_standard')
	]
	])
	await message.answer('Выберите стиль общения:', reply_markup=keyboard)
#-------------------------------------------------------------------------------------------------------#

#Обработка выбора стиля
@router.callback_query(lambda c: c.data.startswith('style_'))
async def set_style(callback: CallbackQuery):
	style = callback.data.split('_')[1]
	users = load_users()
	user_id = str(callback.from_user.id)

	if user_id in users:
		users[user_id]['tone'] = style
		save_user(user_id, users[user_id])
		await callback.message.edit_text(f"✅ Стиль общения установлен: {style}")
	else:
		await callback.message.edit_text('⚠️ Сначала нужно пройти регистрацию — нажми /start')
#-------------------------------------------------------------------------------------------------------#

#Добавляет кнопку с возможностью общения с ИИ
@router.message(Command('ask'))
async def ask_sage(message: types.Message):
	await message.answer("💭 Думаю над ответом...")

	user_input = message.text.replace('/ask', '').strip()
	if not user_input:
		await message.answer("❓ Напиши, что тебя беспокоит. Пример: /ask как мне контролировать желания")
		return

	reply = await generate_reply(user_id = message.from_user.id, user_message = user_input)
	await message.answer(reply)
#-------------------------------------------------------------------------------------------------------#\

# Команда /affirmation
@router.message(Command('affirmation'))
async def give_affirmation(message: types.Message):
	period = get_period()
	user_id = message.from_user.id

	if affirmation_db.is_alredy_done(user_id, period):
		await message.answer(f"🕐 Ты уже получал аффирмацию сегодня.\nПриходи в течении ~ 6 часов... 💬")
		return

	with open('assets/affirmations.json', 'r', encoding='utf-8') as f:
		data = json.load(f)

	# 1 шанс из 3 — генерация
	if random.randint(1, 3) == 1 or len(data.get(period, [])) < 3:
		affirmation = await generate_affirmations(period)
	else:
		affirmation = random.choice(data[period])

	text = affirmation['text']
	image_url = affirmation.get('image', None)

	# Засчитываем XP
	xp_manager = XPManager(user_id)
	xp_manager.add_xp(15)
	affirmation_db.mark_done(user_id, period)

	# Отправка изображения с подписью
	try:
		if image_url:
			# Проверяем, что URL выглядит валидным
			if image_url.startswith(('http://', 'https://')):
				await message.answer_photo(photo=image_url, caption=f"🧘 {text}\n\n+15 XP\n{xp_manager.status()}")
			else:
				await message.answer(f"🧘 {text}\n\n+15 XP\n{xp_manager.status()}")
		else:
			await message.answer(f"🧘 {text}\n\n+15 XP\n{xp_manager.status()}")
	except Exception as e:
		print(f"Ошибка: {e}")
		await message.answer("🧘 Я сосредоточен и развиваюсь каждый день\n\n+15 XP")

#-------------------------------------------------------------------------------------------------------#
@router.message(Command('feedback'))
async def feedback_cmd(message: types.Message):
	"""Отправка обратной связи"""
	await message.answer("💬 Напиши свое предложение, жалобу или отзыв.\n"
        "Мы читаем все сообщения и улучшаем бота благодаря вам!",
	                     reply_markup=types.ForceReply(selective=True)
	                     )

@router.message(F.reply_to_message & F.reply_to_message.text.contains ('💬 Напиши свое предложение'))
async def process_feedback(message: types.Message):
	"""Обработка содержимого фидбека"""
	feedback_text = message.text
	user_id = message.from_user.id

	try:
		#Сохраняем в БД
		async with aiosqlite.connect(SQLITE_DB_PATH) as db:
			await db.execute(
				"INSERT INTO feedback (user_id, message) VALUES (?, ?)",
				(user_id, feedback_text)
			)
			await db.commit()
		await message.answer("✅ Спасибо! Твой отзыв сохранён и будет рассмотрен.")

		# Отправка админу
		admin_msg = (f'📢 Новый фидбек от @{message.from_user.username}!\n'
		             f'{feedback_text}\n\n'
		             f'ID: {user_id}')
		await message.bot.send_message(ADMIN_ID, admin_msg)

	except Exception as e:
		print(f'Feedback error: {e}')
		await message.answer(("⚠️ Произошла ошибка при сохранении отзыва."))

#Добавим команду для админа
@router.message(Command('feedbacks'))
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
@router.message(Command('resolve_fb'))
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
@router.message(Command('help'))
async def help_command(message: types.Message):
	# Проверяем, является ли пользователь админом
	if is_admin(message.from_user.id):
		admin_help_text = """
			<b>🛠 Административные команды:</b>

		/feedbacks - Просмотр новых отзывов
		/resolve_fb [id] - Пометить отзыв как обработанный
		/stats - Статистика по пользователям(В разработке!!!)
		/broadcast - Рассылка сообщения всем пользователям (В разработке!!!)

		<b>🔜 В разработке:</b>
		/ban - Заблокировать пользователя
		/promo - Создать промокод
		/export - Выгрузка данных
			"""
	await message.answer(admin_help_text,
	                     reply_markup=ReplyKeyboardRemove(),
	                     parse_mode='HTML')
	# Основные команды для всех пользователей
	user_help_text = """
	<b>🌿 Основные команды:</b>

	/start - Начало работы с ботом
	/help - Показать это сообщение
	/profile - Ваш прогресс и статистика (В разработке!!!)
	/affirmation - Получить аффирмацию дня
	/ask [вопрос] - Задать вопрос мудрецу
	/feedback - Оставить отзыв или предложение
	/style - Выбрать стиль общения
	
	<b>📝 Работа с дневником:</b>
	/day - Записать сегодняшние мысли (В разработке!!!)
	/reset_day - Сбросить текущий день (В разработке!!!)
	
	<b>🎮 Геймификация:</b>
	/me - Ваш текущий уровень и XP
	/quests - Активные задания (В разработке!!!)
	
	<b>🔜 Скоро появится:</b>
	/meditate - Управляемая медитация
	/achievements - Ваши достижения
	/group - Чат поддержки
	/reminder - Напоминания

	"""
	# Создаем клавиатуру с быстрыми командами
	builder = ReplyKeyboardBuilder()
	builder.row(
		KeyboardButton(text = '/affirmation'),
		KeyboardButton(text = '/ask'),
	)
	builder.row(
		KeyboardButton(text = '/day'),
		KeyboardButton(text = '/profile'),
	)
	await message.answer(user_help_text,
	                     reply_markup = builder.as_markup(resize_keyboard = True),
	                     parse_mode = 'HTML')


#-------------------------------------------------------------------------------------------------------#
#-------------------------------------------------------------------------------------------------------#
#-------------------------------------------------------------------------------------------------------#
#-------------------------------------------------------------------------------------------------------#
#-------------------------------------------------------------------------------------------------------#
#-------------------------------------------------------------------------------------------------------#
#-------------------------------------------------------------------------------------------------------#
#-------------------------------------------------------------------------------------------------------#

#-------------------------------------------------------------------------------------------------------#
#Кнопка фидбека в главном меню
@router.message(F.text == "💬 Оставить отзыв")
async def feedback_button(message: types.Message):
	await feedback_cmd(message)
#вступительное сообщение Должно быть в конце
@router.message()
async def intro_message(message: types.Message):
	welcome_text = (
		"🌿 Добро пожаловать в \"Чистый Ум\" — бота-наставника на пути мужской силы и ясности разума.\n\n"
		"Здесь ты научишься:\n"
		"— Воздержанию и дисциплине\n"
		"— Контролю над импульсами\n"
		"— Самонаблюдению и программированию\n\n"
		"Я не просто бот. Я — твой спутник.\n"
		"Нажми /start и начнём путь 👣")

	#Добавить кнопку фидбека в главное меню:
	keyboard = ReplyKeyboardMarkup(
		keyboard=[
			[KeyboardButton(text="💬 Оставить отзыв")],
			[KeyboardButton(text="/start"), KeyboardButton(text="/help")]
		],
		resize_keyboard = True
	)
	await message.answer(welcome_text, reply_markup=keyboard)

#-------------------------------------------------------------------------------------------------------#
