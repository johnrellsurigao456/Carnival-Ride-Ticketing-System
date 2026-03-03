from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from datetime import datetime
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import qrcode
import io
import base64
import secrets

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


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            flash('Admin access required!', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


def cashier_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'cashier':
            flash('Cashier access required!', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


def generate_qr_code(data):
    """Generate QR code and return as base64 string"""
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    # Convert to base64
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return img_str


# Routes
@app.route('/')
def home():
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif session.get('role') == 'cashier':
            return redirect(url_for('cashier_dashboard'))
    return render_template('home.html')


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
            session['role'] = user['role']

            flash(f'Welcome back, {user["full_name"]}!', 'success')

            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('cashier_dashboard'))
        else:
            flash('Invalid username or password!', 'error')
            return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully!', 'success')
    return redirect(url_for('home'))


# ADMIN ROUTES
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    conn = get_db_connection()

    # Get all rides
    rides = conn.execute('SELECT * FROM rides ORDER BY type, name').fetchall()

    # Get all bookings
    all_bookings = conn.execute('SELECT * FROM bookings ORDER BY id DESC').fetchall()

    # Statistics
    total_rides = len(rides)
    total_bookings = len(all_bookings)
    unused_tickets = len([b for b in all_bookings if b['status'] == 'unused'])
    used_tickets = len([b for b in all_bookings if b['status'] == 'used'])
    total_revenue = sum([b['total_price'] for b in all_bookings])

    # Monthly statistics (current month)
    current_month = datetime.now().strftime('%Y-%m')
    monthly_bookings = [b for b in all_bookings if b['booking_time'].startswith(current_month)]
    monthly_revenue = sum([b['total_price'] for b in monthly_bookings])

    # Yearly statistics (current year)
    current_year = datetime.now().strftime('%Y')
    yearly_bookings = [b for b in all_bookings if b['booking_time'].startswith(current_year)]
    yearly_revenue = sum([b['total_price'] for b in yearly_bookings])

    # Best selling rides
    ride_bookings = {}
    for booking in all_bookings:
        ride_name = booking['ride_name']
        if ride_name not in ride_bookings:
            ride_bookings[ride_name] = 0
        ride_bookings[ride_name] += booking['quantity']

    best_rides = sorted(ride_bookings.items(), key=lambda x: x[1], reverse=True)[:5]

    conn.close()

    return render_template('admin_dashboard.html',
                           rides=rides,
                           total_rides=total_rides,
                           total_bookings=total_bookings,
                           unused_tickets=unused_tickets,
                           used_tickets=used_tickets,
                           total_revenue=total_revenue,
                           monthly_bookings=len(monthly_bookings),
                           monthly_revenue=monthly_revenue,
                           yearly_bookings=len(yearly_bookings),
                           yearly_revenue=yearly_revenue,
                           best_rides=best_rides)


@app.route('/admin/bookings')
@admin_required
def admin_bookings():
    conn = get_db_connection()
    bookings = conn.execute('SELECT * FROM bookings ORDER BY id DESC').fetchall()
    conn.close()

    bookings_list = [dict(booking) for booking in bookings]
    return render_template('admin_bookings.html', bookings=bookings_list)


@app.route('/admin/rides/add', methods=['GET', 'POST'])
@admin_required
def admin_add_ride():
    if request.method == 'POST':
        name = request.form.get('name')
        ride_type = request.form.get('type')
        price = float(request.form.get('price'))
        total_tickets = int(request.form.get('total_tickets'))
        schedule = request.form.get('schedule')
        age_limit = request.form.get('age_limit')
        height_limit = request.form.get('height_limit')

        conn = get_db_connection()
        conn.execute('''
            INSERT INTO rides (name, type, price, available_tickets, total_tickets, schedule, age_limit, height_limit, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, ride_type, price, total_tickets, total_tickets, schedule, age_limit, height_limit,
              datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        conn.close()

        flash(f'Ride "{name}" added successfully!', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('admin_add_ride.html')


@app.route('/admin/rides/edit/<int:ride_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_ride(ride_id):
    conn = get_db_connection()
    ride = conn.execute('SELECT * FROM rides WHERE id = ?', (ride_id,)).fetchone()

    if not ride:
        flash('Ride not found!', 'error')
        conn.close()
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        name = request.form.get('name')
        ride_type = request.form.get('type')
        price = float(request.form.get('price'))
        available_tickets = int(request.form.get('available_tickets'))
        total_tickets = int(request.form.get('total_tickets'))
        schedule = request.form.get('schedule')
        age_limit = request.form.get('age_limit')
        height_limit = request.form.get('height_limit')

        conn.execute('''
            UPDATE rides 
            SET name=?, type=?, price=?, available_tickets=?, total_tickets=?, 
                schedule=?, age_limit=?, height_limit=?
            WHERE id=?
        ''', (name, ride_type, price, available_tickets, total_tickets, schedule,
              age_limit, height_limit, ride_id))
        conn.commit()
        conn.close()

        flash(f'Ride "{name}" updated successfully!', 'success')
        return redirect(url_for('admin_dashboard'))

    conn.close()
    return render_template('admin_edit_ride.html', ride=dict(ride))


@app.route('/admin/rides/delete/<int:ride_id>')
@admin_required
def admin_delete_ride(ride_id):
    conn = get_db_connection()
    ride = conn.execute('SELECT * FROM rides WHERE id = ?', (ride_id,)).fetchone()

    if ride:
        conn.execute('DELETE FROM rides WHERE id = ?', (ride_id,))
        conn.commit()
        flash(f'Ride "{ride["name"]}" deleted successfully!', 'success')
    else:
        flash('Ride not found!', 'error')

    conn.close()
    return redirect(url_for('admin_dashboard'))


# CASHIER ROUTES
@app.route('/cashier/dashboard')
@cashier_required
def cashier_dashboard():
    conn = get_db_connection()
    rides = conn.execute('SELECT * FROM rides WHERE available_tickets > 0 ORDER BY type, name').fetchall()

    # Separate major and family rides
    major_rides = [dict(ride) for ride in rides if ride['type'] == 'Major Ride']
    family_rides = [dict(ride) for ride in rides if ride['type'] == 'Family Ride']

    # Get cashier's bookings
    cashier_bookings = conn.execute('SELECT * FROM bookings WHERE cashier_id = ?',
                                    (session['user_id'],)).fetchall()

    total_sales = sum([b['total_price'] for b in cashier_bookings])
    total_bookings = len(cashier_bookings)

    conn.close()

    return render_template('cashier_dashboard.html',
                           major_rides=major_rides,
                           family_rides=family_rides,
                           total_sales=total_sales,
                           total_bookings=total_bookings)


@app.route('/cashier/book/<int:ride_id>', methods=['GET', 'POST'])
@cashier_required
def cashier_book(ride_id):
    conn = get_db_connection()
    ride = conn.execute('SELECT * FROM rides WHERE id = ?', (ride_id,)).fetchone()

    if not ride:
        flash('Ride not found!', 'error')
        conn.close()
        return redirect(url_for('cashier_dashboard'))

    if request.method == 'POST':
        customer_name = request.form.get('customer_name')
        customer_age = int(request.form.get('customer_age'))
        quantity = int(request.form.get('quantity', 1))

        if quantity > ride['available_tickets']:
            flash('Not enough tickets available!', 'error')
            conn.close()
            return redirect(url_for('cashier_book', ride_id=ride_id))

        # Generate unique QR code
        qr_code = secrets.token_urlsafe(16)
        total_price = ride['price'] * quantity
        booking_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Insert booking
        cursor = conn.execute('''
            INSERT INTO bookings (cashier_id, cashier_name, customer_name, customer_age, 
                                ride_id, ride_name, quantity, total_price, booking_time, qr_code, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (session['user_id'], session['full_name'], customer_name, customer_age,
              ride_id, ride['name'], quantity, total_price, booking_time, qr_code, 'unused'))

        booking_id = cursor.lastrowid

        # Update available tickets
        new_available = ride['available_tickets'] - quantity
        conn.execute('UPDATE rides SET available_tickets = ? WHERE id = ?', (new_available, ride_id))

        conn.commit()
        conn.close()

        flash(f'Successfully booked {quantity} ticket(s) for {customer_name}!', 'success')
        return redirect(url_for('view_ticket', booking_id=booking_id))

    conn.close()
    return render_template('cashier_book.html', ride=dict(ride))


@app.route('/cashier/bookings')
@cashier_required
def cashier_bookings():
    conn = get_db_connection()
    bookings = conn.execute('SELECT * FROM bookings WHERE cashier_id = ? ORDER BY id DESC',
                            (session['user_id'],)).fetchall()
    conn.close()

    bookings_list = [dict(booking) for booking in bookings]
    return render_template('cashier_bookings.html', bookings=bookings_list)


@app.route('/ticket/<int:booking_id>')
@login_required
def view_ticket(booking_id):
    conn = get_db_connection()
    booking = conn.execute('SELECT * FROM bookings WHERE id = ?', (booking_id,)).fetchone()
    conn.close()

    if not booking:
        flash('Ticket not found!', 'error')
        return redirect(url_for('cashier_dashboard'))

    # Generate QR code
    qr_data = f"BOOKING-{booking['id']}-{booking['qr_code']}"
    qr_code_img = generate_qr_code(qr_data)

    return render_template('ticket.html', booking=dict(booking), qr_code=qr_code_img)


@app.route('/scan', methods=['GET', 'POST'])
@login_required
def scan_ticket():
    if request.method == 'POST':
        qr_code = request.form.get('qr_code')

        conn = get_db_connection()
        booking = conn.execute('SELECT * FROM bookings WHERE qr_code = ?', (qr_code,)).fetchone()

        if not booking:
            flash('Invalid ticket!', 'error')
            conn.close()
            return redirect(url_for('scan_ticket'))

        if booking['status'] == 'used':
            flash(f'Ticket already used on {booking["used_time"]}!', 'error')
            conn.close()
            return redirect(url_for('scan_ticket'))

        # Mark as used
        used_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute('UPDATE bookings SET status = ?, used_time = ? WHERE id = ?',
                     ('used', used_time, booking['id']))
        conn.commit()
        conn.close()

        flash(f'Ticket validated successfully! Customer: {booking["customer_name"]}, Ride: {booking["ride_name"]}',
              'success')
        return redirect(url_for('scan_ticket'))

    return render_template('scan_ticket.html')


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/contact')
def contact():
    return render_template('contact.html')


if __name__ == '__main__':
    app.run(debug=True)