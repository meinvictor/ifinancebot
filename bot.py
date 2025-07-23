import os
import json
import telebot
from dotenv import load_dotenv
from telebot import types

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = telebot.TeleBot(BOT_TOKEN)

DATA_FILE = "expenses.json"
GOAL_FILE = "goals.json"
INCOME_FILE = "income.json"

expenses = {}
saving_goals = {}
income_data = {}
user_temp_data = {}

categories = ["🍔 Їжа", "🚕 Транспорт", "🏠 Комуналка", "🎉 Розваги", "🛍 Інше"]

# Збереження даних
def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(expenses, f, indent=2)
    with open(GOAL_FILE, "w") as f:
        json.dump(saving_goals, f, indent=2)
    with open(INCOME_FILE, "w") as f:
        json.dump(income_data, f, indent=2)

# Завантаження даних
def load_data():
    global expenses, saving_goals, income_data
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            expenses = json.load(f)
    if os.path.exists(GOAL_FILE):
        with open(GOAL_FILE, "r") as f:
            saving_goals = json.load(f)
    if os.path.exists(INCOME_FILE):
        with open(INCOME_FILE, "r") as f:
            income_data = json.load(f)

load_data()

# Старт
@bot.message_handler(commands=['start'])
def start_handler(message):
    bot.send_message(message.chat.id, "👋 Привіт! Я бот для обліку витрат. Введи суму або натисни категорію.")
    show_categories(message.chat.id)

# Кнопки категорій
def show_categories(chat_id):
    markup = types.InlineKeyboardMarkup()
    for cat in categories:
        markup.add(types.InlineKeyboardButton(text=cat, callback_data=f"category_{cat}"))
    bot.send_message(chat_id, "Вибери категорію витрат:", reply_markup=markup)

# Обробка витрат через кнопки
@bot.callback_query_handler(func=lambda call: call.data.startswith("category_"))
def handle_category(call):
    chat_id = str(call.message.chat.id)
    category = call.data.split("_", 1)[1]
    user_temp_data[chat_id] = {'step': 'add_expense', 'category': category}
    bot.send_message(call.message.chat.id, f"Введи суму для категорії {category}:")

# Обробка текстових повідомлень
@bot.message_handler(func=lambda m: True)
def handle_message(message):
    chat_id = str(message.chat.id)
    if chat_id not in user_temp_data:
        bot.send_message(message.chat.id, "Введи суму або натисни кнопку категорії.")
        return

    step = user_temp_data[chat_id]['step']

    if step == 'add_expense':
        try:
            amount = float(message.text)
            category = user_temp_data[chat_id]['category']
            if chat_id not in expenses:
                expenses[chat_id] = []
            expenses[chat_id].append({"amount": amount, "category": category})
            save_data()
            bot.send_message(message.chat.id, f"✅ Додано {amount:.2f} грн до {category}")
        except:
            bot.send_message(message.chat.id, "❌ Введи число, наприклад: 50")
        user_temp_data.pop(chat_id)

    elif step == 'set_goal':
        try:
            goal = float(message.text)
            saving_goals[chat_id] = goal
            save_data()
            bot.send_message(message.chat.id, f"🎯 Ціль встановлено: {goal:.2f} грн")
        except:
            bot.send_message(message.chat.id, "❌ Введи число для цілі")
        user_temp_data.pop(chat_id)

    elif step == 'add_income':
        try:
            amount = float(message.text)
            if chat_id not in income_data:
                income_data[chat_id] = []
            income_data[chat_id].append(amount)
            save_data()
            bot.send_message(message.chat.id, f"✅ Доходу додано: {amount:.2f} грн")
        except:
            bot.send_message(message.chat.id, "❌ Введи число, наприклад: 10000")
        user_temp_data.pop(chat_id)

# Команда для додавання доходу
@bot.message_handler(commands=['income'])
def income_handler(message):
    chat_id = str(message.chat.id)
    bot.send_message(chat_id, "💰 Введи суму доходу (наприклад, 15000):")
    user_temp_data[chat_id] = {'step': 'add_income'}

# Команда для встановлення цілі
@bot.message_handler(commands=['goal'])
def goal_handler(message):
    chat_id = str(message.chat.id)
    goal = saving_goals.get(chat_id)
    if goal:
        bot.send_message(message.chat.id, f"🎯 Ваша ціль: {goal:.2f} грн")
    else:
        bot.send_message(message.chat.id, "🎯 У вас немає встановленої цілі. Введіть /goal_set щоб встановити.")

@bot.message_handler(commands=['goal_set'])
def goal_set_handler(message):
    chat_id = str(message.chat.id)
    bot.send_message(chat_id, "Введи суму цілі (наприклад, 10000):")
    user_temp_data[chat_id] = {'step': 'set_goal'}

# Баланс / статистика
@bot.message_handler(commands=['balance', 'stats'])
def balance_handler(message):
    chat_id = str(message.chat.id)
    income = sum(income_data.get(chat_id, []))
    spent = sum(entry['amount'] for entry in expenses.get(chat_id, []))
    goal = saving_goals.get(chat_id)

    text = f"💼 Доходи: {income:.2f} грн\n💸 Витрати: {spent:.2f} грн\n"
    text += f"📈 Баланс: {income - spent:.2f} грн\n"

    if goal:
        left = goal - (income - spent)
        text += f"🎯 Ціль: {goal:.2f} грн → Залишилось: {max(left, 0):.2f} грн"

    bot.send_message(chat_id, text)

bot.polling()
