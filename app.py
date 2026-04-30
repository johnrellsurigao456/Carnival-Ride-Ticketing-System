from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
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


def customer_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'customer':
            flash('Customer access required!', 'error')
            return redirect(url_for('customer_login'))
        return f(*args, **kwargs)

    return decorated_function


def generate_qr_code(data):
    """Generate QR code and return as base64 string"""
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return img_str


# PUBLIC ROUTES
@app.route('/')
def home():
    return render_template('home.html')


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/contact')
def contact():
    return render_template('contact.html')


# STAFF LOGIN (Admin & Cashier)
@app.route('/staff/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ? AND role IN ("admin", "cashier")',
                            (username,)).fetchone()
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
            flash('Invalid credentials or not a staff member!', 'error')
            return redirect(url_for('login'))

    return render_template('staff_login.html')


# CUSTOMER REGISTER
@app.route('/customer/register', methods=['GET', 'POST'])
def customer_register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        full_name = request.form.get('full_name')

        if password != confirm_password:
            flash('Passwords do not match!', 'error')
            return redirect(url_for('customer_register'))

        conn = get_db_connection()
        existing_user = conn.execute('SELECT * FROM users WHERE username = ? OR email = ?',
                                     (username, email)).fetchone()

        if existing_user:
            flash('Username or email already exists!', 'error')
            conn.close()
            return redirect(url_for('customer_register'))

        hashed_password = generate_password_hash(password)
        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        conn.execute('''
            INSERT INTO users (username, email, password, full_name, role, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (username, email, hashed_password, full_name, 'customer', created_at))

        conn.commit()
        conn.close()

        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('customer_login'))

    return render_template('customer_register.html')


# CUSTOMER LOGIN
@app.route('/customer/login', methods=['GET', 'POST'])
def customer_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ? AND role = "customer"',
                            (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['full_name'] = user['full_name']
            session['role'] = user['role']

            flash(f'Welcome, {user["full_name"]}!', 'success')
            return redirect(url_for('customer_dashboard'))
        else:
            flash('Invalid username or password!', 'error')
            return redirect(url_for('customer_login'))

    return render_template('customer_login.html')


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

    rides = conn.execute('SELECT * FROM rides ORDER BY type, name').fetchall()
    all_bookings = conn.execute('SELECT * FROM bookings ORDER BY id DESC').fetchall()

    total_rides = len(rides)
    total_bookings = len(all_bookings)
    unused_tickets = len([b for b in all_bookings if b['status'] == 'unused'])
    used_tickets = len([b for b in all_bookings if b['status'] == 'used'])
    total_revenue = sum([b['total_price'] for b in all_bookings])

    # Daily revenue (today)
    today = datetime.now().strftime('%Y-%m-%d')
    daily_bookings = [b for b in all_bookings if b['booking_time'].startswith(today)]
    daily_revenue = sum([b['total_price'] for b in daily_bookings])

    # Monthly revenue
    current_month = datetime.now().strftime('%Y-%m')
    monthly_bookings = [b for b in all_bookings if b['booking_time'].startswith(current_month)]
    monthly_revenue = sum([b['total_price'] for b in monthly_bookings])

    # Yearly revenue
    current_year = datetime.now().strftime('%Y')
    yearly_bookings = [b for b in all_bookings if b['booking_time'].startswith(current_year)]
    yearly_revenue = sum([b['total_price'] for b in yearly_bookings])

    # Best selling rides
    ride_sales = {}
    for booking in all_bookings:
        items = conn.execute('SELECT * FROM booking_items WHERE booking_id = ?',
                             (booking['id'],)).fetchall()
        for item in items:
            if item['ride_name'] not in ride_sales:
                ride_sales[item['ride_name']] = 0
            ride_sales[item['ride_name']] += item['quantity']

    best_rides = sorted(ride_sales.items(), key=lambda x: x[1], reverse=True)[:5]

    conn.close()

    return render_template('admin_dashboard.html',
                           rides=rides,
                           total_rides=total_rides,
                           total_bookings=total_bookings,
                           unused_tickets=unused_tickets,
                           used_tickets=used_tickets,
                           total_revenue=total_revenue,
                           daily_bookings=len(daily_bookings),
                           daily_revenue=daily_revenue,
                           monthly_bookings=len(monthly_bookings),
                           monthly_revenue=monthly_revenue,
                           yearly_bookings=len(yearly_bookings),
                           yearly_revenue=yearly_revenue,
                           best_rides=best_rides)


@app.route('/admin/bookings')
@admin_required
def admin_bookings():
    conn = get_db_connection()
    bookings_raw = conn.execute('SELECT * FROM bookings ORDER BY id DESC').fetchall()

    bookings = []
    for booking in bookings_raw:
        items = conn.execute('SELECT * FROM booking_items WHERE booking_id = ?',
                             (booking['id'],)).fetchall()
        booking_dict = dict(booking)
        booking_dict['items'] = [dict(item) for item in items]
        bookings.append(booking_dict)

    conn.close()
    return render_template('admin_bookings.html', bookings=bookings)


@app.route('/admin/rides/add', methods=['GET', 'POST'])
@admin_required
def admin_add_ride():
    if request.method == 'POST':
        name = request.form.get('name')
        ride_type = request.form.get('type')
        price = float(request.form.get('price'))
        total_tickets = int(request.form.get('total_tickets'))
        schedule = request.form.get('schedule')

        conn = get_db_connection()
        conn.execute('''
            INSERT INTO rides (name, type, price, total_tickets, available_tickets, schedule, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (name, ride_type, price, total_tickets, total_tickets, schedule,
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
        total_tickets = int(request.form.get('total_tickets'))
        available_tickets = int(request.form.get('available_tickets'))
        schedule = request.form.get('schedule')

        conn.execute('''
            UPDATE rides 
            SET name=?, type=?, price=?, total_tickets=?, available_tickets=?, schedule=?
            WHERE id=?
        ''', (name, ride_type, price, total_tickets, available_tickets, schedule, ride_id))
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

    major_rides = [dict(ride) for ride in rides if ride['type'] == 'Major Ride']
    family_rides = [dict(ride) for ride in rides if ride['type'] == 'Family Ride']

    cashier_bookings = conn.execute('SELECT * FROM bookings WHERE user_id = ?',
                                    (session['user_id'],)).fetchall()

    total_sales = sum([b['total_price'] for b in cashier_bookings])
    total_bookings = len(cashier_bookings)

    conn.close()

    return render_template('cashier_dashboard.html',
                           major_rides=major_rides,
                           family_rides=family_rides,
                           total_sales=total_sales,
                           total_bookings=total_bookings)


@app.route('/cashier/cart')
@cashier_required
def cashier_cart():
    cart = session.get('cart', [])

    conn = get_db_connection()
    cart_items = []
    total_price = 0

    for item in cart:
        ride = conn.execute('SELECT * FROM rides WHERE id = ?', (item['ride_id'],)).fetchone()
        if ride:
            cart_item = {
                'ride_id': item['ride_id'],
                'ride_name': ride['name'],
                'price': ride['price'],
                'quantity': item['quantity'],
                'subtotal': ride['price'] * item['quantity']
            }
            cart_items.append(cart_item)
            total_price += cart_item['subtotal']

    conn.close()

    return render_template('cashier_cart.html', cart_items=cart_items, total_price=total_price)


@app.route('/cashier/add-to-cart/<int:ride_id>', methods=['POST'])
@cashier_required
def cashier_add_to_cart(ride_id):
    quantity = int(request.form.get('quantity', 1))

    conn = get_db_connection()
    ride = conn.execute('SELECT * FROM rides WHERE id = ?', (ride_id,)).fetchone()
    conn.close()

    if not ride:
        flash('Ride not found!', 'error')
        return redirect(url_for('cashier_dashboard'))

    if quantity > ride['available_tickets']:
        flash('Not enough tickets available!', 'error')
        return redirect(url_for('cashier_dashboard'))

    cart = session.get('cart', [])

    existing_item = next((item for item in cart if item['ride_id'] == ride_id), None)

    if existing_item:
        existing_item['quantity'] += quantity
    else:
        cart.append({'ride_id': ride_id, 'quantity': quantity})

    session['cart'] = cart
    flash(f'Added {quantity} ticket(s) for {ride["name"]} to cart!', 'success')
    return redirect(url_for('cashier_dashboard'))


@app.route('/cashier/remove-from-cart/<int:ride_id>')
@cashier_required
def cashier_remove_from_cart(ride_id):
    cart = session.get('cart', [])
    cart = [item for item in cart if item['ride_id'] != ride_id]
    session['cart'] = cart
    flash('Item removed from cart!', 'success')
    return redirect(url_for('cashier_cart'))


@app.route('/cashier/checkout', methods=['POST'])
@cashier_required
def cashier_checkout():
    cart = session.get('cart', [])

    if not cart:
        flash('Cart is empty!', 'error')
        return redirect(url_for('cashier_dashboard'))

    conn = get_db_connection()

    total_price = 0
    booking_items = []

    for item in cart:
        ride = conn.execute('SELECT * FROM rides WHERE id = ?', (item['ride_id'],)).fetchone()

        if not ride or item['quantity'] > ride['available_tickets']:
            flash(f'Not enough tickets for {ride["name"]}!', 'error')
            conn.close()
            return redirect(url_for('cashier_cart'))

        subtotal = ride['price'] * item['quantity']
        total_price += subtotal

        booking_items.append({
            'ride_id': ride['id'],
            'ride_name': ride['name'],
            'quantity': item['quantity'],
            'price': ride['price'],
            'subtotal': subtotal
        })

    qr_code = secrets.token_urlsafe(16)
    booking_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    cursor = conn.execute('''
        INSERT INTO bookings (user_id, user_name, user_role, booking_time, total_price, qr_code, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (session['user_id'], session['full_name'], session['role'], booking_time, total_price, qr_code, 'unused'))

    booking_id = cursor.lastrowid

    for item in booking_items:
        conn.execute('''
            INSERT INTO booking_items (booking_id, ride_id, ride_name, quantity, price, subtotal)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (booking_id, item['ride_id'], item['ride_name'], item['quantity'], item['price'], item['subtotal']))

        conn.execute('UPDATE rides SET available_tickets = available_tickets - ? WHERE id = ?',
                     (item['quantity'], item['ride_id']))

    conn.commit()
    conn.close()

    session['cart'] = []

    flash('Booking successful!', 'success')
    return redirect(url_for('view_ticket', booking_id=booking_id))


@app.route('/cashier/bookings')
@cashier_required
def cashier_bookings():
    conn = get_db_connection()
    bookings_raw = conn.execute('SELECT * FROM bookings WHERE user_id = ? ORDER BY id DESC',
                                (session['user_id'],)).fetchall()

    bookings = []
    for booking in bookings_raw:
        items = conn.execute('SELECT * FROM booking_items WHERE booking_id = ?',
                             (booking['id'],)).fetchall()
        booking_dict = dict(booking)
        booking_dict['items'] = [dict(item) for item in items]
        bookings.append(booking_dict)

    conn.close()
    return render_template('cashier_bookings.html', bookings=bookings)


# CUSTOMER ROUTES
@app.route('/customer/dashboard')
@customer_required
def customer_dashboard():
    conn = get_db_connection()
    rides = conn.execute('SELECT * FROM rides WHERE available_tickets > 0 ORDER BY type, name').fetchall()

    major_rides = [dict(ride) for ride in rides if ride['type'] == 'Major Ride']
    family_rides = [dict(ride) for ride in rides if ride['type'] == 'Family Ride']

    customer_bookings = conn.execute('SELECT * FROM bookings WHERE user_id = ?',
                                     (session['user_id'],)).fetchall()

    total_spent = sum([b['total_price'] for b in customer_bookings])
    total_bookings = len(customer_bookings)

    conn.close()

    return render_template('customer_dashboard.html',
                           major_rides=major_rides,
                           family_rides=family_rides,
                           total_spent=total_spent,
                           total_bookings=total_bookings)


@app.route('/customer/cart')
@customer_required
def customer_cart():
    cart = session.get('cart', [])

    conn = get_db_connection()
    cart_items = []
    total_price = 0

    for item in cart:
        ride = conn.execute('SELECT * FROM rides WHERE id = ?', (item['ride_id'],)).fetchone()
        if ride:
            cart_item = {
                'ride_id': item['ride_id'],
                'ride_name': ride['name'],
                'price': ride['price'],
                'quantity': item['quantity'],
                'subtotal': ride['price'] * item['quantity']
            }
            cart_items.append(cart_item)
            total_price += cart_item['subtotal']

    conn.close()

    return render_template('customer_cart.html', cart_items=cart_items, total_price=total_price)


@app.route('/customer/add-to-cart/<int:ride_id>', methods=['POST'])
@customer_required
def customer_add_to_cart(ride_id):
    quantity = int(request.form.get('quantity', 1))

    conn = get_db_connection()
    ride = conn.execute('SELECT * FROM rides WHERE id = ?', (ride_id,)).fetchone()
    conn.close()

    if not ride:
        flash('Ride not found!', 'error')
        return redirect(url_for('customer_dashboard'))

    if quantity > ride['available_tickets']:
        flash('Not enough tickets available!', 'error')
        return redirect(url_for('customer_dashboard'))

    cart = session.get('cart', [])

    existing_item = next((item for item in cart if item['ride_id'] == ride_id), None)

    if existing_item:
        existing_item['quantity'] += quantity
    else:
        cart.append({'ride_id': ride_id, 'quantity': quantity})

    session['cart'] = cart
    flash(f'Added {quantity} ticket(s) for {ride["name"]} to cart!', 'success')
    return redirect(url_for('customer_dashboard'))


@app.route('/customer/remove-from-cart/<int:ride_id>')
@customer_required
def customer_remove_from_cart(ride_id):
    cart = session.get('cart', [])
    cart = [item for item in cart if item['ride_id'] != ride_id]
    session['cart'] = cart
    flash('Item removed from cart!', 'success')
    return redirect(url_for('customer_cart'))


@app.route('/customer/checkout', methods=['POST'])
@customer_required
def customer_checkout():
    cart = session.get('cart', [])

    if not cart:
        flash('Cart is empty!', 'error')
        return redirect(url_for('customer_dashboard'))

    conn = get_db_connection()

    total_price = 0
    booking_items = []

    for item in cart:
        ride = conn.execute('SELECT * FROM rides WHERE id = ?', (item['ride_id'],)).fetchone()

        if not ride or item['quantity'] > ride['available_tickets']:
            flash(f'Not enough tickets for {ride["name"]}!', 'error')
            conn.close()
            return redirect(url_for('customer_cart'))

        subtotal = ride['price'] * item['quantity']
        total_price += subtotal

        booking_items.append({
            'ride_id': ride['id'],
            'ride_name': ride['name'],
            'quantity': item['quantity'],
            'price': ride['price'],
            'subtotal': subtotal
        })

    qr_code = secrets.token_urlsafe(16)
    booking_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    cursor = conn.execute('''
        INSERT INTO bookings (user_id, user_name, user_role, booking_time, total_price, qr_code, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (session['user_id'], session['full_name'], session['role'], booking_time, total_price, qr_code, 'unused'))

    booking_id = cursor.lastrowid

    for item in booking_items:
        conn.execute('''
            INSERT INTO booking_items (booking_id, ride_id, ride_name, quantity, price, subtotal)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (booking_id, item['ride_id'], item['ride_name'], item['quantity'], item['price'], item['subtotal']))

        conn.execute('UPDATE rides SET available_tickets = available_tickets - ? WHERE id = ?',
                     (item['quantity'], item['ride_id']))

    conn.commit()
    conn.close()

    session['cart'] = []

    flash('Booking successful!', 'success')
    return redirect(url_for('view_ticket', booking_id=booking_id))


@app.route('/customer/bookings')
@customer_required
def customer_bookings():
    conn = get_db_connection()
    bookings_raw = conn.execute('SELECT * FROM bookings WHERE user_id = ? ORDER BY id DESC',
                                (session['user_id'],)).fetchall()

    bookings = []
    for booking in bookings_raw:
        items = conn.execute('SELECT * FROM booking_items WHERE booking_id = ?',
                             (booking['id'],)).fetchall()
        booking_dict = dict(booking)
        booking_dict['items'] = [dict(item) for item in items]
        bookings.append(booking_dict)

    conn.close()
    return render_template('customer_bookings.html', bookings=bookings)


# TICKET & SCAN ROUTES
@app.route('/ticket/<int:booking_id>')
@login_required
def view_ticket(booking_id):
    conn = get_db_connection()
    booking = conn.execute('SELECT * FROM bookings WHERE id = ?', (booking_id,)).fetchone()

    if not booking:
        flash('Ticket not found!', 'error')
        conn.close()
        return redirect(url_for('home'))

    items = conn.execute('SELECT * FROM booking_items WHERE booking_id = ?', (booking_id,)).fetchall()
    conn.close()

    qr_data = f"BOOKING-{booking['id']}-{booking['qr_code']}"
    qr_code_img = generate_qr_code(qr_data)

    return render_template('ticket.html', booking=dict(booking), items=[dict(item) for item in items],
                           qr_code=qr_code_img)


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

        used_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute('UPDATE bookings SET status = ?, used_time = ? WHERE id = ?',
                     ('used', used_time, booking['id']))
        conn.commit()
        conn.close()

        flash(f'Ticket validated successfully! Booking #{booking["id"]} - {booking["user_name"]}', 'success')
        return redirect(url_for('scan_ticket'))

    return render_template('scan_ticket.html')


if __name__ == '__main__':
    app.run(debug=True)