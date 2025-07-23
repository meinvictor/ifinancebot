import telebot
from telebot import types
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TOKEN")

bot = telebot.TeleBot(TOKEN)

# Словник для збереження витрат (тимчасово)
expenses = {}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton('Додати')
    btn2 = types.KeyboardButton('Статистика')
    btn3 = types.KeyboardButton('Баланс')
    markup.add(btn1, btn2, btn3)
    bot.send_message(message.chat.id, "👋 Привіт! Обери дію:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == 'Додати')
def handle_add_button(message):
    bot.send_message(message.chat.id, "📝 Введи витрату у форматі: сума категорія (наприклад: `200 їжа`)")

@bot.message_handler(func=lambda message: message.text == 'Статистика')
def handle_stats_button(message):
    bot.send_message(message.chat.id, "/stats")

@bot.message_handler(func=lambda message: message.text == 'Баланс')
def handle_balance_button(message):
    bot.send_message(message.chat.id, "/balance")

@bot.message_handler(commands=['add'])
def handle_add_command(message):
    bot.send_message(message.chat.id, "📝 Введи витрату у форматі: сума категорія (наприклад: `200 їжа`)")

@bot.message_handler(func=lambda message: message.text.startswith('/') is False)
def handle_expense_input(message):
    try:
        amount, category = message.text.split(maxsplit=1)
        amount = float(amount)
        chat_id = message.chat.id

        if chat_id not in expenses:
            expenses[chat_id] = []

        expenses[chat_id].append({'amount': amount, 'category': category})
        bot.send_message(chat_id, f"✅ Додано: {amount} грн на '{category}'")
    except:
        bot.send_message(message.chat.id, "❌ Неправильний формат. Введи: сума категорія (наприклад: `100 транспорт`)")

@bot.message_handler(commands=['stats'])
def handle_stats(message):
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
        response += f"• {category}: {total} грн\n"
    bot.send_message(chat_id, response)

@bot.message_handler(commands=['balance'])
def handle_balance(message):
    chat_id = message.chat.id
    if chat_id not in expenses or not expenses[chat_id]:
        bot.send_message(chat_id, "💰 Баланс: 0 грн")
        return

    total = sum(item['amount'] for item in expenses[chat_id])
    bot.send_message(chat_id, f"💰 Загальні витрати: {total} грн")

bot.polling()
