import sqlite3
from datetime import datetime, timedelta
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

API_TOKEN = "YOUR_API_TOKEN"
MASTER_ID = "master's username"

bot = telebot.TeleBot(API_TOKEN)

# Подключение к базе данных
conn = sqlite3.connect("lash_bot.db", check_same_thread=False)
cursor = conn.cursor()

# Создание таблиц
cursor.execute("""
CREATE TABLE IF NOT EXISTS services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    duration INTEGER NOT NULL
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    username TEXT,
    service_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    time TEXT NOT NULL,
    FOREIGN KEY (service_id) REFERENCES services (id)
)
""")
conn.commit()

# Заполнение таблицы услуг
cursor.execute("SELECT COUNT(*) FROM services")
if cursor.fetchone()[0] == 0:
    cursor.executemany(
        "INSERT INTO services (name, duration) VALUES (?, ?)",
        [
            ("Классическое наращивание (800 р.)", 180),
            ("1.5D объём (1000 р.)", 180),
            ("2D - 3D объём (1100 р.)", 180),
            ("Мокрый эффект (1200 - 1400 р.)", 180)
        ]
    )
    conn.commit()

# ===================== ОБРАБОТЧИКИ =====================

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        "👋 Привет! Я бот для записи на ресницы.\n\n"
        "Напишите /book, чтобы записаться на услугу, или /my_booking, чтобы проверить вашу запись."
    )

@bot.message_handler(commands=['book'])
def book(message):
    cursor.execute("SELECT id, name FROM services")
    services = cursor.fetchall()
    kb = InlineKeyboardMarkup(row_width=1)
    for service_id, name in services:
        kb.add(InlineKeyboardButton(name, callback_data=f"service_{service_id}"))
    bot.send_message(message.chat.id, "Выберите услугу из списка ниже:", reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data.startswith("service_"))
def select_service(call):
    service_id = int(call.data.split("_")[1])
    cursor.execute("SELECT name, duration FROM services WHERE id = ?", (service_id,))
    service = cursor.fetchone()

    if not service:
        bot.send_message(call.message.chat.id, "❌ Услуга не найдена. Попробуйте ещё раз.")
        return

    service_name, duration = service
    bot.send_message(call.message.chat.id, f"✅ Вы выбрали услугу: {service_name}.\n\nНапишите дату в формате ДД.ММ.ГГГГ:")

    @bot.message_handler(func=lambda msg: True)
    def select_date(msg):
        date = msg.text
        try:
            datetime.strptime(date, "%d.%m.%Y")
            available_slots = get_available_time_slots(date, duration)
            if available_slots:
                kb = InlineKeyboardMarkup(row_width=3)
                for time in available_slots:
                    kb.add(InlineKeyboardButton(time, callback_data=f"time_{date}_{time}_{service_id}"))
                bot.send_message(msg.chat.id, f"📅 Доступное время на {date}:", reply_markup=kb)
            else:
                bot.send_message(msg.chat.id, f"❌ На {date} нет доступного времени.")
        except ValueError:
            bot.send_message(msg.chat.id, "❌ Неверный формат даты. Попробуйте снова (ДД.ММ.ГГГГ).")

@bot.callback_query_handler(func=lambda call: call.data.startswith("time_"))
def book_time(call):
    _, date, time, service_id = call.data.split("_")
    user_id = call.from_user.id
    username = call.from_user.username or "Неизвестный пользователь"

    cursor.execute("SELECT * FROM bookings WHERE date = ? AND time = ?", (date, time))
    if cursor.fetchone():
        bot.send_message(call.message.chat.id, "❌ Это время уже занято. Выберите другое.")
        return

    cursor.execute(
        "INSERT INTO bookings (user_id, username, service_id, date, time) VALUES (?, ?, ?, ?, ?)",
        (user_id, username, service_id, date, time)
    )
    conn.commit()

    bot.send_message(call.message.chat.id, "✅ Вы успешно записались! Спасибо!")
    notify_master_new_booking(username, service_id, date, time)

@bot.message_handler(commands=['my_booking'])
def my_booking(message):
    user_id = message.from_user.id
    cursor.execute("SELECT id, service_id, date, time FROM bookings WHERE user_id = ?", (user_id,))
    booking = cursor.fetchone()

    if booking:
        booking_id, service_id, date, time = booking
        cursor.execute("SELECT name FROM services WHERE id = ?", (service_id,))
        service_name = cursor.fetchone()[0]
        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton("❌ Отменить запись", callback_data=f"cancel_{booking_id}")
        )
        bot.send_message(
            message.chat.id,
            f"📋 Ваша запись:\n\n"
            f"Услуга: {service_name}\n"
            f"Дата: {date}\n"
            f"Время: {time}",
            reply_markup=kb
        )
    else:
        bot.send_message(message.chat.id, "❌ У вас нет активных записей.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("cancel_"))
def cancel_booking(call):
    booking_id = int(call.data.split("_")[1])
    cursor.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))
    conn.commit()
    bot.send_message(call.message.chat.id, "✅ Ваша запись успешно отменена.")
    # Уведомление мастеру об отмене можно добавить по аналогии с notify_master_new_booking

# ===================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====================

def get_available_time_slots(date, duration):
    cursor.execute("SELECT time, service_id FROM bookings WHERE date = ?", (date,))
    bookings = cursor.fetchall()

    start_time = datetime.strptime("10:00", "%H:%M")
    end_time = datetime.strptime("18:00", "%H:%M")

    busy_intervals = []
    for time, service_id in bookings:
        cursor.execute("SELECT duration FROM services WHERE id = ?", (service_id,))
        service_duration = cursor.fetchone()[0]
        start = datetime.strptime(time, "%H:%M")
        busy_intervals.append((start, start + timedelta(minutes=service_duration)))

    available_slots = []
    current_time = start_time
    while current_time + timedelta(minutes=duration) <= end_time:
        is_free = all(
            not (start <= current_time < end or start < current_time + timedelta(minutes=duration) <= end)
            for start, end in busy_intervals
        )
        if is_free:
            available_slots.append(current_time.strftime("%H:%M"))
        current_time += timedelta(minutes=30)

    return available_slots

def notify_master_new_booking(username, service_id, date, time):
    cursor.execute("SELECT name FROM services WHERE id = ?", (service_id,))
    service_name = cursor.fetchone()[0]
    bot.send_message(
        MASTER_ID,
        f"🔔 Новая запись:\n\n"
        f"Клиент: @{username}\n"
        f"Услуга: {service_name}\n"
        f"Дата: {date}\n"
        f"Время: {time}"
    )

# ===================== ЗАПУСК БОТА =====================
if __name__ == '__main__':
    bot.polling(none_stop=True)
