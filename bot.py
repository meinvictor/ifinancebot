import telebot
import sqlite3
from datetime import datetime
import os
from telebot import types

TOKEN = os.getenv('TOKEN')
bot = telebot.TeleBot(TOKEN)

conn = sqlite3.connect('expenses.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount REAL,
        category TEXT,
        date TEXT
    )
''')
conn.commit()


@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_add = types.KeyboardButton('Додати')
    btn_stats = types.KeyboardButton('Статистика')
    btn_balance = types.KeyboardButton('Баланс')
    markup.row(btn_add)
    markup.row(btn_stats, btn_balance)

    bot.send_message(message.chat.id,
                     "👋 Привіт! Я бот для обліку витрат.\nОберіть команду кнопкою або введіть її вручну.",
                     reply_markup=markup)


@bot.message_handler(commands=['add'])
def add_expense(message):
    try:
        _, amount, *category = message.text.split()
        amount = float(amount)
        category = ' '.join(category)
        date = datetime.now().strftime("%Y-%m-%d")
        user_id = message.from_user.id
        cursor.execute("INSERT INTO expenses (user_id, amount, category, date) VALUES (?, ?, ?, ?)",
                       (user_id, amount, category, date))
        conn.commit()
        bot.send_message(message.chat.id, f"✅ Додано {amount} грн у категорію '{category}'")
    except:
        bot.send_message(message.chat.id, "⚠️ Приклад: /add 150 Продукти")

@bot.message_handler(commands=['balance'])
def balance(message):
    user_id = message.from_user.id
    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("SELECT SUM(amount) FROM expenses WHERE user_id = ? AND date = ?", (user_id, today))
    total = cursor.fetchone()[0]
    total = total if total else 0
    bot.send_message(message.chat.id, f"💰 Сьогодні ти витратив: {total:.2f} грн")

@bot.message_handler(commands=['stats'])
def stats(message):
    user_id = message.from_user.id
    cursor.execute("SELECT category, SUM(amount) FROM expenses WHERE user_id = ? GROUP BY category", (user_id,))
    data = cursor.fetchall()
    if not data:
        bot.send_message(message.chat.id, "🔍 Ще немає статистики.")
        return
    text = "📊 Твоя статистика витрат:\n"
    for category, total in data:
        text += f"— {category}: {total:.2f} грн\n"
    bot.send_message(message.chat.id, text)

bot.polling()
