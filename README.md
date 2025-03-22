# Telegram Bot for Appointment Scheduling

A Telegram bot for scheduling appointments with a master. The bot allows clients to book appointments, cancel them, and sends notifications to both clients and the master.

## Features

- Appointment booking with procedure selection
- Date and time slot selection
- Appointment cancellation
- Automatic notifications for both clients and master
- Admin panel for viewing appointments and statistics
- SQLite database for storing appointments
- Back buttons for easy navigation
- Start button for initial interaction
- User-friendly interface with emojis

## Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file in the project root with the following variables:
   ```
   TELEGRAM_TOKEN=your_telegram_bot_token
   ADMIN_ID=your_telegram_id
   ```

   To get your Telegram ID:
   1. Send a message to @userinfobot on Telegram
   2. The bot will reply with your ID
   3. Copy this ID and paste it as ADMIN_ID in the .env file
   
   Alternatively, you can:
   1. Open Telegram in your browser (web.telegram.org)
   2. Open any chat
   3. Look at the URL: `https://web.telegram.org/k/#123456789`
   4. The number after # is your ID

4. Run the bot:
   ```bash
   python bot.py
   ```

## Usage

### For Clients

1. Start the bot with `/start` command
2. Click the "🚀 Начать" button
3. Select a procedure from the list
4. Choose a date from available dates
5. Select a time slot
6. Confirm the booking

To cancel an appointment:
1. Click "❌ Отменить запись" in the main menu
2. Select the appointment you want to cancel from the list
3. Confirm the cancellation

### For Administrators

1. Access the admin panel by clicking "👨‍💼 Панель администратора" in the main menu
2. Available options:
   - View all appointments
   - View today's appointments
   - View tomorrow's appointments
   - View booking statistics

## Navigation

- Use "◀️ Назад" buttons to return to previous steps
- Use "◀️ Назад" in admin panel to return to main admin menu
- Use "🚀 Начать" to start working with the bot

## Notifications

The bot sends notifications to:
- Clients: 24 hours and 1 hour before the appointment
- Master: When a new appointment is booked or cancelled

## Database

The bot uses SQLite database (`appointments.db`) to store appointments. The database is automatically created when the bot starts.

## Requirements

- Python 3.7+
- aiogram
- python-dotenv
- SQLite3

## Configuration

You can modify the following variables in `bot.py`:
- `TIME_SLOTS`: Available time slots for appointments
- `PROCEDURES`: List of procedures and their prices

## Error Handling

The bot includes error handling for:
- Database operations
- Notification sending
- Appointment cancellation
- Invalid user inputs

## Security

- Admin functions are protected and only accessible to users with the correct ADMIN_ID
- All database operations are wrapped in try-except blocks
- User data is properly sanitized before database operations
