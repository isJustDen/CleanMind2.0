#handlers.py file
import sqlite3

from aiogram  import Router, types
from aiogram.filters import CommandStart, Command
import json
import os
from datetime import datetime

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from core.content_ai import generate_reply
from core.xp_engine import XPManager

router = Router()
os.makedirs("db", exist_ok=True)
DB_PATH = os.path.join("db", 'users.json')
#-------------------------------------------------------------------------------------------------------#

#Загрузка параметров пользователя из JSON файла
def load_users():
	if not os.path.exists(DB_PATH) or os.path.getsize(DB_PATH) == 0:
		return {}
	try:
		with open(DB_PATH, 'r', encoding='utf-8') as f:
			return json.load(f)
	except json.JSONDecodeError:
		return {}
#-------------------------------------------------------------------------------------------------------#

#сохранение параметров пользователя
def save_user(user_id, data):
	users = load_users()
	users[str(user_id)] = data
	with open(DB_PATH, 'w', encoding='utf-8') as f:
		json.dump(users, f, ensure_ascii = False, indent = 4 )

# Команда start. Сохранение пользователя в JSON и отображение о его статусе в регистрации
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

#Добовляет кнопку с возможность общения с ИИ
@router.message(Command('ask'))
async def ask_sage(message: types.Message):
	await message.answer("💭 Думаю над ответом...")

	user_input = message.text.replace('/ask', '').strip()
	if not user_input:
		await message.answer("❓ Напиши, что тебя беспокоит. Пример: /ask как мне контролировать желания")
		return

	reply = await generate_reply(user_id = message.from_user.id, user_message = user_input)
	await message.answer(reply)
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