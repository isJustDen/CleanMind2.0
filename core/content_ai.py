#content_ai - file
#-------------------------------------------------------------------------------------------------------#
from openai import AsyncOpenAI

from config import GPT_TOKEN
from core.token_manager import token_db

# Инициализируем OpenAI-клиент один раз (оптимизация)
client = AsyncOpenAI(api_key=GPT_TOKEN)

# Тарифы OpenAI (актуальные на 2024)
INPUT_PRICE = 0.50 / 1_000_000  # $ за токен ввода
OUTPUT_PRICE = 1.50 / 1_000_000  # $ за токен вывода
ESTIMATED_BALANCE = 5.00  # Ваш депозит $5


# Основная функция генерации ответа
async def generate_reply(user_id: int, user_message: str) -> str:
    if token_db.get_tokens(user_id) >= 5000: # Лимит на 1 пользователя в день
        return "❌ Лимит токенов исчерпан. Попробуйте завтра."
    if is_gibberish(user_message):
        return f"⚠️ Запрос отклонён: некорректный ввод."
    try:
        response = await client.chat.completions.create(
            model = "gpt-3.5-turbo",
            messages = [
                {
                    # Описываем роль модели Инструкция GPT — как ему вести себя
                    'role': 'system',
                    'content':  ('Ты — мужской наставник.Пиши человечнее, как будто-то ты в чате в переписке. Стиль общения свободный.Пишешь кратко и максимум сути. Помогаешь с:1. Воздержанием (контроль импульсов)2. Дисциплиной (режим, спорт)3. Аскезами (сила воли)4. Медитацией (осознанность)5. Выходом из депрессии**Правила:**- Тон: поддерживающий- Даешь конкретные техники (пример: «метод 5 секунд»)- От тебя требуется:Понимание и разбор проблемы совет и короткая мотивация**Запрещено:** осуждать, диагностировать, рекламировать религии')
                },
                {
                    #Описываем роль пользователя
                    'role': 'user',
                    'content': user_message
                }
            ],
            temperature=0.7, #Контроль креативности (0.3 — строго, 1.0 — свободно)
            max_tokens =  350,
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