import os
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change-me-in-production!')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///devices.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ------------------------------------------------------------------------------
# Database Model (move to models.py for cleanliness, here for simplicity)
# ------------------------------------------------------------------------------
class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(100), unique=True, nullable=False)
    added_on = db.Column(db.DateTime, server_default=db.func.now())

    def __repr__(self):
        return f'<Device {self.device_id}>'

# ------------------------------------------------------------------------------
# Simple HTTP Basic Auth to protect the admin panel (optional but recommended)
# You can set USERNAME and PASSWORD in Render environment variables.
# ------------------------------------------------------------------------------
def check_auth(username, password):
    return username == os.environ.get('ADMIN_USER', 'admin') and \
           password == os.environ.get('ADMIN_PASS', 'password')

def authenticate():
    return jsonify({"error": "Authentication required"}), 401, \
           {'WWW-Authenticate': 'Basic realm="Admin Panel"'}

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

# ------------------------------------------------------------------------------
# API endpoint called by the CodeHax loader
# ------------------------------------------------------------------------------
@app.route('/api/check_device', methods=['POST'])
def check_device():
    """Check if a device ID is allowed. Expect JSON: {'device_id': '...'}"""
    data = request.get_json()
    if not data or 'device_id' not in data:
        return jsonify({"error": "Missing device_id"}), 400

    device_id = data['device_id'].strip()
    if not device_id:
        return jsonify({"error": "Empty device_id"}), 400

    # Look up the device in the database
    device = Device.query.filter_by(device_id=device_id).first()
    return jsonify({"access": device is not None})

# ------------------------------------------------------------------------------
# Admin Dashboard (protected by basic auth)
# ------------------------------------------------------------------------------
@app.route('/')
@requires_auth
def index():
    devices = Device.query.order_by(Device.added_on.desc()).all()
    return render_template('index.html', devices=devices)

@app.route('/add', methods=['POST'])
@requires_auth
def add_device():
    device_id = request.form.get('device_id', '').strip()
    if not device_id:
        flash('Device ID cannot be empty', 'danger')
        return redirect(url_for('index'))

    existing = Device.query.filter_by(device_id=device_id).first()
    if existing:
        flash('Device ID already exists', 'warning')
        return redirect(url_for('index'))

    new_device = Device(device_id=device_id)
    db.session.add(new_device)
    db.session.commit()
    flash(f'Device {device_id} added successfully', 'success')
    return redirect(url_for('index'))

@app.route('/delete/<int:device_id>')
@requires_auth
def delete_device(device_id):
    device = Device.query.get_or_404(device_id)
    db.session.delete(device)
    db.session.commit()
    flash(f'Device {device.device_id} removed', 'info')
    return redirect(url_for('index'))

# ------------------------------------------------------------------------------
# Create tables before first request (for simplicity)
# ------------------------------------------------------------------------------
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
