#core/content_ai - file
#-------------------------------------------------------------------------------------------------------#

import json
import os.path
import random
from random import randint

import requests
from openai import AsyncOpenAI
from datetime import datetime
from config import GPT_TOKEN, UNSPLASH_KEY, DAILY_TOKEN_LIMIT
from core.context_manager import ContextManager
from core.token_manager import token_db
import tiktoken

UNSPLASH_ACCESS_KEY = UNSPLASH_KEY

AFF_PATH = 'assets/affirmations.json'
# Инициализируем OpenAI-клиент один раз (оптимизация)
client = AsyncOpenAI(api_key=GPT_TOKEN)
model_name = "gpt-3.5-turbo"

# Тарифы OpenAI (актуальные на 2024)
INPUT_PRICE = 0.50 / 1_000_000  # $ за токен ввода
OUTPUT_PRICE = 1.50 / 1_000_000  # $ за токен вывода
ESTIMATED_BALANCE = 5.00  # Ваш депозит $5
MAX_INPUT_TOKENS = 1500 #максимум токенов на ввод
MAX_OUTPUT_TOKENS = 400#максимум токенов на вывод
TOKENS_FOR_USERS = DAILY_TOKEN_LIMIT #всего токенов на пользователя

# Основная функция генерации ответа
async def generate_reply(user_id: int, user_message: str) -> str:
    # Проверяем длину вопроса
    encoding = tiktoken.encoding_for_model(model_name)
    current_tokens  = len(encoding.encode(user_message))

    if current_tokens  > MAX_INPUT_TOKENS:
        return f'❌ Вопрос слишком длинный. Сократите до ~{MAX_INPUT_TOKENS} символов.'
    if token_db.get_tokens(user_id) >= TOKENS_FOR_USERS: # Лимит на 1 пользователя в день
        return "❌ Лимит токенов исчерпан. Попробуйте завтра."
    if is_gibberish(user_message):
        return f"⚠️ Запрос отклонён: некорректный ввод."
# -------------------------------------------------------------------------------------------------------#
    tone = get_user_tone(user_id)

    if tone == 'soft':
        style_prompt = (""" Ты — понимающий и терпеливый помощник. Твой стиль — поддержка без давления.Ты не давишь, не критикуешь, а мягко направляешь.Если человек оступился — помогаешь ему встать, а не ругаешь.Ты веришь в постепенный прогресс и избегаешь резких формулировок.Ты не командуешь, а предлагаешь:"Попробуй сделать маленький шаг сегодня. Даже если не получится — это нормально."Ты избегаешь: Жестких требований;Осуждения;Давления""")

    elif tone == 'strict':
        style_prompt = (""" Ты — требовательный наставник, который не принимает отговорок.Ты говоришь прямо, без сюсюканья. Если человек слабеет — ты жестко возвращаешь его в колею.Ты не даешь расслабляться, но при этом справедлив.Ты не поддерживаешь, а мотивируешь через вызов:"Если сейчас сдашься — потом пожалеешь. Соберись и сделай!"Ты избегаешь:Жалости;Растянутых объяснений;Снисходительности""")

    elif tone == 'funny':
        style_prompt = (""" Ты — друг, который подбадривает через юмор и мемы.Ты не даешь заскучать, превращаешь сложные темы в игру.Ты не читаешь нотации, а вдохновляешь через абсурд и стёб.Ты не грузишь, а разряжаешь обстановку:"Ну что, снова поддался 'фабрике грёблей'? Ладно, завтра исправимся — сегодня просто посмейся над собой."Ты избегаешь:Заумных советов; Серьезных нравоучений; Сухого тона""")

    elif tone == 'standard':
        style_prompt = ("""Ты — мужской наставник.Пиши человечнее,как будто-то ты в чате в переписке.Стиль общения свободный.Пишешь краткои максимум сути. Помогаешь с:1. Воздержанием (контроль импульсов)2. Дисциплиной (режим, спорт)3. Аскезами (сила воли)4. Медитацией (осознанность)5. Выходом из депрессии**Правила:**- Тон: поддерживающий- Даешь конкретные техники(пример: «метод 5 секунд»)- От тебя требуется:Понимание и разбор проблемы совет и короткая мотивация**Запрещено:** осуждать, диагностировать, рекламировать религии""")

    else:
        style_prompt = ("""Ты — наставник. Отвечай с умом и добротой.""")
