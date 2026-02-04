from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'carnival_secret_key_2024'

# Carnival Rides Data (temporary storage, no database yet)
rides_data = {
    'major_rides': [
        {
            'id': 1,
            'name': 'Dragon Coaster',
            'type': 'Major Ride',
            'price': 150,
            'available_tickets': 50,
            'schedule': '10:00 AM - 8:00 PM',
            'age_limit': '12+',
            'height_limit': '4.5 ft minimum'
        },
        {
            'id': 2,
            'name': 'Viking Ship',
            'type': 'Major Ride',
            'price': 120,
            'available_tickets': 40,
            'schedule': '10:30 AM - 7:30 PM',
            'age_limit': '10+',
            'height_limit': '4 ft minimum'
        },
        {
            'id': 3,
            'name': 'Ferris Wheel',
            'type': 'Major Ride',
            'price': 100,
            'available_tickets': 60,
            'schedule': '9:00 AM - 9:00 PM',
            'age_limit': 'All ages',
            'height_limit': 'No limit'
        }
    ],
    'family_rides': [
        {
            'id': 4,
            'name': 'Carousel',
            'type': 'Family Ride',
            'price': 50,
            'available_tickets': 80,
            'schedule': '9:00 AM - 8:00 PM',
            'age_limit': 'All ages',
            'height_limit': 'No limit'
        },
        {
            'id': 5,
            'name': 'Tea Cups',
            'type': 'Family Ride',
            'price': 60,
            'available_tickets': 70,
            'schedule': '10:00 AM - 7:00 PM',
            'age_limit': '5+',
            'height_limit': '3 ft minimum'
        },
        {
            'id': 6,
            'name': 'Mini Train',
            'type': 'Family Ride',
            'price': 40,
            'available_tickets': 100,
            'schedule': '9:30 AM - 8:30 PM',
            'age_limit': 'All ages',
            'height_limit': 'No limit'
        }
    ]
}

# Bookings storage
bookings = []


@app.route('/')
def dashboard():
    # Calculate statistics
    total_rides = len(rides_data['major_rides']) + len(rides_data['family_rides'])
    total_tickets_available = sum(
        ride['available_tickets'] for ride in rides_data['major_rides'] + rides_data['family_rides'])
    total_bookings = len(bookings)

    return render_template('dashboard.html',
                           major_rides=rides_data['major_rides'],
                           family_rides=rides_data['family_rides'],
                           total_rides=total_rides,
                           total_tickets=total_tickets_available,
                           total_bookings=total_bookings)


@app.route('/book/<int:ride_id>', methods=['GET', 'POST'])
def book_ticket(ride_id):
    # Find the ride
    ride = None
    for r in rides_data['major_rides'] + rides_data['family_rides']:
        if r['id'] == ride_id:
            ride = r
            break

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

        # Create booking
        booking = {
            'id': len(bookings) + 1,
            'name': name,
            'age': age,
            'ride_name': ride['name'],
            'quantity': quantity,
            'total_price': ride['price'] * quantity,
            'booking_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        bookings.append(booking)
        ride['available_tickets'] -= quantity

        flash(f'Successfully booked {quantity} ticket(s) for {ride["name"]}!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('book.html', ride=ride)


@app.route('/bookings')
def view_bookings():
    return render_template('bookings.html', bookings=bookings)


if __name__ == '__main__':
    app.run(debug=True)