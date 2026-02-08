import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash


def init_db():
    """Initialize the database and create tables"""
    conn = sqlite3.connect('carnival.db')
    cursor = conn.cursor()

    # Create Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    ''')

    # Create Rides table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rides (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            price REAL NOT NULL,
            available_tickets INTEGER NOT NULL,
            schedule TEXT NOT NULL,
            age_limit TEXT NOT NULL,
            height_limit TEXT NOT NULL
        )
    ''')

    # Create Bookings table with user_id
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            age INTEGER NOT NULL,
            ride_id INTEGER NOT NULL,
            ride_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            total_price REAL NOT NULL,
            booking_time TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (ride_id) REFERENCES rides (id)
        )
    ''')

    # Check if rides table is empty
    cursor.execute('SELECT COUNT(*) FROM rides')
    count = cursor.fetchone()[0]

    # If empty, insert sample data
    if count == 0:
        sample_rides = [
            ('Dragon Coaster', 'Major Ride', 150, 50, '10:00 AM - 8:00 PM', '12+', '4.5 ft minimum'),
            ('Viking Ship', 'Major Ride', 120, 40, '10:30 AM - 7:30 PM', '10+', '4 ft minimum'),
            ('Ferris Wheel', 'Major Ride', 100, 60, '9:00 AM - 9:00 PM', 'All ages', 'No limit'),
            ('Carousel', 'Family Ride', 50, 80, '9:00 AM - 8:00 PM', 'All ages', 'No limit'),
            ('Tea Cups', 'Family Ride', 60, 70, '10:00 AM - 7:00 PM', '5+', '3 ft minimum'),
            ('Mini Train', 'Family Ride', 40, 100, '9:30 AM - 8:30 PM', 'All ages', 'No limit')
        ]

        cursor.executemany('''
            INSERT INTO rides (name, type, price, available_tickets, schedule, age_limit, height_limit)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', sample_rides)

    # Create admin user if not exists
    cursor.execute('SELECT COUNT(*) FROM users')
    user_count = cursor.fetchone()[0]

    if user_count == 0:
        admin_password = generate_password_hash('admin123')
        cursor.execute('''
            INSERT INTO users (username, email, password, full_name, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', ('admin', 'admin@carnival.com', admin_password, 'Administrator',
              datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    conn.commit()
    conn.close()
    print("✅ Database initialized successfully!")


if __name__ == '__main__':
    init_db()