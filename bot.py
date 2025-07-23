import os
import json
from datetime import datetime
import telebot
from telebot import types
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

expenses = {}
incomes = {}
savings_goals = {}
user_temp_data = {}

DATA_FILE = 'data.json'

# ---------- ЗБЕРЕЖЕННЯ / ЗАВАНТАЖЕННЯ ----------
def save_data():
    with open(DATA_FILE, 'w') as f:
        json.dump({"expenses": expenses, "incomes": incomes, "savings_goals": savings_goals}, f)

def load_data():
    global expenses, incomes, savings_goals
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            data = json.load(f)
            expenses = data.get("expenses", {})
            incomes = data.get("incomes", {})
            savings_goals = data.get("savings_goals", {})

load_data()

# ---------- ГОЛОВНЕ МЕНЮ ----------
def show_main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        types.KeyboardButton('Дохід'),
        types.KeyboardButton('Розхід'),
        types.KeyboardButton('Статистика'),
        types.KeyboardButton('Баланс'),
        types.KeyboardButton('Категорії'),
        types.KeyboardButton('Видалити останню'),
        types.KeyboardButton('Мої витрати'),
        types.KeyboardButton('Моя ціль')
    )
    bot.send_message(chat_id, "Оберіть дію:", reply_markup=markup)

# ---------- СТАРТ ----------
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = str(message.chat.id)
    expenses.setdefault(chat_id, [])
    incomes.setdefault(chat_id, [])
    savings_goals.setdefault(chat_id, None)
    show_main_menu(chat_id)

# ---------- ДОХІД ----------
@bot.message_handler(func=lambda m: m.text == "Дохід")
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

# ---------- РОЗХІД ----------
@bot.message_handler(func=lambda m: m.text == "Розхід")
def expense_start(message):
    chat_id = message.chat.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("↩️ Назад")
    bot.send_message(chat_id, "💸 Введи суму витрати:", reply_markup=markup)
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

# ---------- СТАТИСТИКА ----------
@bot.message_handler(func=lambda m: m.text == "Статистика")
def show_stats(message):
    chat_id = str(message.chat.id)
    total_exp = sum(e['amount'] for e in expenses.get(chat_id, []))
    total_inc = sum(i['amount'] for i in incomes.get(chat_id, []))
    bot.send_message(message.chat.id, f"📊 Статистика:\nЗагальний дохід: {total_inc:.2f} грн\nЗагальні витрати: {total_exp:.2f} грн")

# ---------- БАЛАНС ----------
@bot.message_handler(func=lambda m: m.text == "Баланс")
def show_balance(message):
    chat_id = str(message.chat.id)
    total_exp = sum(e['amount'] for e in expenses.get(chat_id, []))
    total_inc = sum(i['amount'] for i in incomes.get(chat_id, []))
    balance = total_inc - total_exp
    bot.send_message(message.chat.id, f"💰 Баланс: {balance:.2f} грн")

# ---------- МОЇ ВИТРАТИ ----------
@bot.message_handler(func=lambda m: m.text == "Мої витрати")
def my_expenses(message):
    chat_id = str(message.chat.id)
    items = expenses.get(chat_id, [])[-5:]
    if not items:
        bot.send_message(message.chat.id, "ℹ️ Немає витрат")
    else:
        text = "🧾 Останні витрати:\n" + "\n".join([f"{e['amount']} грн - {e['date'][:10]}" for e in items])
        bot.send_message(message.chat.id, text)

# ---------- ЦІЛЬ ----------
@bot.message_handler(func=lambda m: m.text == "Моя ціль")
def goal_status(message):
    chat_id = str(message.chat.id)
    goal = savings_goals.get(chat_id)
    if goal:
        total_exp = sum(e['amount'] for e in expenses.get(chat_id, []))
        total_inc = sum(i['amount'] for i in incomes.get(chat_id, []))
        balance = total_inc - total_exp
        progress = min(balance / goal * 100, 100)
        bot.send_message(message.chat.id, f"🎯 Ваша ціль: {goal} грн\nПрогрес: {progress:.2f}%")
    else:
        bot.send_message(message.chat.id, "🎯 У вас немає встановленої цілі. Введіть /goal_set щоб встановити.")

@bot.message_handler(commands=['goal_set'])
def set_goal(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "🎯 Введіть суму вашої цілі:")
    user_temp_data[chat_id] = {'step': 'awaiting_goal_amount'}

@bot.message_handler(func=lambda m: user_temp_data.get(m.chat.id, {}).get('step') == 'awaiting_goal_amount')
def save_goal(message):
    chat_id = str(message.chat.id)
    try:
        goal = float(message.text)
        savings_goals[chat_id] = goal
        save_data()
        user_temp_data.pop(message.chat.id, None)
        bot.send_message(message.chat.id, f"🎯 Ціль встановлена: {goal:.2f} грн")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Введіть коректне число.")

# ---------- ВИДАЛИТИ ОСТАННЮ ВИТРАТУ ----------
@bot.message_handler(func=lambda m: m.text == "Видалити останню")
def delete_last(message):
    chat_id = str(message.chat.id)
    if expenses.get(chat_id):
        last = expenses[chat_id].pop()
        save_data()
        bot.send_message(message.chat.id, f"❌ Видалено: {last['amount']} грн")
    else:
        bot.send_message(message.chat.id, "ℹ️ Немає витрат для видалення.")

# ---------- КАТЕГОРІЇ (тимчасово заглушка) ----------
@bot.message_handler(func=lambda m: m.text == "Категорії")
def show_categories(message):
    bot.send_message(message.chat.id, "🔧 Категорії ще не реалізовані.")

# ---------- ОБРОБКА ВСЬОГО ІНШОГО ----------
@bot.message_handler(func=lambda m: True)
def fallback(message):
    bot.send_message(message.chat.id, "❓ Команду не розпізнано. Оберіть дію з меню.")

print("🤖 Бот запущено...")
bot.polling(none_stop=True)
