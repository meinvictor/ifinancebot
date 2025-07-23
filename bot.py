import telebot
from telebot import types
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import json
from collections import defaultdict
import matplotlib.pyplot as plt

# === Завантаження токену ===
load_dotenv()
TOKEN = os.getenv("TOKEN")
bot = telebot.TeleBot(TOKEN)

# === Дані користувачів ===
expenses = defaultdict(list)
user_temp_data = {}
user_categories = {}
subscriptions = {}

# === Дефолтні категорії ===
default_categories = ['Їжа', 'Транспорт', 'Покупки', 'Інше']

# === Допоміжні функції ===
def save_data():
    with open("expenses.json", "w") as f:
        json.dump(expenses, f, indent=2, default=str)

def load_data():
    global expenses
    if os.path.exists("expenses.json"):
        with open("expenses.json", "r") as f:
            data = json.load(f)
            for chat_id, items in data.items():
                expenses[int(chat_id)] = [
                    {"amount": float(i['amount']), "category": i['category'], "date": i['date']} for i in items
                ]

load_data()

# === Команди ===
@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        types.KeyboardButton('Додати'),
        types.KeyboardButton('Статистика'),
        types.KeyboardButton('Баланс'),
        types.KeyboardButton('Категорії'),
        types.KeyboardButton('Видалити останню')
    )
    bot.send_message(
        message.chat.id,
        "👋 Привіт! Я бот для обліку витрат.\nОбери дію кнопкою нижче або введи вручну.",
        reply_markup=markup
    )

@bot.message_handler(commands=['today'])
def today_stats(message):
    chat_id = message.chat.id
    today = datetime.now().date()
    today_exp = [e for e in expenses.get(chat_id, []) if datetime.fromisoformat(e['date']).date() == today]

    if not today_exp:
        bot.send_message(chat_id, "📅 Сьогодні витрат не було.")
        return

    stats = defaultdict(float)
    for e in today_exp:
        stats[e['category']] += e['amount']

    text = "📅 Витрати за сьогодні:\n"
    for cat, total in stats.items():
        text += f"• {cat}: {total:.2f} грн\n"
    bot.send_message(chat_id, text)

@bot.message_handler(commands=['subscribe'])
def subscribe(message):
    subscriptions[message.chat.id] = True
    bot.send_message(message.chat.id, "✅ Ви підписалися на щоденну статистику.")

@bot.message_handler(commands=['unsubscribe'])
def unsubscribe(message):
    subscriptions.pop(message.chat.id, None)
    bot.send_message(message.chat.id, "❌ Ви відписалися від щоденної статистики.")

@bot.message_handler(func=lambda m: m.text == 'Додати')
def handle_add(message):
    bot.send_message(message.chat.id, "💵 Введи суму витрати:")
    user_temp_data[message.chat.id] = {'step': 'awaiting_amount'}

