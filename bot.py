import telebot
import json
import os
from datetime import datetime
from telebot import types
from dotenv import load_dotenv


# === Завантаження токену ===
load_dotenv()
TOKEN = os.getenv("TOKEN")
bot = telebot.TeleBot(TOKEN)

expenses = {}
saving_goals = {}
income_data = {}
user_temp_data = {}

DATA_FILE = "expenses.json"
GOAL_FILE = "goals.json"
INCOME_FILE = "income.json"

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(expenses, f, indent=2)
    with open(GOAL_FILE, "w") as f:
        json.dump(saving_goals, f, indent=2)
    with open(INCOME_FILE, "w") as f:
        json.dump(income_data, f, indent=2)

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

@bot.message_handler(commands=['start'])
def start_handler(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Моя ціль"))
    bot.send_message(message.chat.id, "👋 Привіт! Я бот для обліку витрат.\n\nНапиши суму (наприклад, 200), щоб додати витрату.\n\nКоманди:\n/stats — статистика\n/goal — ціль накопичення\n/income — додати дохід\n/balance — загальний баланс", reply_markup=markup)

@bot.message_handler(commands=['stats'])
def stats_handler(message):
    chat_id = str(message.chat.id)
    if chat_id not in expenses or not expenses[chat_id]:
        bot.send_message(chat_id, "У вас поки немає витрат.")
        return
    total = sum(entry['amount'] for entry in expenses[chat_id])
    text = f"📊 Загальні витрати: {total:.2f} грн\n\nОстанні:\n"
    for entry in expenses[chat_id][-5:]:
        text += f"- {entry['amount']} грн ({entry['date']})\n"
    bot.send_message(chat_id, text)

@bot.message_handler(commands=['goal'])
def handle_goal_command(message):
    chat_id = str(message.chat.id)
    args = message.text.strip().split()

    if len(args) == 2:
        cmd = args[1].lower()

        if cmd == 'set' or cmd == 'edit':
            bot.send_message(chat_id, "📝 Введи суму для цілі (наприклад, 10000):")
            user_temp_data[chat_id] = {'step': 'set_goal'}
            return

        elif cmd == 'delete':
            if chat_id in saving_goals:
                saving_goals.pop(chat_id)
                save_data()
                bot.send_message(chat_id, "🗑️ Ціль видалено.")
            else:
                bot.send_message(chat_id, "⚠️ У вас немає встановленої цілі.")
            return

        else:
            try:
                goal = float(cmd)
                saving_goals[chat_id] = goal
                save_data()
                bot.send_message(chat_id, f"✅ Ціль встановлено: {goal:.2f} грн")
                return
            except:
                bot.send_message(chat_id, "❌ Невірний формат. Напишіть /goal 10000 або /goal set")
                return
    else:
        goal = saving_goals.get(chat_id)
        if goal:
            income = sum(income_data.get(chat_id, []))
            spent = sum(entry['amount'] for entry in expenses.get(chat_id, []))
            left = goal - (income - spent)
            bot.send_message(chat_id, f"🎯 Ваша ціль: {goal:.2f} грн\nЗалишилось: {max(left, 0):.2f} грн")
        else:
            bot.send_message(chat_id, "🎯 У вас немає встановленої цілі. Введіть /goal set щоб встановити.")

@bot.message_handler(commands=['income'])
def income_handler(message):
    chat_id = str(message.chat.id)
    bot.send_message(chat_id, "💰 Введи суму доходу (наприклад, 15000):")
    user_temp_data[chat_id] = {'step': 'add_income'}

@bot.message_handler(commands=['balance'])
def balance_handler(message):
    chat_id = str(message.chat.id)
    income = sum(income_data.get(chat_id, []))
    spent = sum(entry['amount'] for entry in expenses.get(chat_id, []))
    goal = saving_goals.get(chat_id, None)

    text = f"💼 Доходи: {income:.2f} грн\n💸 Витрати: {spent:.2f} грн\n📈 Баланс: {income - spent:.2f} грн\n"
    if goal:
        left = goal - (income - spent)
        text += f"🎯 Ціль: {goal:.2f} грн → Залишилось: {max(left, 0):.2f} грн"
    bot.send_message(chat_id, text)

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = str(message.chat.id)

    if chat_id in user_temp_data:
        step = user_temp_data[chat_id]['step']

        if step == 'set_goal':
            try:
                goal = float(message.text)
                saving_goals[chat_id] = goal
                save_data()
                bot.send_message(chat_id, f"✅ Ціль встановлено: {goal:.2f} грн")
            except:
                bot.send_message(chat_id, "❌ Введи число, наприклад: 10000")
            user_temp_data.pop(chat_id)

        elif step == 'add_income':
            try:
                amount = float(message.text)
                if chat_id not in income_data:
                    income_data[chat_id] = []
                income_data[chat_id].append(amount)
                save_data()
                bot.send_message(chat_id, f"✅ Дохід додано: {amount:.2f} грн")
            except:
                bot.send_message(chat_id, "❌ Введи число, наприклад: 10000")
            user_temp_data.pop(chat_id)

    elif message.text.lower() == "моя ціль":
        goal = saving_goals.get(chat_id)
        if goal:
            income = sum(income_data.get(chat_id, []))
            spent = sum(entry['amount'] for entry in expenses.get(chat_id, []))
            left = goal - (income - spent)
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("Редагувати", callback_data="edit_goal"))
            markup.add(types.InlineKeyboardButton("Видалити", callback_data="delete_goal"))
            bot.send_message(chat_id, f"🎯 Ваша ціль: {goal:.2f} грн\nЗалишилось: {max(left, 0):.2f} грн", reply_markup=markup)
        else:
            bot.send_message(chat_id, "🎯 У вас немає встановленої цілі. Введіть /goal set щоб встановити.")

    else:
        try:
            amount = float(message.text)
            if chat_id not in expenses:
                expenses[chat_id] = []
            expenses[chat_id].append({"amount": amount, "date": datetime.now().strftime("%Y-%m-%d")})
            save_data()
            bot.send_message(chat_id, f"✅ Додано витрату: {amount:.2f} грн")
        except:
            bot.send_message(chat_id, "❌ Введи число, наприклад: 200")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = str(call.message.chat.id)
    if call.data == "edit_goal":
        bot.send_message(chat_id, "📝 Введи нову суму для цілі:")
        user_temp_data[chat_id] = {'step': 'set_goal'}
    elif call.data == "delete_goal":
        if chat_id in saving_goals:
            saving_goals.pop(chat_id)
            save_data()
            bot.send_message(chat_id, "🗑️ Ціль видалено.")
        else:
            bot.send_message(chat_id, "⚠️ У вас немає встановленої цілі.")

bot.polling(none_stop=True)
