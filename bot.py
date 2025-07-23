import telebot
from telebot import types
import os
from dotenv import load_dotenv
from datetime import datetime, time, timedelta
import json
from collections import defaultdict
import matplotlib.pyplot as plt
import threading
import time as time_module
import pytz

# === Завантаження токену ===
load_dotenv()
TOKEN = os.getenv("TOKEN")
bot = telebot.TeleBot(TOKEN)

# === Дані користувачів ===
expenses = defaultdict(list)
incomes = defaultdict(list)

user_temp_data = {}
user_categories = {}
subscriptions = {}
saving_goals = {}  # <--- цілі на накопичення
income_data = {}  # або завантажуй із JSON, якщо ти це вже робиш

# === Дефолтні категорії ===
default_categories = ['Їжа', 'Транспорт', 'Покупки', 'Інше']

# === Збереження та завантаження ===
def save_data():
    data = {
        "expenses": expenses,
        "goals": saving_goals,
        "incomes": incomes,
    }
    with open("expenses.json", "w") as f:
        json.dump(data, f, indent=2, default=str)

def load_data():
    global expenses, saving_goals, incomes
    if os.path.exists("expenses.json"):
        with open("expenses.json", "r") as f:
            data = json.load(f)
            for chat_id, items in data.get("expenses", {}).items():
                expenses[int(chat_id)] = [
                    {"amount": float(i['amount']), "category": i['category'], "date": i['date']} for i in items
                ]
            saving_goals = {int(k): float(v) for k, v in data.get("goals", {}).items()}
            for chat_id, items in data.get("incomes", {}).items():
                incomes[int(chat_id)] = [
                    {"amount": float(i['amount']), "date": i['date']} for i in items
                ]


# === Меню ===
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


def send_welcome(message):
    show_main_menu(message.chat.id)
    bot.send_message(
        message.chat.id,
        "👋 Привіт! Я бот для обліку витрат. Обери дію нижче або введи вручну."
    )

@bot.message_handler(commands=['start'])
def start_handler(message):
    send_welcome(message)

# === Команди /goal ===
@bot.message_handler(commands=['goal'])
def handle_goal_command(message):
    chat_id = message.chat.id
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

    # Якщо просто /goal
    if chat_id in saving_goals:
        goal = saving_goals[chat_id]
        spent = sum(e['amount'] for e in expenses.get(chat_id, []))
        percent = min(100, spent / goal * 100)
        left = max(0, goal - spent)
        bot.send_message(chat_id, f"🎯 Ваша ціль: {goal:.2f} грн\n💸 Витрачено: {spent:.2f} грн\n📊 Прогрес: {percent:.1f}%\n🔒 Залишилось: {left:.2f} грн\n\nВикористай:\n/goal edit — змінити\n/goal delete — видалити")
    else:
        bot.send_message(chat_id, "🎯 У вас немає встановленої цілі. Введіть /goal set або /goal 10000 щоб встановити.")



# === Обробка введеної цілі ===
@bot.message_handler(func=lambda m: user_temp_data.get(m.chat.id, {}).get('step') == 'set_goal')
def save_goal_amount(message):
    chat_id = message.chat.id
    try:
        goal = float(message.text)
        saving_goals[chat_id] = goal
        save_data()
        bot.send_message(chat_id, f"✅ Ціль встановлено: {goal:.2f} грн")
    except:
        bot.send_message(chat_id, "❌ Введіть число.")
    user_temp_data.pop(chat_id, None)

# === Моя ціль (кнопка) ===
@bot.message_handler(func=lambda m: m.text == 'Моя ціль')
def show_goal_info(message):
    chat_id = message.chat.id
    goal = saving_goals.get(chat_id)
    total_spent = sum(e['amount'] for e in expenses.get(chat_id, []))
    if goal:
        percent = min(100, total_spent / goal * 100)
        remaining = max(0, goal - total_spent)
        text = (
            f"🎯 Ваша ціль: {goal:.2f} грн\n"
            f"💸 Витрачено: {total_spent:.2f} грн\n"
            f"📊 Прогрес: {percent:.1f}%\n"
            f"🔒 Залишилось: {remaining:.2f} грн"
        )
    else:
        text = "⚠️ У вас немає встановленої цілі. Введіть /goal set щоб створити."
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Редагувати ціль", "Видалити ціль", "↩️ Назад")
    bot.send_message(chat_id, text, reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "Редагувати ціль")
