import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash
import secrets


def init_db():
    """Initialize the database and create tables"""
    conn = sqlite3.connect('carnival.db')
    cursor = conn.cursor()

    # Create Users table with roles (admin, cashier, customer)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'customer',
            created_at TEXT NOT NULL
        )
    ''')

    # Create Rides table (simplified - no age/height limits)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rides (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            price REAL NOT NULL,
            total_tickets INTEGER NOT NULL,
            available_tickets INTEGER NOT NULL,
            schedule TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    ''')

    # Create Bookings table (no customer name/age)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            user_name TEXT NOT NULL,
            user_role TEXT NOT NULL,
            booking_time TEXT NOT NULL,
            total_price REAL NOT NULL,
            qr_code TEXT UNIQUE NOT NULL,
            status TEXT NOT NULL DEFAULT 'unused',
            used_time TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # Create Booking Items table (for cart system - multiple rides per booking)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS booking_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id INTEGER NOT NULL,
            ride_id INTEGER NOT NULL,
            ride_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            subtotal REAL NOT NULL,
            FOREIGN KEY (booking_id) REFERENCES bookings (id),
            FOREIGN KEY (ride_id) REFERENCES rides (id)
        )
    ''')

    # Check if rides table is empty
    cursor.execute('SELECT COUNT(*) FROM rides')
    count = cursor.fetchone()[0]

    # If empty, insert sample data
    if count == 0:
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        sample_rides = [
            ('Dragon Coaster', 'Major Ride', 150, 50, 50, '10:00 AM - 8:00 PM', current_time),
            ('Viking Ship', 'Major Ride', 120, 40, 40, '10:30 AM - 7:30 PM', current_time),
            ('Ferris Wheel', 'Major Ride', 100, 60, 60, '9:00 AM - 9:00 PM', current_time),
            ('Carousel', 'Family Ride', 50, 80, 80, '9:00 AM - 8:00 PM', current_time),
            ('Tea Cups', 'Family Ride', 60, 70, 70, '10:00 AM - 7:00 PM', current_time),
            ('Mini Train', 'Family Ride', 40, 100, 100, '9:30 AM - 8:30 PM', current_time)
        ]

        cursor.executemany('''
            INSERT INTO rides (name, type, price, total_tickets, available_tickets, schedule, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', sample_rides)

    # Create default admin and cashier users if not exists
    cursor.execute('SELECT COUNT(*) FROM users')
    user_count = cursor.fetchone()[0]

    if user_count == 0:
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Admin user
        admin_password = generate_password_hash('admin123')
        cursor.execute('''
            INSERT INTO users (username, email, password, full_name, role, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('admin', 'admin@carnival.com', admin_password, 'Administrator', 'admin', current_time))

        # Cashier user
        cashier_password = generate_password_hash('cashier123')
        cursor.execute('''
            INSERT INTO users (username, email, password, full_name, role, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('cashier', 'cashier@carnival.com', cashier_password, 'Cashier User', 'cashier', current_time))

    conn.commit()
    conn.close()
    print("✅ Database initialized successfully!")
    print("\n📋 DEFAULT STAFF ACCOUNTS:")
    print("   ADMIN    - Username: admin    | Password: admin123")
    print("   CASHIER  - Username: cashier  | Password: cashier123")
    print("\n👥 Customers must register to create an account.")


if __name__ == '__main__':
    init_db()