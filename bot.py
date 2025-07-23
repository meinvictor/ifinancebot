import telebot
from telebot import types
from datetime import datetime
import json
import os
import matplotlib.pyplot as plt

TOKEN = os.getenv("TOKEN")
bot = telebot.TeleBot(TOKEN)

DATA_FILE = 'data.json'

expenses = {}
incomes = {}
user_temp_data = {}

def save_data():
    with open(DATA_FILE, 'w') as f:
        json.dump({'expenses': expenses, 'incomes': incomes}, f)

def load_data():
    global expenses, incomes
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            expenses = data.get('expenses', {})
            incomes = data.get('incomes', {})

load_data()

def show_main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        types.KeyboardButton('Дохід'),
        types.KeyboardButton('Розхід'),
        types.KeyboardButton('Статистика'),
        types.KeyboardButton('Баланс')
    )
    markup.add(
        types.KeyboardButton('Категорії'),
        types.KeyboardButton('Видалити останню'),
        types.KeyboardButton('Мої витрати'),
        types.KeyboardButton('Моя ціль')
    )
    bot.send_message(chat_id, "Оберіть дію:", reply_markup=markup)

@bot.message_handler(commands=['start'])
def start(message):
    chat_id = str(message.chat.id)
    expenses.setdefault(chat_id, [])
    incomes.setdefault(chat_id, [])
    show_main_menu(message.chat.id)

@bot.message_handler(func=lambda message: message.text == 'Дохід')
def income_start(message):
    chat_id = message.chat.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("↩️ Назад")
    bot.send_message(chat_id, "💵 Введи суму доходу або скасуй:", reply_markup=markup)
    user_temp_data[chat_id] = {'step': 'awaiting_income_amount'}

@bot.message_handler(func=lambda m: user_temp_data.get(m.chat.id, {}).get('step') == 'awaiting_income_amount')
def income_amount(message):
    chat_id = message.chat.id
    if message.text == "↩️ Назад":
        user_temp_data.pop(chat_id, None)
        show_main_menu(chat_id)
        return
    try:
        amount = float(message.text)
        incomes[str(chat_id)].append({"amount": amount, "date": datetime.now().isoformat()})
        save_data()
        bot.send_message(chat_id, f"✅ Додано дохід: {amount:.2f} грн")
        user_temp_data.pop(chat_id, None)
        show_main_menu(chat_id)
    except ValueError:
        bot.send_message(chat_id, "❌ Введи число.")

@bot.message_handler(func=lambda message: message.text == 'Розхід')
def expense_start(message):
    chat_id = message.chat.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("↩️ Назад")
    bot.send_message(chat_id, "💸 Введи суму витрати або скасуй:", reply_markup=markup)
    user_temp_data[chat_id] = {'step': 'awaiting_expense_amount'}

@bot.message_handler(func=lambda m: user_temp_data.get(m.chat.id, {}).get('step') == 'awaiting_expense_amount')
def expense_amount(message):
    chat_id = message.chat.id
    if message.text == "↩️ Назад":
        user_temp_data.pop(chat_id, None)
        show_main_menu(chat_id)
        return
    try:
        amount = float(message.text)
        expenses[str(chat_id)].append({"amount": amount, "date": datetime.now().isoformat()})
        save_data()
        bot.send_message(chat_id, f"✅ Додано витрату: {amount:.2f} грн")
        user_temp_data.pop(chat_id, None)
        show_main_menu(chat_id)
    except ValueError:
        bot.send_message(chat_id, "❌ Введи число.")

@bot.message_handler(func=lambda message: message.text == 'Баланс')
def show_balance(message):
    chat_id = str(message.chat.id)
    total_income = sum(i['amount'] for i in incomes.get(chat_id, []))
    total_expense = sum(e['amount'] for e in expenses.get(chat_id, []))
    balance = total_income - total_expense
    bot.send_message(message.chat.id, f"💰 Ваш баланс: {balance:.2f} грн")

@bot.message_handler(func=lambda message: message.text == 'Мої витрати')
def show_expenses(message):
    chat_id = str(message.chat.id)
    user_expenses = expenses.get(chat_id, [])[-10:]
    if not user_expenses:
        bot.send_message(message.chat.id, "У вас ще немає витрат.")
    else:
        msg = "Останні витрати:\n"
        for e in user_expenses:
            msg += f"{e['date'][:10]} — {e['amount']:.2f} грн\n"
        bot.send_message(message.chat.id, msg)

@bot.message_handler(func=lambda message: message.text == 'Статистика')
def show_statistics(message):
    chat_id = str(message.chat.id)
    user_expenses = expenses.get(chat_id, [])
    if not user_expenses:
        bot.send_message(message.chat.id, "Статистика недоступна. Немає витрат.")
        return

    dates = [e['date'][:10] for e in user_expenses]
    amounts = [e['amount'] for e in user_expenses]

    plt.figure(figsize=(8, 4))
    plt.plot(dates, amounts, marker='o')
    plt.title('Ваші витрати')
    plt.xlabel('Дата')
    plt.ylabel('Сума (грн)')
    plt.xticks(rotation=45)
    plt.tight_layout()
    filename = f"stat_{chat_id}.png"
    plt.savefig(filename)
    plt.close()

    with open(filename, 'rb') as photo:
        bot.send_photo(message.chat.id, photo, caption="📊 Графік витрат")

    os.remove(filename)

bot.polling(none_stop=True)