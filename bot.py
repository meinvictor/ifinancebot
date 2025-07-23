import telebot
import json
import os
from telebot import types
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import pytz

load_dotenv()
TOKEN = os.getenv("TOKEN")
bot = telebot.TeleBot(TOKEN)

DATA_FILE = 'expenses.json'
expenses = {}

def load_expenses():
    global expenses
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            expenses = json.load(f)

def save_expenses():
    with open(DATA_FILE, 'w') as f:
        json.dump(expenses, f)

load_expenses()

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("➕ Додати витрату", "📊 Статистика", "💰 Баланс")
    markup.row("📋 Всі витрати", "✏️ Редагувати", "❌ Видалити")
    bot.send_message(message.chat.id, "Привіт! Це твій фінансовий помічник 💸", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "➕ Додати витрату")
def ask_amount(message):
    bot.send_message(message.chat.id, "Введи суму витрати:")
    bot.register_next_step_handler(message, get_amount)

def get_amount(message):
    try:
        amount = float(message.text)
        bot.send_message(message.chat.id, "Введи категорію (наприклад, їжа, транспорт, тощо):")
        bot.register_next_step_handler(message, get_category, amount)
    except ValueError:
        bot.send_message(message.chat.id, "Будь ласка, введи число.")
        ask_amount(message)

def get_category(message, amount):
    user_id = str(message.from_user.id)
    category = message.text
    entry = {
        "amount": amount,
        "category": category,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    expenses.setdefault(user_id, []).append(entry)
    save_expenses()
    bot.send_message(message.chat.id, f"✅ Витрату додано: {amount} грн на {category}.")

@bot.message_handler(func=lambda m: m.text == "📊 Статистика")
def stats(message):
    user_id = str(message.from_user.id)
    total = 0
    categories = {}
    for e in expenses.get(user_id, []):
        total += e['amount']
        categories[e['category']] = categories.get(e['category'], 0) + e['amount']

    if total == 0:
        bot.send_message(message.chat.id, "Немає витрат 😇")
        return

    stat_msg = f"📊 Статистика:\nЗагалом: {total:.2f} грн\n\n"
    for cat, amt in categories.items():
        stat_msg += f"- {cat}: {amt:.2f} грн\n"
    bot.send_message(message.chat.id, stat_msg)

@bot.message_handler(func=lambda m: m.text == "💰 Баланс")
def balance(message):
    user_id = str(message.from_user.id)
    total = sum(e["amount"] for e in expenses.get(user_id, []))
    bot.send_message(message.chat.id, f"💰 Загальні витрати: {total:.2f} грн")

@bot.message_handler(func=lambda m: m.text == "📋 Всі витрати")
def all_expenses(message):
    user_id = str(message.from_user.id)
    user_exp = expenses.get(user_id, [])
    if not user_exp:
        bot.send_message(message.chat.id, "У тебе ще немає витрат.")
        return
    msg = "📋 Твої витрати:\n"
    for i, e in enumerate(user_exp, 1):
        msg += f"{i}. {e['amount']} грн - {e['category']} ({e['timestamp']})\n"
    bot.send_message(message.chat.id, msg)

@bot.message_handler(func=lambda m: m.text == "✏️ Редагувати")
def edit_expense(message):
    user_id = str(message.from_user.id)
    user_exp = expenses.get(user_id, [])
    if not user_exp:
        bot.send_message(message.chat.id, "Немає витрат для редагування.")
        return
    msg = "Вибери номер витрати для редагування:\n"
    for i, e in enumerate(user_exp, 1):
        msg += f"{i}. {e['amount']} грн - {e['category']}\n"
    bot.send_message(message.chat.id, msg)
    bot.register_next_step_handler(message, get_edit_index)

def get_edit_index(message):
    try:
        idx = int(message.text) - 1
        user_id = str(message.from_user.id)
        if 0 <= idx < len(expenses[user_id]):
            bot.send_message(message.chat.id, "Введи нову суму:")
            bot.register_next_step_handler(message, get_new_amount, idx)
        else:
            bot.send_message(message.chat.id, "Невірний номер.")
    except:
        bot.send_message(message.chat.id, "Введи номер витрати.")

def get_new_amount(message, idx):
    try:
        amount = float(message.text)
        bot.send_message(message.chat.id, "Введи нову категорію:")
        bot.register_next_step_handler(message, apply_edit, idx, amount)
    except:
        bot.send_message(message.chat.id, "Введи число.")

def apply_edit(message, idx, amount):
    user_id = str(message.from_user.id)
    expenses[user_id][idx]["amount"] = amount
    expenses[user_id][idx]["category"] = message.text
    save_expenses()
    bot.send_message(message.chat.id, "✅ Витрату оновлено.")

@bot.message_handler(func=lambda m: m.text == "❌ Видалити")
def delete_expense(message):
    user_id = str(message.from_user.id)
    user_exp = expenses.get(user_id, [])
    if not user_exp:
        bot.send_message(message.chat.id, "Немає витрат для видалення.")
        return
    msg = "Вибери номер витрати для видалення:\n"
    for i, e in enumerate(user_exp, 1):
        msg += f"{i}. {e['amount']} грн - {e['category']}\n"
    bot.send_message(message.chat.id, msg)
    bot.register_next_step_handler(message, get_delete_index)

def get_delete_index(message):
    try:
        idx = int(message.text) - 1
        user_id = str(message.from_user.id)
        if 0 <= idx < len(expenses[user_id]):
            deleted = expenses[user_id].pop(idx)
            save_expenses()
            bot.send_message(message.chat.id, f"❌ Видалено: {deleted['amount']} грн - {deleted['category']}")
        else:
            bot.send_message(message.chat.id, "Невірний номер.")
    except:
        bot.send_message(message.chat.id, "Введи номер.")

def send_daily_reminders():
    for user_id in expenses:
        bot.send_message(user_id, "🔔 Не забудь записати свої витрати сьогодні!")

scheduler = BackgroundScheduler(timezone=pytz.timezone("Europe/Kyiv"))
scheduler.add_job(send_daily_reminders, CronTrigger(hour=20, minute=0))
scheduler.start()

print("Бот запущено...")
bot.infinity_polling()
