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

# Обробка команди /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton('Додати')
    btn2 = types.KeyboardButton('Статистика')
    btn3 = types.KeyboardButton('Баланс')
    markup.add(btn1, btn2, btn3)
    bot.send_message(
        message.chat.id,
        "👋 Привіт! Я бот для обліку витрат.\nОбери дію кнопкою нижче або введи вручну.",
        reply_markup=markup
    )

# Обробка кнопки "Додати"
@bot.message_handler(func=lambda message: message.text == 'Додати')
def handle_add_button(message):
    bot.send_message(message.chat.id, "📝 Введи витрату у форматі: `сума категорія`\nНаприклад: `150 транспорт`")

# Обробка кнопки "Статистика"
@bot.message_handler(func=lambda message: message.text == 'Статистика')
def handle_stats_button(message):
    show_stats(message)

# Обробка кнопки "Баланс"
@bot.message_handler(func=lambda message: message.text == 'Баланс')
def handle_balance_button(message):
    show_balance(message)

# Обробка текстового вводу витрати
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

# Обробка команди /add (показує інструкцію)
@bot.message_handler(commands=['add'])
def handle_add_command(message):
    bot.send_message(message.chat.id, "📝 Введи витрату у форматі: `сума категорія`\nНаприклад: `150 транспорт`")

# Обробка команди /stats або кнопки "Статистика"
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

# Обробка команди /balance або кнопки "Баланс"
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
