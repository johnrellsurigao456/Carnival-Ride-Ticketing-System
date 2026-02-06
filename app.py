from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime
import sqlite3

app = Flask(__name__)
app.secret_key = 'carnival_secret_key_2024'


# Database helper functions
def get_db_connection():
    conn = sqlite3.connect('carnival.db')
    conn.row_factory = sqlite3.Row
    return conn


def get_all_rides():
    conn = get_db_connection()
    rides = conn.execute('SELECT * FROM rides').fetchall()
    conn.close()
    return rides


def get_ride_by_id(ride_id):
    conn = get_db_connection()
    ride = conn.execute('SELECT * FROM rides WHERE id = ?', (ride_id,)).fetchone()
    conn.close()
    return ride


def get_all_bookings():
    conn = get_db_connection()
    bookings = conn.execute('SELECT * FROM bookings ORDER BY id DESC').fetchall()
    conn.close()
    return bookings


@app.route('/')
def dashboard():
    rides = get_all_rides()

    # Separate major and family rides
    major_rides = [dict(ride) for ride in rides if ride['type'] == 'Major Ride']
    family_rides = [dict(ride) for ride in rides if ride['type'] == 'Family Ride']

    # Calculate statistics
    total_rides = len(rides)
    total_tickets_available = sum(ride['available_tickets'] for ride in rides)

    bookings = get_all_bookings()
    total_bookings = len(bookings)

    return render_template('dashboard.html',
                           major_rides=major_rides,
                           family_rides=family_rides,
                           total_rides=total_rides,
                           total_tickets=total_tickets_available,
                           total_bookings=total_bookings)


@app.route('/book/<int:ride_id>', methods=['GET', 'POST'])
def book_ticket(ride_id):
    ride = get_ride_by_id(ride_id)

    if not ride:
        flash('Ride not found!', 'error')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        name = request.form.get('name')
        age = request.form.get('age')
        quantity = int(request.form.get('quantity', 1))

        if quantity > ride['available_tickets']:
            flash('Not enough tickets available!', 'error')
            return redirect(url_for('book_ticket', ride_id=ride_id))

        # Calculate total price
        total_price = ride['price'] * quantity
        booking_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Insert booking into database
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO bookings (name, age, ride_id, ride_name, quantity, total_price, booking_time)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (name, age, ride_id, ride['name'], quantity, total_price, booking_time))

        # Update available tickets
        new_available = ride['available_tickets'] - quantity
        conn.execute('UPDATE rides SET available_tickets = ? WHERE id = ?', (new_available, ride_id))

        conn.commit()
        conn.close()

        flash(f'Successfully booked {quantity} ticket(s) for {ride["name"]}!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('book.html', ride=dict(ride))


@app.route('/bookings')
def view_bookings():
    bookings = get_all_bookings()
    bookings_list = [dict(booking) for booking in bookings]
    return render_template('bookings.html', bookings=bookings_list)


if __name__ == '__main__':
    app.run(debug=True)