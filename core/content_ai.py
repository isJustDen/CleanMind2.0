#content_ai - file
#-------------------------------------------------------------------------------------------------------#
import json
import os.path

from openai import AsyncOpenAI

from config import GPT_TOKEN
from core.token_manager import token_db
import tiktoken
# Инициализируем OpenAI-клиент один раз (оптимизация)
client = AsyncOpenAI(api_key=GPT_TOKEN)
model_name = "gpt-3.5-turbo"

# Тарифы OpenAI (актуальные на 2024)
INPUT_PRICE = 0.50 / 1_000_000  # $ за токен ввода
OUTPUT_PRICE = 1.50 / 1_000_000  # $ за токен вывода
ESTIMATED_BALANCE = 5.00  # Ваш депозит $5
MAX_INPUT_TOKENS = 1500 #максимум токенов на ввод
MAX_OUTPUT_TOKENS = 400#максимум токенов на вывод
TOKENS_FOR_USERS = 15000 #всего токенов на пользователя

# Основная функция генерации ответа
async def generate_reply(user_id: int, user_message: str) -> str:
    # Проверяем длину вопроса
    encoding = tiktoken.encoding_for_model(model_name)
    input_tokens = len(encoding.encode(user_message))
    if input_tokens > MAX_INPUT_TOKENS:
        return f'❌ Вопрос слишком длинный. Сократите до ~{MAX_INPUT_TOKENS} символов.'
    if token_db.get_tokens(user_id) >= TOKENS_FOR_USERS: # Лимит на 1 пользователя в день
        return "❌ Лимит токенов исчерпан. Попробуйте завтра."
    if is_gibberish(user_message):
        return f"⚠️ Запрос отклонён: некорректный ввод."
# -------------------------------------------------------------------------------------------------------#
    tone = get_user_tone(user_id)

    if tone == 'soft':
        style_prompt = (""" Ты — понимающий и терпеливый помощник. Твой стиль — поддержка без давления. 
                            Ты не давишь, не критикуешь, а мягко направляешь. 
                            Если человек оступился — помогаешь ему встать, а не ругаешь. 
                            Ты веришь в постепенный прогресс и избегаешь резких формулировок.
                            Ты не командуешь, а предлагаешь:
                            "Попробуй сделать маленький шаг сегодня. Даже если не получится — это нормально."
                            Ты избегаешь: Жестких требований;Осуждения;Давления""")

    elif tone == 'strict':
        style_prompt = (""" Ты — требовательный наставник, который не принимает отговорок. 
                            Ты говоришь прямо, без сюсюканья. Если человек слабеет — ты жестко возвращаешь его в колею. 
                            Ты не даешь расслабляться, но при этом справедлив.
                            Ты не поддерживаешь, а мотивируешь через вызов:
                            "Если сейчас сдашься — потом пожалеешь. Соберись и сделай!"
                            Ты избегаешь:Жалости;Растянутых объяснений;Снисходительности""")

    elif tone == 'funny':
        style_prompt = (""" Ты — друг, который подбадривает через юмор и мемы.
                            Ты не даешь заскучать, превращаешь сложные темы в игру. 
                            Ты не читаешь нотации, а вдохновляешь через абсурд и стёб.
                            Ты не грузишь, а разряжаешь обстановку:
                            "Ну что, снова поддался 'фабрике грёблей'? Ладно, завтра исправимся — сегодня просто посмейся над собой."
                            Ты избегаешь:Заумных советов; Серьезных нравоучений; Сухого тона""")

    elif tone == 'standard':
        style_prompt = ("""Ты — мужской наставник.Пиши человечнее,
                                 как будто-то ты в чате в переписке. 
                                 Стиль общения свободный.Пишешь кратко 
                                 и максимум сути. Помогаешь с:
                                 1. Воздержанием (контроль импульсов)
                                 2. Дисциплиной (режим, спорт)
                                 3. Аскезами (сила воли)
                                 4. Медитацией (осознанность)
                                 5. Выходом из депрессии
                                 **Правила:**- Тон: поддерживающий- Даешь конкретные техники 
                                 (пример: «метод 5 секунд»)- От тебя требуется:
                                 Понимание и разбор проблемы совет и короткая мотивация
                                 **Запрещено:** осуждать, диагностировать, рекламировать религии""")

    else:
        style_prompt = ("""Ты — наставник. Отвечай с умом и добротой.""")
# -------------------------------------------------------------------------------------------------------#

    try:
        response = await client.chat.completions.create(
            model = model_name,
            messages = [
                {
                    # Описываем роль модели Инструкция GPT — как ему вести себя
                    'role': 'system',
                    'content':  style_prompt
                },
                {
                    #Описываем роль пользователя
                    'role': 'user',
                    'content': user_message
                }
            ],
            temperature=0.7, #Контроль креативности (0.3 — строго, 1.0 — свободно)
            max_tokens =  MAX_OUTPUT_TOKENS,
            top_p=0.9,
            frequency_penalty=0.3, #Наказание за повтор слов, делает речь живее
        )
        token_db.add_tokens(user_id, response.usage.total_tokens)

        # Рассчет стоимости
        used_tokens = response.usage.total_tokens
        cost = (response.usage.prompt_tokens * INPUT_PRICE +
                response.usage.completion_tokens * OUTPUT_PRICE)

        # Простое отображение в консоли
        cost_rounded = round(cost, 5)
        remaining = ESTIMATED_BALANCE - cost
        print(f"\n[Токены: {used_tokens} | Стоимость: ${cost_rounded:.5f} | Осталось: ~${remaining:.2f}]")

        return response.choices[0].message.content.strip()

    except Exception as e:
        return f'"⚠️ Ошибка при обращении к GPT: {str(e)}'

def is_gibberish(text: str) -> bool:
    # Проверка на повторяющиеся символы/слова
    if len(set(text))< len(text)*0.3: # 70% повторений
        return True
    return False

#-------------------------------------------------------------------------------------------------------#
#Подгрузка тонов из json базы данных
def get_user_tone(user_id: int) -> str:
    db_path = os.path.join('db', 'users.json')
    if not os.path.exists(db_path):
        return 'soft'
    with open(db_path, 'r', encoding='utf-8') as f:
        users = json.load(f)
    user = users.get(str(user_id))
    return user.get('tone', 'soft') if user else 'soft'
#-------------------------------------------------------------------------------------------------------#
