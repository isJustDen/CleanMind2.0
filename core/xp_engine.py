#xp_engine.py file

import json
import os


DB_PATH = os.path.join('db', 'users.json')

# Загрузка всех пользователей
def load_users():
	if not os.path.exists(DB_PATH):
		return{}
	with open(DB_PATH, 'r', encoding='utf-8') as f:
		return json.load(f)
#-------------------------------------------------------------------------------------------------------#

#Сохраняем всех пользователей
def save_users(users: dict):
	with open(DB_PATH, 'w', encoding='utf-8') as f:
		json.dump(users, f, ensure_ascii=False, indent=4)
#-------------------------------------------------------------------------------------------------------#

#Класс прокачки
class XPManager:
	def __init__(self, user_id: int):
		self.user_id = str(user_id)
		self.users = load_users()

		# Если пользователь не найден — создаём его
		if self.user_id not in self.users:
			self.users[self.user_id] = {
				'experience': 0,
				'level': 1,
			}
		self.user = self.users[self.user_id]

	# Текущий XP
	@property
	def xp(self):
		return self.user.get('experience', 0)

	# Текущий уровень
	@property
	def level(self):
		return self.user.get('level', 1)

	#Добавляем XP
	def add_xp(self, amount: int):
		self.user['experience'] += amount

		# Проверка на уровень
		while self.user['experience'] >= self.level * 100:
			self.user['experience'] -= self.level * 100
			self.user['level'] += 1
			
		self.save()

	# Сохраняем изменения
	def save(self):
		self.users[self.user_id] = self.user
		save_users(self.users)

	#Возвращаем статус как текст
	def status(self):
		return f"🏅 Уровень: {self.level} | 📈 XP: {self.xp}/{self.level * 100}"
#-------------------------------------------------------------------------------------------------------#

