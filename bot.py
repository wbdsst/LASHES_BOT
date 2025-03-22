import os
import logging
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import database

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
# You can modify these variables to customize the bot
TOKEN = os.getenv('TELEGRAM_TOKEN')  # Your bot token from @BotFather
ADMIN_ID = int(os.getenv('ADMIN_ID'))  # Your Telegram ID for admin functions

# Debug output
print(f"Loaded TOKEN: {TOKEN}")
print(f"Loaded ADMIN_ID: {ADMIN_ID}")

if not TOKEN:
    raise ValueError("TELEGRAM_TOKEN not found in environment variables!")

if not ADMIN_ID:
    raise ValueError("ADMIN_ID not found in environment variables!")

# Available time slots (you can modify these)
TIME_SLOTS = [
    "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00"
]

# Available procedures (you can modify these)
PROCEDURES = {
    "lash_lifting": "Lash Lifting - 3000₽",
    "lash_extension": "Lash Extension - 4000₽",
    "brow_lamination": "Brow Lamination - 2500₽",
    "brow_correction": "Brow Correction - 1500₽"
}

# States
class BookingStates(StatesGroup):
    selecting_procedure = State()
    selecting_date = State()
    selecting_time = State()

def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return str(user_id) == str(ADMIN_ID)

async def send_notification(bot: Bot, chat_id: int, message: str):
    """Send notification to user"""
    try:
        print(f"Sending notification to chat_id: {chat_id}")  # Debug output
        await bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode='HTML'
        )
        print("Notification sent successfully")  # Debug output
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")
        print(f"Error sending notification: {e}")  # Debug output

async def check_appointments(bot: Bot):
    """Check for upcoming appointments and send reminders"""
    while True:
        appointments = database.get_upcoming_appointments()
        now = datetime.now()
        
        for appointment in appointments:
            appointment_id, client_id, client_name, procedure_name, \
            appointment_date, appointment_time, reminder_sent_24h, reminder_sent_1h = appointment
            
            appointment_datetime = datetime.strptime(
                f"{appointment_date} {appointment_time}", 
                '%Y-%m-%d %H:%M'
            )
            
            # Calculate time difference
            time_diff = appointment_datetime - now
            hours_diff = time_diff.total_seconds() / 3600
            
            # Send 24h reminder
            if not reminder_sent_24h and 24 <= hours_diff <= 24.5:
                reminder_message = (
                    f"🔔 Напоминание!\n\n"
                    f"Завтра у вас запись на процедуру:\n"
                    f"Процедура: {procedure_name}\n"
                    f"Время: {appointment_time}\n\n"
                    f"Ждем вас!"
                )
                await send_notification(bot, client_id, reminder_message)
                database.mark_reminder_sent(appointment_id, '24h')
            
            # Send 1h reminder
            elif not reminder_sent_1h and 1 <= hours_diff <= 1.5:
                reminder_message = (
                    f"🔔 Напоминание!\n\n"
                    f"Через час у вас запись на процедуру:\n"
                    f"Процедура: {procedure_name}\n"
                    f"Время: {appointment_time}\n\n"
                    f"Ждем вас!"
                )
                await send_notification(bot, client_id, reminder_message)
                database.mark_reminder_sent(appointment_id, '1h')
                
                # Send master reminder
                master_message = (
                    f"🔔 Напоминание!\n\n"
                    f"Через час у вас запись:\n"
                    f"Клиент: {client_name}\n"
                    f"Процедура: {procedure_name}\n"
                    f"Время: {appointment_time}"
                )
                await send_notification(bot, ADMIN_ID, master_message)
        
        # Check every minute
        await asyncio.sleep(60)

def format_appointments_list(appointments: list) -> str:
    """Format appointments list for display"""
    if not appointments:
        return "Нет записей"
    
    message = "📅 Список записей:\n\n"
    current_date = None
    
    for app in appointments:
        app_id, client_name, procedure_name, date, time = app
        date_obj = datetime.strptime(date, '%Y-%m-%d')
        formatted_date = date_obj.strftime('%d.%m.%Y')
        
        if formatted_date != current_date:
            message += f"\n📌 {formatted_date}:\n"
            current_date = formatted_date
        
        message += f"🕒 {time} - {client_name} - {procedure_name}\n"
    
    return message

async def start(message: types.Message):
    """Start command handler"""
    user_id = message.from_user.id
    
    # Create welcome message with start button
    keyboard = [[InlineKeyboardButton(text="🚀 Начать", callback_data='start_bot')]]
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    await message.answer(
        "👋 Добро пожаловать в бот для записи на процедуры!\n\n"
        "Нажмите кнопку 'Начать' для продолжения:",
        reply_markup=reply_markup
    )

