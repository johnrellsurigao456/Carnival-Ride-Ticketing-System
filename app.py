from flask import Flask, render_template, request, redirect, url_for, flash, session
from datetime import datetime
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = 'carnival_secret_key_2024'


# Database helper functions
def get_db_connection():
    conn = sqlite3.connect('carnival.db')
    conn.row_factory = sqlite3.Row
    return conn


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first!', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


# Routes
@app.route('/')
def home():
    return render_template('home.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        full_name = request.form.get('full_name')

        # Validation
        if password != confirm_password:
            flash('Passwords do not match!', 'error')
            return redirect(url_for('register'))

        # Check if user exists
        conn = get_db_connection()
        existing_user = conn.execute('SELECT * FROM users WHERE username = ? OR email = ?',
                                     (username, email)).fetchone()

        if existing_user:
            flash('Username or email already exists!', 'error')
            conn.close()
            return redirect(url_for('register'))

        # Create new user
        hashed_password = generate_password_hash(password)
        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        conn.execute('''
            INSERT INTO users (username, email, password, full_name, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (username, email, hashed_password, full_name, created_at))

        conn.commit()
        conn.close()

        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['full_name'] = user['full_name']
            flash(f'Welcome back, {user["full_name"]}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password!', 'error')
            return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully!', 'success')
    return redirect(url_for('home'))


@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()
    rides = conn.execute('SELECT * FROM rides').fetchall()
    conn.close()

    # Separate major and family rides
    major_rides = [dict(ride) for ride in rides if ride['type'] == 'Major Ride']
    family_rides = [dict(ride) for ride in rides if ride['type'] == 'Family Ride']

    # Calculate statistics
    total_rides = len(rides)
    total_tickets_available = sum(ride['available_tickets'] for ride in rides)

    # Get user's bookings count
    conn = get_db_connection()
    user_bookings = conn.execute('SELECT * FROM bookings WHERE user_id = ?',
                                 (session['user_id'],)).fetchall()
    conn.close()
    total_bookings = len(user_bookings)

    return render_template('dashboard.html',
                           major_rides=major_rides,
                           family_rides=family_rides,
                           total_rides=total_rides,
                           total_tickets=total_tickets_available,
                           total_bookings=total_bookings)


@app.route('/book/<int:ride_id>', methods=['GET', 'POST'])
@login_required
def book_ticket(ride_id):
    conn = get_db_connection()
    ride = conn.execute('SELECT * FROM rides WHERE id = ?', (ride_id,)).fetchone()
    conn.close()

    if not ride:
        flash('Ride not found!', 'error')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
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
            INSERT INTO bookings (user_id, name, age, ride_id, ride_name, quantity, total_price, booking_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (session['user_id'], session['full_name'], age, ride_id, ride['name'], quantity, total_price,
              booking_time))

        # Update available tickets
        new_available = ride['available_tickets'] - quantity
        conn.execute('UPDATE rides SET available_tickets = ? WHERE id = ?', (new_available, ride_id))

        conn.commit()
        conn.close()

        flash(f'Successfully booked {quantity} ticket(s) for {ride["name"]}!', 'success')
        return redirect(url_for('view_bookings'))

    return render_template('book.html', ride=dict(ride))


@app.route('/bookings')
@login_required
def view_bookings():
    conn = get_db_connection()
    bookings = conn.execute('SELECT * FROM bookings WHERE user_id = ? ORDER BY id DESC',
                            (session['user_id'],)).fetchall()
    conn.close()

    bookings_list = [dict(booking) for booking in bookings]
    return render_template('bookings.html', bookings=bookings_list)


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/contact')
def contact():
    return render_template('contact.html')


if __name__ == '__main__':
    app.run(debug=True)