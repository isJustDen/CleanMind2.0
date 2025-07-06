from aiogram  import Router, types
from aiogram.filters import CommandStart
import json
import os
from datetime import datetime

router = Router()
os.makedirs("db", exist_ok=True)
DB_PATH = os.path.join("db", 'users.json')

def load_users():
	if not os.path.exists(DB_PATH) or os.path.getsize(DB_PATH) == 0:
		return {}
	try:
		with open(DB_PATH, 'r', encoding='utf-8') as f:
			return json.load(f)
	except json.JSONDecodeError:
		return {}

def save_user(user_id, data):
	users = load_users()
	users[str(user_id)] = data
	with open(DB_PATH, 'w', encoding='utf-8') as f:
		json.dump(users, f, ensure_ascii = False, indent = 4 )

@router.message(CommandStart())
async def start_cmd(message: types.Message):
	user = message.from_user
	user_data = {
		'id': user.id,
		'name': user.full_name,
		'username': user.username,
		'registered': datetime.now().isoformat()
	}
	if str(user.id) in load_users():
		await message.answer("Вы уже зарегистрированы!")
		return
	else:
		save_user(user.id, user_data)
		await message.answer(f'Привет, {user.first_name}! Добро пожаловаться в 🌿 Чистый Ум.\nТы зарегистрирован."')