def edit_goal_from_menu(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "📝 Введи нову суму для цілі (наприклад, 15000):")
    user_temp_data[chat_id] = {'step': 'set_goal'}

@bot.message_handler(func=lambda m: m.text == "Видалити ціль")
def delete_goal_from_menu(message):
    chat_id = message.chat.id
    if chat_id in saving_goals:
        saving_goals.pop(chat_id)
        save_data()
        bot.send_message(chat_id, "🗑️ Ціль успішно видалено.")
    else:
        bot.send_message(chat_id, "⚠️ У вас немає встановленої цілі.")

# === Нагадування (з Київським часом) ===

kyiv_tz = pytz.timezone("Europe/Kyiv")

def reminder_loop():
    while True:
        now_kyiv = datetime.now(kyiv_tz)
        for chat_id, remind_time_str in subscriptions.items():
            try:
                remind_time = datetime.strptime(remind_time_str, "%H:%M").time()
            except:
                continue
            if now_kyiv.time().hour == remind_time.hour and now_kyiv.time().minute == remind_time.minute:
                try:
                    bot.send_message(chat_id, "🔔 Не забудь внести витрати!")
                except Exception as e:
                    print(f"Помилка відправки нагадування {chat_id}: {e}")
        time_module.sleep(60)

threading.Thread(target=reminder_loop, daemon=True).start()

@bot.message_handler(commands=['remind'])
def handle_remind(message):
    chat_id = message.chat.id
    args = message.text.split()
    if len(args) == 1:
        bot.send_message(chat_id, "ℹ️ Використання:\n/remind on - увімкнути нагадування о 20:00 (Київ)\n/remind off - вимкнути\n/remind HH:MM - встановити час нагадування")
        return
    param = args[1].lower()

    if param == "on":
        subscriptions[chat_id] = "20:00"
        bot.send_message(chat_id, "✅ Нагадування увімкнено на 20:00 (за Києвом).")
    elif param == "off":
        if chat_id in subscriptions:
            subscriptions.pop(chat_id)
            bot.send_message(chat_id, "✅ Нагадування вимкнено.")
        else:
            bot.send_message(chat_id, "ℹ️ Нагадування не було увімкнено.")
    else:
        try:
            dt = datetime.strptime(param, "%H:%M")
            subscriptions[chat_id] = param
            bot.send_message(chat_id, f"✅ Нагадування встановлено на {param} (Київ).")
        except:
            bot.send_message(chat_id, "❌ Невірний формат. Використай HH:MM (24-годинний формат).")