async def process_start_bot(callback: types.CallbackQuery):
    """Process start button click"""
    user_id = callback.from_user.id
    
    if is_admin(user_id):
        # Admin menu
        keyboard = [
            [InlineKeyboardButton(text="📅 Все записи", callback_data='admin_all')],
            [InlineKeyboardButton(text="📅 Записи на сегодня", callback_data='admin_today')],
            [InlineKeyboardButton(text="📅 Записи на завтра", callback_data='admin_tomorrow')],
            [InlineKeyboardButton(text="📊 Статистика", callback_data='admin_stats')]
        ]
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        await callback.message.edit_text(
            "👋 Добро пожаловать в панель администратора!\n\n"
            "Выберите действие:",
            reply_markup=reply_markup
        )
    else:
        # Client menu
        keyboard = [
            [InlineKeyboardButton(text="📅 Записаться на процедуру", callback_data='book')],
            [InlineKeyboardButton(text="❌ Отменить запись", callback_data='cancel')]
        ]
        if is_admin(user_id):
            keyboard.append([InlineKeyboardButton(text="👨‍💼 Панель администратора", callback_data='admin')])
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        await callback.message.edit_text(
            "👋 Добро пожаловать в бот для записи на процедуры!\n\n"
            "Выберите действие:",
            reply_markup=reply_markup
        )

async def process_booking_start(callback: types.CallbackQuery, state: FSMContext):
    """Start booking process"""
    keyboard = [[InlineKeyboardButton(text=name, callback_data=f'proc_{proc_id}')] 
                for proc_id, name in PROCEDURES.items()]
    # Add back button
    keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data='back_to_start')])
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    await callback.message.edit_text(
        "Выберите процедуру:",
        reply_markup=reply_markup
    )
    await state.set_state(BookingStates.selecting_procedure)

async def process_procedure_selection(callback: types.CallbackQuery, state: FSMContext):
    """Process procedure selection"""
    print(f"Processing procedure selection: {callback.data}")  # Debug output
    proc_id = '_'.join(callback.data.split('_')[1:])
    await state.update_data(selected_procedure=proc_id)
    print(f"Updated state with procedure: {proc_id}")  # Debug output
    
    # Generate dates for next 7 days
    dates = []
    for i in range(7):
        date = datetime.now() + timedelta(days=i)
        date_str = date.strftime('%Y-%m-%d')
        booked_times = database.get_appointments_by_date(date_str)
        if len(booked_times) < len(TIME_SLOTS):
            dates.append(date)
    
    keyboard = [[InlineKeyboardButton(
        text=date.strftime('%d.%m.%Y'),
        callback_data=f'date_{date.strftime("%Y-%m-%d")}'
    )] for date in dates]
    # Add back button
    keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data='back_to_procedures')])
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    await callback.message.edit_text(
        "Выберите дату:",
        reply_markup=reply_markup
    )
    await state.set_state(BookingStates.selecting_date)
    print(f"State set to selecting_date")  # Debug output

async def process_date_selection(callback: types.CallbackQuery, state: FSMContext):
    """Process date selection"""
    print(f"Processing date selection: {callback.data}")  # Debug output
    date = callback.data.split('_')[1]
    await state.update_data(selected_date=date)
    print(f"Updated state with date: {date}")  # Debug output
    
    # Filter out booked time slots
    booked_times = database.get_appointments_by_date(date)
    available_slots = [slot for slot in TIME_SLOTS if slot not in booked_times]
    
    keyboard = [[InlineKeyboardButton(
        text=slot,
        callback_data=f'time_{slot}'
    )] for slot in available_slots]
    # Add back button
    keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data='back_to_dates')])
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    await callback.message.edit_text(
        "Выберите время:",
        reply_markup=reply_markup
    )
    await state.set_state(BookingStates.selecting_time)
    print(f"State set to selecting_time")  # Debug output

