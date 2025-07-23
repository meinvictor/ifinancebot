import telebot
from telebot import types
from datetime import datetime
import json
from collections import defaultdict
from dotenv import load_dotenv
import os

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = telebot.TeleBot(BOT_TOKEN)

expenses = defaultdict(list)
incomes = defaultdict(list)
user_temp_data = {}
categories = ["🍔 Їжа", "🚗 Транспорт", "🏠 Житло", "🎉 Розваги", "🛍️ Покупки"]
saving_goals = {}

def save_data():
    with open("expenses.json", "w") as f:
        json.dump(expenses, f)
    with open("incomes.json", "w") as f:
        json.dump(incomes, f)
    with open("goals.json", "w") as f:
        json.dump(saving_goals, f)

def load_data():
    global expenses, incomes, saving_goals
    try:
        with open("expenses.json") as f:
            expenses = defaultdict(list, json.load(f))
        with open("incomes.json") as f:
            incomes = defaultdict(list, json.load(f))
        with open("goals.json") as f:
            saving_goals = json.load(f)
    except FileNotFoundError:
        pass

@bot.message_handler(commands=['start'])
def start(message):
    load_data()
    show_main_menu(message.chat.id)


def show_main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        types.KeyboardButton('Розхід'),
        types.KeyboardButton('Дохід'),
        types.KeyboardButton('Баланс'),
        types.KeyboardButton('Статистика'),
        types.KeyboardButton('Категорії'),
        types.KeyboardButton('Мої витрати'),
        types.KeyboardButton('Моя ціль'),
        types.KeyboardButton('Видалити останню')
    )
    bot.send_message(chat_id, "Оберіть дію:", reply_markup=markup)


@bot.message_handler(func=lambda message: message.text == "Розхід")
def start_expense(message):
    chat_id = message.chat.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for cat in categories:
        markup.add(types.KeyboardButton(cat))
    markup.add(types.KeyboardButton("↩️ Назад"))
    bot.send_message(chat_id, "Оберіть категорію:", reply_markup=markup)
    user_temp_data[chat_id] = {'step': 'awaiting_expense_category'}

@bot.message_handler(func=lambda m: user_temp_data.get(m.chat.id, {}).get('step') == 'awaiting_expense_category')
def category_chosen(message):
    chat_id = message.chat.id
    category = message.text
    if category == "↩️ Назад":
        user_temp_data.pop(chat_id, None)
        show_main_menu(chat_id)
        return
    if category not in categories:
        bot.send_message(chat_id, "❌ Невірна категорія.")
        return
    user_temp_data[chat_id] = {'step': 'awaiting_expense_amount', 'category': category}
    bot.send_message(chat_id, f"Введи суму витрати для категорії {category}:")

@bot.message_handler(func=lambda m: user_temp_data.get(m.chat.id, {}).get('step') == 'awaiting_expense_amount')
def expense_amount(message):
    chat_id = message.chat.id
    try:
        amount = float(message.text)
        category = user_temp_data[chat_id]['category']
        expenses[chat_id].append({"amount": amount, "category": category, "date": datetime.now().isoformat()})
        save_data()
        bot.send_message(chat_id, f"✅ Додано витрату {amount:.2f} грн в категорію {category}")
        user_temp_data.pop(chat_id, None)
        show_main_menu(chat_id)
    except ValueError:
        bot.send_message(chat_id, "❌ Введи число.")

@bot.message_handler(func=lambda message: message.text == "Дохід")
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
        incomes[chat_id].append({"amount": amount, "date": datetime.now().isoformat()})
        save_data()
        bot.send_message(chat_id, f"✅ Додано дохід: {amount:.2f} грн")
        user_temp_data.pop(chat_id, None)
        show_main_menu(chat_id)
    except ValueError:
        bot.send_message(chat_id, "❌ Введи число.")

@bot.message_handler(func=lambda message: message.text == "Баланс")
def balance(message):
    chat_id = message.chat.id
    total_income = sum(i["amount"] for i in incomes.get(str(chat_id), []))
    total_expense = sum(e["amount"] for e in expenses.get(str(chat_id), []))
    bot.send_message(chat_id, f"📊 Баланс: {total_income - total_expense:.2f} грн\n\n💵 Дохід: {total_income:.2f} грн\n💸 Витрати: {total_expense:.2f} грн")

@bot.message_handler(func=lambda message: message.text == "Категорії")
def show_categories(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "Поточні категорії:")
    for cat in categories:
        bot.send_message(chat_id, cat)

@bot.message_handler(func=lambda message: message.text == "Мої витрати")
def show_expenses(message):
    chat_id = message.chat.id
    if not expenses.get(str(chat_id)):
        bot.send_message(chat_id, "Немає записаних витрат.")
        return
    msg = "Останні витрати:\n"
    for e in expenses[str(chat_id)][-5:]:
        msg += f"- {e['amount']} грн | {e['category']} | {e['date'][:10]}\n"
    bot.send_message(chat_id, msg)

@bot.message_handler(func=lambda message: message.text == "Видалити останню")
def delete_last(message):
    chat_id = str(message.chat.id)
    if expenses[chat_id]:
        removed = expenses[chat_id].pop()
        save_data()
        bot.send_message(chat_id, f"❌ Видалено: {removed['amount']} грн — {removed['category']}")
    else:
        bot.send_message(chat_id, "❌ Немає витрат для видалення.")

@bot.message_handler(func=lambda message: message.text == "Моя ціль")
def saving_goal(message):
    chat_id = str(message.chat.id)
    bot.send_message(chat_id, "Введи бажану суму накопичення:")
    user_temp_data[chat_id] = {'step': 'awaiting_goal'}

@bot.message_handler(func=lambda m: user_temp_data.get(str(m.chat.id), {}).get('step') == 'awaiting_goal')
def goal_input(message):
    chat_id = str(message.chat.id)
    try:
        goal = float(message.text)
        saving_goals[chat_id] = goal
        save_data()
        user_temp_data.pop(chat_id, None)
        bot.send_message(chat_id, f"🎯 Ціль встановлена: {goal:.2f} грн")
    except ValueError:
        bot.send_message(chat_id, "❌ Введи число.")

print("Бот запущено")
bot.polling(none_stop=True)