# === Додати витрату ===
@bot.message_handler(func=lambda m: m.text == 'Додати')
def handle_add(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("↩️ Назад")
    bot.send_message(message.chat.id, "💵 Введи суму витрати або скасуй:", reply_markup=markup)
    user_temp_data[message.chat.id] = {'step': 'awaiting_amount'}

@bot.message_handler(func=lambda m: user_temp_data.get(m.chat.id, {}).get('step') == 'awaiting_amount')
def handle_amount(message):
    if message.text == "↩️ Назад":
        user_temp_data.pop(message.chat.id, None)
        show_main_menu(message.chat.id)
        return
    try:
        amount = float(message.text)
        user_temp_data[message.chat.id] = {'step': 'awaiting_category', 'amount': amount}
        cats = user_categories.get(message.chat.id, default_categories)
        markup = types.InlineKeyboardMarkup()
        for c in cats:
            markup.add(types.InlineKeyboardButton(c, callback_data=f'category:{c}'))
        markup.add(types.InlineKeyboardButton("↩️ Назад", callback_data='cancel_add'))
        bot.send_message(message.chat.id, "📂 Вибери категорію:", reply_markup=markup)
    except:
        bot.send_message(message.chat.id, "❌ Введи суму числом.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('category:') or call.data == 'cancel_add')
def handle_category_or_cancel(call):
    chat_id = call.message.chat.id
    if call.data == 'cancel_add':
        user_temp_data.pop(chat_id, None)
        bot.edit_message_text("❌ Додавання витрати скасовано.", chat_id, call.message.message_id)
        show_main_menu(chat_id)
        bot.answer_callback_query(call.id)
        return

    cat = call.data.split(':')[1]
    data = user_temp_data.pop(chat_id, {})
    amount = data.get('amount')
    if amount is None:
        bot.send_message(chat_id, "⚠️ Помилка. Спробуй ще раз.")
        return
    expenses[chat_id].append({"amount": amount, "category": cat, "date": datetime.now().isoformat()})
    save_data()
    bot.edit_message_text(f"✅ Додано: {amount:.2f} грн на \"{cat}\"", chat_id, call.message.message_id)
    bot.answer_callback_query(call.id)

# === Додавання доходу ===

@bot.message_handler(commands=['income'])
def income_start(message):
    chat_id = message.chat.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("↩️ Назад")
    bot.send_message(chat_id, "💵 Введи суму доходу або скасуй:", reply_markup=markup)
    user_temp_data[chat_id] = {'step': 'awaiting_income_amount'}


@bot.message_handler(func=lambda m: user_temp_data.get(m.chat.id, {}).get('step') == 'awaiting_income_amount')
def income_amount_handler(message):
    chat_id = str(message.chat.id)
    if message.text == "↩️ Назад":
        user_temp_data.pop(message.chat.id, None)
        show_main_menu(message.chat.id)
        return
    try:
        amount = float(message.text)
        if chat_id not in income_data:
            income_data[chat_id] = []
        income_data[chat_id].append({
            "amount": amount,
            "date": datetime.now().isoformat()
        })
        save_data()
        bot.send_message(message.chat.id, f"✅ Дохід {amount:.2f} грн додано.")
        user_temp_data.pop(message.chat.id, None)
        show_main_menu(message.chat.id)
    except ValueError:
        bot.send_message(message.chat.id, "❌ Введи число.")


@bot.message_handler(func=lambda m: m.text == "Дохід")
def income_button_handler(message):
    chat_id = message.chat.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("↩️ Назад")
    bot.send_message(chat_id, "💵 Введи суму доходу або натисни «Назад»:", reply_markup=markup)
    user_temp_data[chat_id] = {'step': 'awaiting_income_amount'}



# === Статистика ===
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

# === Баланс ===
@bot.message_handler(func=lambda m: m.text == 'Баланс')
def balance(message):
    chat_id = message.chat.id
    total_expenses = sum(e['amount'] for e in expenses.get(chat_id, []))
    total_incomes = sum(i['amount'] for i in incomes.get(chat_id, []))
    net_balance = total_incomes - total_expenses
    bot.send_message(chat_id,
        f"💰 Загальні доходи: {total_incomes:.2f} грн\n"
        f"💸 Загальні витрати: {total_expenses:.2f} грн\n"
        f"⚖️ Чистий баланс: {net_balance:.2f} грн"
    )



# === Категорії ===
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
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("↩️ Назад")
    bot.send_message(message.chat.id, "✏️ Введи нову категорію або скасуй:", reply_markup=markup)
    user_temp_data[message.chat.id] = {'step': 'new_category'}

@bot.message_handler(func=lambda m: user_temp_data.get(m.chat.id, {}).get('step') == 'new_category')
def save_new_cat(message):
    if message.text == "↩️ Назад":
        user_temp_data.pop(message.chat.id, None)
        show_main_menu(message.chat.id)
        return
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
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for c in cats:
        markup.add(c)
    markup.add("↩️ Назад")
    bot.send_message(chat_id, "🗑️ Вибери категорію для видалення або скасуй:", reply_markup=markup)
    user_temp_data[chat_id] = {'step': 'delete_category'}

@bot.message_handler(func=lambda m: user_temp_data.get(m.chat.id, {}).get('step') == 'delete_category')
def delete_cat(message):
    if message.text == "↩️ Назад":
        user_temp_data.pop(message.chat.id, None)
        show_main_menu(message.chat.id)
        return
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


def show_categories(chat_id):
    markup = types.InlineKeyboardMarkup()
    for cat in categories:
        markup.add(types.InlineKeyboardButton(text=cat, callback_data=f"category_{cat}"))
    markup.add(types.InlineKeyboardButton(text="➕ Додати дохід", callback_data="add_income"))
    bot.send_message(chat_id, "Вибери категорію витрат або додай дохід:", reply_markup=markup)


@bot.message_handler(func=lambda m: m.text == "↩️ Назад")
def go_back(message):
    user_temp_data.pop(message.chat.id, None)
    show_main_menu(message.chat.id)


# === Видалити останню витрату ===
@bot.message_handler(func=lambda m: m.text == 'Видалити останню')
def delete_last(message):
    chat_id = message.chat.id
    if expenses.get(chat_id):
        last = expenses[chat_id].pop()
        save_data()
        bot.send_message(chat_id, f"❌ Видалено: {last['amount']} грн на {last['category']}")
    else:
        bot.send_message(chat_id, "⚠️ Немає витрат для видалення")

# === Мої витрати ===
@bot.message_handler(func=lambda m: m.text == 'Мої витрати')
def show_expense_history(message):
    chat_id = message.chat.id
    user_expenses = expenses.get(chat_id, [])

    if not user_expenses:
        bot.send_message(chat_id, "📭 У вас поки немає витрат.")
        return

    last_5 = user_expenses[-5:]
    start_idx = len(user_expenses) - len(last_5)

    for i, exp in enumerate(last_5, start=start_idx):
        text = f"{i+1}. 💸 {exp['amount']} грн — {exp['category']}\n🕓 {exp['date'][:16]}"
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✏️ Редагувати", callback_data=f"edit:{i}"),
            types.InlineKeyboardButton("🗑 Видалити", callback_data=f"delete:{i}")
        )
        bot.send_message(chat_id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith(('edit:', 'delete:')))
def handle_edit_or_delete(call):
    chat_id = call.message.chat.id
    data = call.data
    action, idx_str = data.split(":")
    idx = int(idx_str)

    if chat_id not in expenses:
        bot.answer_callback_query(call.id, "❌ Помилка: не знайдено.")
        return

    try:
        exp = expenses[chat_id][idx]
    except IndexError:
        bot.answer_callback_query(call.id, "⚠️ Витрату не знайдено.")
        return

    if action == "delete":
        deleted = expenses[chat_id].pop(idx)
        save_data()
        bot.edit_message_text(
            f"🗑️ Видалено: {deleted['amount']} грн — {deleted['category']}",
            chat_id, call.message.message_id
        )
        bot.answer_callback_query(call.id, "Витрату видалено")

    elif action == "edit":
        user_temp_data[chat_id] = {'step': 'edit_amount', 'idx': idx}
        bot.send_message(chat_id, f"✏️ Введи нову суму для {exp['category']} (було {exp['amount']} грн):")
        bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda m: user_temp_data.get(m.chat.id, {}).get('step') == 'edit_amount')
def update_expense_amount(message):
    chat_id = message.chat.id
    try:
        new_amount = float(message.text)
        idx = user_temp_data[chat_id]['idx']
        expenses[chat_id][idx]['amount'] = new_amount
        save_data()
        bot.send_message(chat_id, f"✅ Суму оновлено: {new_amount:.2f} грн")
    except ValueError:
        bot.send_message(chat_id, "❌ Введи число.")
    finally:
        user_temp_data.pop(chat_id, None)




# === Запуск бота ===
print("🤖 Бот запущено")
bot.polling(none_stop=True)