async def process_time_selection(callback: types.CallbackQuery, state: FSMContext):
    """Process time selection and confirm booking"""
    print(f"Processing time selection: {callback.data}")  # Debug output
    current_state = await state.get_state()
    print(f"Current state: {current_state}")  # Debug output
    
    data = await state.get_data()
    print(f"State data: {data}")  # Debug output
    
    if not data or 'selected_date' not in data or 'selected_procedure' not in data:
        print("Missing required data in state")  # Debug output
        await callback.message.edit_text(
            "Произошла ошибка при обработке записи. Пожалуйста, попробуйте снова."
        )
        await state.clear()
        return
    
    time = callback.data.split('_')[1]
    date = data['selected_date']
    proc_id = data['selected_procedure']
    
    # Add appointment to database
    database.add_appointment(
        client_id=callback.from_user.id,
        client_name=callback.from_user.full_name,
        procedure_name=PROCEDURES[proc_id],
        appointment_date=date,
        appointment_time=time
    )
    
    # Format confirmation message
    proc_name = PROCEDURES[proc_id]
    client_message = (
        f"✅ Запись подтверждена!\n\n"
        f"Процедура: {proc_name}\n"
        f"Дата: {datetime.strptime(date, '%Y-%m-%d').strftime('%d.%m.%Y')}\n"
        f"Время: {time}\n\n"
        f"Для отмены записи используйте команду /cancel"
    )
    
    # Send notification to master
    master_message = (
        f"📝 Новая запись!\n\n"
        f"Процедура: {proc_name}\n"
        f"Дата: {datetime.strptime(date, '%Y-%m-%d').strftime('%d.%m.%Y')}\n"
        f"Время: {time}\n"
        f"Клиент: {callback.from_user.full_name}"
    )
    
    print(f"Attempting to send master notification to ADMIN_ID: {ADMIN_ID}")  # Debug output
    await callback.message.edit_text(client_message)
    await send_notification(callback.bot, ADMIN_ID, master_message)
    await state.clear()
    print("Booking completed successfully")  # Debug output

async def cancel_appointment(message: types.Message):
    """Handle appointment cancellation"""
    user_id = message.from_user.id
    appointments = database.get_user_appointments(user_id)
    
    if not appointments:
        await message.answer(
            "У вас нет активных записей.",
            reply_markup=ReplyKeyboardRemove()
        )
        return
    
    # Create keyboard with cancel buttons for each appointment
    keyboard = []
    for appt in appointments:
        date = datetime.strptime(appt['appointment_date'], '%Y-%m-%d').strftime('%d.%m.%Y')
        button_text = f"❌ {appt['procedure_name']} - {date} {appt['appointment_time']}"
        keyboard.append([InlineKeyboardButton(
            text=button_text,
            callback_data=f"cancel_{appt['appointment_date']}_{appt['appointment_time']}"
        )])
    
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await message.answer(
        "Выберите запись для отмены:",
        reply_markup=reply_markup
    )

async def process_cancel(callback: types.CallbackQuery):
    """Process appointment cancellation"""
    try:
        # Extract date and time from callback data
        _, date, time = callback.data.split('_')
        
        # Cancel the appointment
        if database.cancel_appointment(callback.from_user.id, date, time):
            # Send confirmation to client
            await callback.message.edit_text(
                "✅ Запись успешно отменена.",
                reply_markup=None
            )
            
            # Send notification to master
            master_message = (
                f"❌ Запись отменена\n\n"
                f"Клиент: {callback.from_user.full_name}\n"
                f"Дата: {datetime.strptime(date, '%Y-%m-%d').strftime('%d.%m.%Y')}\n"
                f"Время: {time}"
            )
            await send_notification(callback.bot, ADMIN_ID, master_message)
            
            # Show updated list of appointments
            appointments = database.get_user_appointments(callback.from_user.id)
            if appointments:
                keyboard = []
                for appt in appointments:
                    date = datetime.strptime(appt['appointment_date'], '%Y-%m-%d').strftime('%d.%m.%Y')
                    button_text = f"❌ {appt['procedure_name']} - {date} {appt['appointment_time']}"
                    keyboard.append([InlineKeyboardButton(
                        text=button_text,
                        callback_data=f"cancel_{appt['appointment_date']}_{appt['appointment_time']}"
                    )])
                
                reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
                await callback.message.answer(
                    "Выберите запись для отмены:",
                    reply_markup=reply_markup
                )
            else:
                await callback.message.answer(
                    "У вас нет активных записей.",
                    reply_markup=ReplyKeyboardRemove()
                )
        else:
            await callback.message.edit_text(
                "❌ Не удалось отменить запись. Пожалуйста, попробуйте снова.",
                reply_markup=None
            )
            
    except Exception as e:
        logger.error(f"Error cancelling appointment: {e}")
        await callback.message.edit_text(
            "Произошла ошибка при отмене записи. Пожалуйста, попробуйте снова.",
            reply_markup=None
        )

async def process_admin_all(callback: types.CallbackQuery):
    """Process admin all appointments request"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа к этой функции", show_alert=True)
        return
    
    appointments = database.get_all_appointments()
    message = format_appointments_list(appointments)
    
    keyboard = [[InlineKeyboardButton(text="◀️ Назад", callback_data='admin_back')]]
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await callback.message.edit_text(message, reply_markup=reply_markup)

async def process_admin_today(callback: types.CallbackQuery):
    """Process admin today appointments request"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа к этой функции", show_alert=True)
        return
    
    appointments = database.get_today_appointments()
    message = format_appointments_list(appointments)
    
    keyboard = [[InlineKeyboardButton(text="◀️ Назад", callback_data='admin_back')]]
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await callback.message.edit_text(message, reply_markup=reply_markup)

