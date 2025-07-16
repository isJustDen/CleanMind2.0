#handlers.py file
import sqlite3
import random
from zoneinfo import ZoneInfo

from aiogram  import Router, types
from aiogram.filters import CommandStart, Command
import json
import os
from datetime import datetime

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton

from core.affirmation_tracker import affirmation_db
from core.content_ai import generate_reply, generate_affirmations
from core.xp_engine import XPManager

router = Router()
os.makedirs("db", exist_ok=True)
DB_PATH = os.path.join("db", 'users.json')
#-------------------------------------------------------------------------------------------------------#

#Функция Загрузка параметров пользователя из JSON файла
def load_users():
	if not os.path.exists(DB_PATH) or os.path.getsize(DB_PATH) == 0:
		return {}
	try:
		with open(DB_PATH, 'r', encoding='utf-8') as f:
			return json.load(f)
	except json.JSONDecodeError:
		return {}
#-------------------------------------------------------------------------------------------------------#

# Функция сохранение параметров пользователя
def save_user(user_id, data):
	users = load_users()
	users[str(user_id)] = data
	with open(DB_PATH, 'w', encoding='utf-8') as f:
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
	if random.randint(1, 3) == 1 or len(data.get(period, []) < 3):
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
#-------------------------------------------------------------------------------------------------------#
#-------------------------------------------------------------------------------------------------------#
#-------------------------------------------------------------------------------------------------------#
#-------------------------------------------------------------------------------------------------------#
#-------------------------------------------------------------------------------------------------------#
#-------------------------------------------------------------------------------------------------------#
#-------------------------------------------------------------------------------------------------------#
#-------------------------------------------------------------------------------------------------------#

#-------------------------------------------------------------------------------------------------------#
#вступительное сообщение Должно быть в конце
@router.message()
async def intro_message(message: types.Message):
	await message.answer(
		"🌿 Добро пожаловать в \"Чистый Ум\" — бота-наставника на пути мужской силы и ясности разума.\n\n"
		"Здесь ты научишься:\n"
		"— Воздержанию и дисциплине\n"
		"— Контролю над импульсами\n"
		"— Самонаблюдению и программированию\n\n"
		"Я не просто бот. Я — твой спутник.\n"
		"Нажми /start и начнём путь 👣"
	)
#-------------------------------------------------------------------------------------------------------#
