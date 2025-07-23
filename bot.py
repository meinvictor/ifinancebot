import telebot
from telebot import types
import os
from dotenv import load_dotenv

# Завантаження .env файлу
load_dotenv()
TOKEN = os.getenv("TOKEN")

# Ініціалізація бота
bot = telebot.TeleBot(TOKEN)

# Тимчасове сховище витрат у памʼяті
expenses = {}
user_temp_data = {}

# Команда /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        types.KeyboardButton('Додати'),
        types.KeyboardButton('Статистика'),
        types.KeyboardButton('Баланс')
    )
    bot.send_message(
        message.chat.id,
        "👋 Привіт! Я бот для обліку витрат.\nОбери дію кнопкою нижче або введи вручну.",
        reply_markup=markup
    )

# ДОДАВАННЯ ВИТРАТ — крок 1: запит суми
@bot.message_handler(func=lambda message: message.text == 'Додати')
def handle_add_button(message):
    bot.send_message(message.chat.id, "💵 Введи суму витрати:")
    user_temp_data[message.chat.id] = {'step': 'awaiting_amount'}

# Обробка введеної суми — крок 2: вибір категорії
@bot.message_handler(func=lambda message: user_temp_data.get(message.chat.id, {}).get('step') == 'awaiting_amount')
def handle_amount_input(message):
    try:
        amount = float(message.text)
        user_temp_data[message.chat.id]['amount'] = amount
        user_temp_data[message.chat.id]['step'] = 'awaiting_category'

        markup = types.InlineKeyboardMarkup()
        for cat in ['Їжа', 'Транспорт', 'Покупки', 'Інше']:
            markup.add(types.InlineKeyboardButton(text=cat, callback_data=f'category:{cat}'))

        bot.send_message(message.chat.id, "📂 Вибери категорію:", reply_markup=markup)
    except:
        bot.send_message(message.chat.id, "❌ Введи суму числом (наприклад: 150)")

# Обробка вибору категорії — крок 3: запис
@bot.callback_query_handler(func=lambda call: call.data.startswith('category:'))
def handle_category_selection(call):
    chat_id = call.message.chat.id
    category = call.data.split(':')[1]

    amount = user_temp_data.get(chat_id, {}).get('amount')
    if amount is None:
        bot.send_message(chat_id, "⚠️ Сталася помилка. Спробуй ще раз натиснути 'Додати'")
        return

    if chat_id not in expenses:
        expenses[chat_id] = []
    expenses[chat_id].append({'amount': amount, 'category': category})

    # Очистити тимчасові дані
    user_temp_data.pop(chat_id, None)

    bot.send_message(chat_id, f"✅ Додано: {amount:.2f} грн на \"{category}\"")

# Кнопка "Статистика"
@bot.message_handler(func=lambda message: message.text == 'Статистика')
def handle_stats_button(message):
    show_stats(message)

# Кнопка "Баланс"
@bot.message_handler(func=lambda message: message.text == 'Баланс')
def handle_balance_button(message):
    show_balance(message)

# Команда /add (залишається як альтернатива)
@bot.message_handler(commands=['add'])
def handle_add_command(message):
    bot.send_message(message.chat.id, "📝 Введи витрату у форматі: `сума категорія`\nНаприклад: `150 транспорт`")

# Прямий текстовий ввід у форматі "сума категорія"
@bot.message_handler(func=lambda message: not message.text.startswith('/'))
def handle_expense_input(message):
    try:
        amount, category = message.text.split(maxsplit=1)
        amount = float(amount)
        chat_id = message.chat.id

        if chat_id not in expenses:
            expenses[chat_id] = []

        expenses[chat_id].append({'amount': amount, 'category': category})
        bot.send_message(chat_id, f"✅ Додано: {amount} грн на \"{category}\"")
    except:
        bot.send_message(message.chat.id, "❌ Неправильний формат. Введи: `сума категорія`, наприклад: `100 їжа`")

# Статистика (через команду або кнопку)
@bot.message_handler(commands=['stats'])
def handle_stats_command(message):
    show_stats(message)

def show_stats(message):
    chat_id = message.chat.id
    if chat_id not in expenses or not expenses[chat_id]:
        bot.send_message(chat_id, "📊 Статистика поки порожня.")
        return

    stats = {}
    for item in expenses[chat_id]:
        category = item['category']
        stats[category] = stats.get(category, 0) + item['amount']

    response = "📈 Статистика витрат:\n"
    for category, total in stats.items():
        response += f"• {category}: {total:.2f} грн\n"
    bot.send_message(chat_id, response)

# Баланс (через команду або кнопку)
@bot.message_handler(commands=['balance'])
def handle_balance_command(message):
    show_balance(message)

def show_balance(message):
    chat_id = message.chat.id
    if chat_id not in expenses or not expenses[chat_id]:
        bot.send_message(chat_id, "💰 Баланс: 0 грн")
        return

    total = sum(item['amount'] for item in expenses[chat_id])
    bot.send_message(chat_id, f"💰 Загальні витрати: {total:.2f} грн")

# Запуск бота
bot.polling()
