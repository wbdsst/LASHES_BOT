import sqlite3
import os
from datetime import datetime, timedelta

# Database file path
DB_FILE = 'appointments.db'

def init_db():
    """Initialize database"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Create appointments table
    c.execute('''
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            client_name TEXT NOT NULL,
            procedure_name TEXT NOT NULL,
            appointment_date TEXT NOT NULL,
            appointment_time TEXT NOT NULL,
            reminder_sent_24h BOOLEAN DEFAULT 0,
            reminder_sent_1h BOOLEAN DEFAULT 0
        )
    ''')
    
    conn.commit()
    conn.close()

def add_appointment(client_id: int, client_name: str, procedure_name: str, 
                   appointment_date: str, appointment_time: str) -> int:
    """Add new appointment to database"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    c.execute('''
        INSERT INTO appointments 
        (client_id, client_name, procedure_name, appointment_date, appointment_time)
        VALUES (?, ?, ?, ?, ?)
    ''', (client_id, client_name, procedure_name, appointment_date, appointment_time))
    
    appointment_id = c.lastrowid
    conn.commit()
    conn.close()
    
    return appointment_id

def get_appointments_by_date(date: str) -> list:
    """Get all appointments for specific date"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    c.execute('''
        SELECT appointment_time 
        FROM appointments 
        WHERE appointment_date = ?
    ''', (date,))
    
    appointments = [row[0] for row in c.fetchall()]
    conn.close()
    
    return appointments

def get_upcoming_appointments() -> list:
    """Get all upcoming appointments that need reminders"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Get appointments for next 24 hours that need 24h reminder
    c.execute('''
        SELECT id, client_id, client_name, procedure_name, 
               appointment_date, appointment_time, reminder_sent_24h, reminder_sent_1h
        FROM appointments 
        WHERE appointment_date >= date('now')
        AND appointment_date <= date('now', '+1 day')
        AND reminder_sent_24h = 0
    ''')
    
    appointments = c.fetchall()
    conn.close()
    
    return appointments

def mark_reminder_sent(appointment_id: int, reminder_type: str):
    """Mark reminder as sent"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    if reminder_type == '24h':
        c.execute('''
            UPDATE appointments 
            SET reminder_sent_24h = 1 
            WHERE id = ?
        ''', (appointment_id,))
    elif reminder_type == '1h':
        c.execute('''
            UPDATE appointments 
            SET reminder_sent_1h = 1 
            WHERE id = ?
        ''', (appointment_id,))
    
    conn.commit()
    conn.close()

def get_all_appointments() -> list:
    """Get all appointments"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    c.execute('''
        SELECT id, client_name, procedure_name, appointment_date, appointment_time
        FROM appointments
        ORDER BY appointment_date, appointment_time
    ''')
    
    appointments = c.fetchall()
    conn.close()
    
    return appointments

def get_today_appointments() -> list:
    """Get all appointments for today"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    c.execute('''
        SELECT id, client_name, procedure_name, appointment_date, appointment_time
        FROM appointments
        WHERE appointment_date = date('now')
        ORDER BY appointment_time
    ''')
    
    appointments = c.fetchall()
    conn.close()
    
    return appointments

def get_tomorrow_appointments() -> list:
    """Get all appointments for tomorrow"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    c.execute('''
        SELECT id, client_name, procedure_name, appointment_date, appointment_time
        FROM appointments
        WHERE appointment_date = date('now', '+1 day')
        ORDER BY appointment_time
    ''')
    
    appointments = c.fetchall()
    conn.close()
    
    return appointments

def cancel_appointment(user_id: int, date: str, time: str) -> bool:
    """Cancel an appointment"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    try:
        c.execute('''
            DELETE FROM appointments
            WHERE client_id = ? AND appointment_date = ? AND appointment_time = ?
        ''', (user_id, date, time))
        
        success = c.rowcount > 0
        conn.commit()
        return success
    except Exception as e:
        print(f"Error cancelling appointment: {e}")  # Debug output
        conn.rollback()
        return False
    finally:
        conn.close()

def get_user_appointments(user_id: int) -> list:
    """Get all appointments for a specific user"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    c.execute('''
        SELECT appointment_date, appointment_time, procedure_name
        FROM appointments
        WHERE client_id = ? AND appointment_date >= date('now')
        ORDER BY appointment_date, appointment_time
    ''', (user_id,))
    
    appointments = []
    for row in c.fetchall():
        appointments.append({
            'appointment_date': row[0],
            'appointment_time': row[1],
            'procedure_name': row[2]
        })
    
    conn.close()
    return appointments 