@bot.message_handler(func=lambda m: user_temp_data.get(m.chat.id, {}).get('step') == 'awaiting_amount')
def handle_amount(message):
    try:
        amount = float(message.text)
        user_temp_data[message.chat.id] = {'step': 'awaiting_category', 'amount': amount}
        cats = user_categories.get(message.chat.id, default_categories)
        markup = types.InlineKeyboardMarkup()
        for c in cats:
            markup.add(types.InlineKeyboardButton(c, callback_data=f'category:{c}'))
        bot.send_message(message.chat.id, "📂 Вибери категорію:", reply_markup=markup)
    except:
        bot.send_message(message.chat.id, "❌ Введи суму числом.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('category:'))
def handle_category(call):
    chat_id = call.message.chat.id
    cat = call.data.split(':')[1]
    data = user_temp_data.pop(chat_id, {})
    amount = data.get('amount')
    if amount is None:
        bot.send_message(chat_id, "⚠️ Помилка. Спробуй ще раз.")
        return
    expenses[chat_id].append({"amount": amount, "category": cat, "date": datetime.now().isoformat()})
    save_data()
    bot.send_message(chat_id, f"✅ Додано: {amount:.2f} грн на \"{cat}\"")

@bot.message_handler(func=lambda m: m.text == 'Статистика')
def stats(message):
    chat_id = message.chat.id
    if not expenses.get(chat_id):
        bot.send_message(chat_id, "📊 Статистика пуста.")
        return
    stat = defaultdict(float)
    for e in expenses[chat_id]:
        stat[e['category']] += e['amount']
    text = "📈 Статистика витрат:\n"
    for cat, total in stat.items():
        text += f"• {cat}: {total:.2f} грн\n"
    bot.send_message(chat_id, text)
    generate_pie_chart(stat, chat_id)

def generate_pie_chart(stat, chat_id):
    fig, ax = plt.subplots()
    ax.pie(stat.values(), labels=stat.keys(), autopct='%1.1f%%')
    ax.axis('equal')
    plt.title("Витрати по категоріях")
    path = f"chart_{chat_id}.png"
    plt.savefig(path)
    plt.close()
    with open(path, 'rb') as photo:
        bot.send_photo(chat_id, photo)
    os.remove(path)

@bot.message_handler(func=lambda m: m.text == 'Баланс')
def balance(message):
    chat_id = message.chat.id
    total = sum(e['amount'] for e in expenses.get(chat_id, []))
    bot.send_message(chat_id, f"💰 Загальні витрати: {total:.2f} грн")

@bot.message_handler(func=lambda m: m.text == 'Категорії')
def categories(message):
    chat_id = message.chat.id
    cats = user_categories.get(chat_id, default_categories)
    text = "📂 Категорії:\n" + '\n'.join(f"• {c}" for c in cats)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("➕ Додати категорію", "➖ Видалити категорію", "↩️ Назад")
    bot.send_message(chat_id, text, reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "➕ Додати категорію")
def add_cat(message):
    bot.send_message(message.chat.id, "✏️ Введи нову категорію:")
    user_temp_data[message.chat.id] = {'step': 'new_category'}

@bot.message_handler(func=lambda m: user_temp_data.get(m.chat.id, {}).get('step') == 'new_category')
def save_new_cat(message):
    cat = message.text.strip()
    chat_id = message.chat.id
    cats = user_categories.get(chat_id, default_categories.copy())
    if cat in cats:
        bot.send_message(chat_id, "⚠️ Категорія вже існує.")
    else:
        cats.append(cat)
        user_categories[chat_id] = cats
        bot.send_message(chat_id, f"✅ Додано категорію: {cat}")
    user_temp_data.pop(chat_id, None)

@bot.message_handler(func=lambda m: m.text == "➖ Видалити категорію")
def delete_cat_start(message):
    chat_id = message.chat.id
    cats = user_categories.get(chat_id, default_categories.copy())
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for c in cats:
        markup.add(c)
    bot.send_message(chat_id, "🗑️ Вибери категорію для видалення:", reply_markup=markup)
    user_temp_data[chat_id] = {'step': 'delete_category'}

@bot.message_handler(func=lambda m: user_temp_data.get(m.chat.id, {}).get('step') == 'delete_category')
def delete_cat(message):
    cat = message.text.strip()
    chat_id = message.chat.id
    cats = user_categories.get(chat_id, default_categories.copy())
    if cat in cats:
        cats.remove(cat)
        user_categories[chat_id] = cats
        bot.send_message(chat_id, f"🗑️ Категорію {cat} видалено")
    else:
        bot.send_message(chat_id, "⚠️ Категорію не знайдено")
    user_temp_data.pop(chat_id, None)

@bot.message_handler(func=lambda m: m.text == "↩️ Назад")
def go_back(message):
    send_welcome(message)

@bot.message_handler(func=lambda m: m.text == 'Видалити останню')
def delete_last(message):
    chat_id = message.chat.id
    if expenses.get(chat_id):
        last = expenses[chat_id].pop()
        save_data()
        bot.send_message(chat_id, f"❌ Видалено: {last['amount']} грн на {last['category']}")
    else:
        bot.send_message(chat_id, "⚠️ Немає витрат для видалення")

# Старт бота
print("🤖 Бот запущено")
bot.polling(none_stop=True)