async def process_admin_tomorrow(callback: types.CallbackQuery):
    """Process admin tomorrow appointments request"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа к этой функции", show_alert=True)
        return
    
    appointments = database.get_tomorrow_appointments()
    message = format_appointments_list(appointments)
    
    keyboard = [[InlineKeyboardButton(text="◀️ Назад", callback_data='admin_back')]]
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await callback.message.edit_text(message, reply_markup=reply_markup)

async def process_admin_stats(callback: types.CallbackQuery):
    """Process admin stats request"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа к этой функции", show_alert=True)
        return
    
    # TODO: Implement statistics
    message = "📊 Статистика в разработке..."
    
    keyboard = [[InlineKeyboardButton(text="◀️ Назад", callback_data='admin_back')]]
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await callback.message.edit_text(message, reply_markup=reply_markup)

async def process_admin_back(callback: types.CallbackQuery):
    """Process admin back button"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа к этой функции", show_alert=True)
        return
    
    keyboard = [
        [InlineKeyboardButton(text="📅 Все записи", callback_data='admin_all')],
        [InlineKeyboardButton(text="📅 Записи на сегодня", callback_data='admin_today')],
        [InlineKeyboardButton(text="📅 Записи на завтра", callback_data='admin_tomorrow')],
        [InlineKeyboardButton(text="📊 Статистика", callback_data='admin_stats')]
    ]
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    await callback.message.edit_text(
        "👋 Панель администратора\n\n"
        "Выберите действие:",
        reply_markup=reply_markup
    )

async def process_back_to_start(callback: types.CallbackQuery, state: FSMContext):
    """Process back to start button"""
    await state.clear()
    keyboard = [
        [InlineKeyboardButton(text="📅 Записаться на процедуру", callback_data='book')],
        [InlineKeyboardButton(text="❌ Отменить запись", callback_data='cancel')]
    ]
    if is_admin(callback.from_user.id):
        keyboard.append([InlineKeyboardButton(text="👨‍💼 Панель администратора", callback_data='admin')])
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    await callback.message.edit_text(
        "👋 Добро пожаловать в бот для записи на процедуры!\n\n"
        "Выберите действие:",
        reply_markup=reply_markup
    )

async def process_back_to_procedures(callback: types.CallbackQuery, state: FSMContext):
    """Process back to procedures button"""
    await state.clear()
    await process_booking_start(callback, state)

async def process_back_to_dates(callback: types.CallbackQuery, state: FSMContext):
    """Process back to dates button"""
    data = await state.get_data()
    if 'selected_procedure' in data:
        await process_procedure_selection(callback, state)
    else:
        await process_booking_start(callback, state)

async def main():
    """Start the bot"""
    # Initialize database
    database.init_db()
    
    # Create bot and dispatcher
    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    
    # Register handlers
    dp.message.register(start, Command("start"))
    dp.message.register(cancel_appointment, Command("cancel"))
    
    # Register callback handlers
    dp.callback_query.register(process_start_bot, lambda c: c.data == 'start_bot')
    dp.callback_query.register(process_booking_start, lambda c: c.data == 'book')
    dp.callback_query.register(process_procedure_selection, lambda c: c.data.startswith('proc_'))
    dp.callback_query.register(process_date_selection, lambda c: c.data.startswith('date_'))
    dp.callback_query.register(process_time_selection, lambda c: c.data.startswith('time_'))
    dp.callback_query.register(process_cancel, lambda c: c.data.startswith('cancel_'))
    dp.callback_query.register(process_admin_all, lambda c: c.data == 'admin_all')
    dp.callback_query.register(process_admin_today, lambda c: c.data == 'admin_today')
    dp.callback_query.register(process_admin_tomorrow, lambda c: c.data == 'admin_tomorrow')
    dp.callback_query.register(process_admin_stats, lambda c: c.data == 'admin_stats')
    dp.callback_query.register(process_admin_back, lambda c: c.data == 'admin_back')
    
    # Register back button handlers
    dp.callback_query.register(process_back_to_start, lambda c: c.data == 'back_to_start')
    dp.callback_query.register(process_back_to_procedures, lambda c: c.data == 'back_to_procedures')
    dp.callback_query.register(process_back_to_dates, lambda c: c.data == 'back_to_dates')
    
    # Start the appointment checker
    asyncio.create_task(check_appointments(bot))
    
    # Start polling
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main()) 