# -------------------------------------------------------------------------------------------------------#

    # Сохраняем вопрос пользователя
    await ContextManager.save_message(user_id, user_message, 'user')

    # Получаем контекст
    history = await ContextManager.get_recent_history(user_id)
    compressed_context = await ContextManager.get_compressed_context(user_id)

    # Проверяем общий размер токенов
    total_tokens = current_tokens + sum(len(encoding.encode(msg['content'])) for msg in history)
    if total_tokens > 1500:
        await ContextManager.compress_context(user_id, force=True)
        history = await ContextManager.get_recent_history(user_id) # Обновляем историю после сжатия


    message = [
                {
                    # Описываем роль модели Инструкция GPT — как ему вести себя
                    'role': 'system',
                    'content':  style_prompt
                }
            ]

    # Добавляем историю в правильном порядке (не reversed)
    message.extend(history) ## Добавляем историю диалога

    if compressed_context:
        message.insert(1, {
            'role': 'system',
            'content': f"Контекст из предыдущих диалогов: \n {compressed_context}"
        })
    message.append({
        'role': 'user',
        'content': user_message
    })

    try:
        response = await client.chat.completions.create(
            model = model_name,
            messages = message,

            temperature=0.7, #Контроль креативности (0.3 — строго, 1.0 — свободно)
            max_tokens =  MAX_OUTPUT_TOKENS,
            top_p=0.9,
            frequency_penalty=0.3, #Наказание за повтор слов, делает речь живее
        )
        token_db.add_tokens(user_id, response.usage.total_tokens)

        # Сохраняем ответ бота
        reply = response.choices[0].message.content
        await ContextManager.save_message(user_id, reply, 'assistant')

        # Периодическое сжатие контекста (раз в 10 диалогов)
        if random.randint(1, 10) == 1:
            await ContextManager.compress_context(user_id)

        # Рассчет стоимости
        used_tokens = response.usage.total_tokens
        cost = (response.usage.prompt_tokens * INPUT_PRICE +
                response.usage.completion_tokens * OUTPUT_PRICE)

        # Простое отображение в консоли
        cost_rounded = round(cost, 5)
        remaining = ESTIMATED_BALANCE - cost
        print(f"\n[Токены: {used_tokens} | Стоимость: ${cost_rounded:.5f} | Осталось: ~${remaining:.2f}]")

        return reply.strip()

    except Exception as e:
        return f'"⚠️ Ошибка при обращении к ИИ: {str(e)}'
#-------------------------------------------------------------------------------------------------------#

# Защита первого уровня от спама и бессмысленных сообщений
def is_gibberish(text: str) -> bool:
    """Улучшенная проверка на бессмысленный текст"""
    # Удаляем пунктуацию и приводим к нижнему регистру
    clean_text = ''.join(c.lower() for c in text if c.isalpha() or c.isspace())

    # Слишком короткий текст
    if len(clean_text) < 10:
        return True

    # Проверяем повторяющиеся слова (если больше 3 слов)
    words = clean_text.split()
    if len(words) > 3 and len(set(words)) < len(words) / 2:
        return True

    # Проверяем повторяющиеся последовательности символов
    if any(text.count(text[i:i + 5]) > 2 for i in range(len(text) - 4)):
        return True

    return False

#-------------------------------------------------------------------------------------------------------#
#Подгрузка тонов из json базы данных
def get_user_tone(user_id: int) -> str:
    DB_USERS_PATH = os.path.join('db', 'users.json')
    if not os.path.exists(DB_USERS_PATH):
        return 'soft'
    with open(DB_USERS_PATH, 'r', encoding='utf-8') as f:
        users = json.load(f)
    user = users.get(str(user_id))
    return user.get('tone', 'soft') if user else 'soft'
#-------------------------------------------------------------------------------------------------------#

#    Создание новой аффирмации через GPT
async def generate_affirmations(period: str) -> dict:
    prompt = f'Придумай вдохновляющую, аффирмацию на тему саморазвития для времени: {period}.Со смыслом и глубокие. Не забывай хвалить в тернистом пути развивающегося. Не повторяй уже известные. Только текст.'
    response = await generate_reply(user_id = 999, user_message = prompt)

    # Псевдо-изображение (можно заменить на запрос к Unsplash)
    image_url = await get_unsplash_image(period)

    # Загружаем и обновляем JSON
    with open(AFF_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

        new_item ={
            'text': response.strip('"\''),
            'image': image_url
        }
        data[period].append(new_item)
        with open(AFF_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        if image_url.startswith("https://images.unsplash.com"):
            new_item['image_source'] = 'unsplash'
        return new_item
#-------------------------------------------------------------------------------------------------------#

#случайное изображение по тематике периода
async def get_unsplash_image(period: str) -> str:
    """Получает случайное изображение по тематике периода"""
    themes = {
        "morning": "sunrise,morning,coffee,meditation",
        "day": "productivity,work,focus,discipline",
        "evening": "sunset,evening,relax,peace"
    }
    try:
        url = "https://api.unsplash.com/photos/random"
        params = {
            'query': themes[period],
            'client_id': UNSPLASH_ACCESS_KEY,
            'orientation': 'landscape',
            'w': 600,
            'h': 400,
        }
        response = requests.get(url, params=params, timeout=5).json()
        return response['urls']['regular']
    except Exception as e:
        print(f"Ошибка Unsplash API: {e}")
        # Fallback на стандартный URL с таймстампом для уникальности
        return f"https://source.unsplash.com/600x400/?{themes[period]},{int(datetime.now().timestamp())}"

#-------------------------------------------------------------------------------------------------------#
