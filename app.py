import os
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'super-secret-key-change-me')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///devices.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ------------------------------------------------------------------------------
# Database Model
# ------------------------------------------------------------------------------
class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(100), unique=True, nullable=False)
    status = db.Column(db.String(20), default='active')  # active or banned
    added_on = db.Column(db.DateTime, server_default=db.func.now())

    def __repr__(self):
        return f'<Device {self.device_id} ({self.status})>'

# Hardcoded admin credentials (change via environment variables)
ADMIN_USER = os.environ.get('ADMIN_USER', 'admin')
ADMIN_PASS = os.environ.get('ADMIN_PASS', 'admin123')

# ------------------------------------------------------------------------------
# Login / Logout logic
# ------------------------------------------------------------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USER and password == ADMIN_PASS:
            session['logged_in'] = True
            flash('Welcome back, Admin!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# ------------------------------------------------------------------------------
# API for the CodeHax loader
# ------------------------------------------------------------------------------
@app.route('/api/check_device', methods=['POST'])
def check_device():
    data = request.get_json()
    if not data or 'device_id' not in data:
        return jsonify({"error": "Missing device_id"}), 400

    device_id = data['device_id'].strip()
    if not device_id:
        return jsonify({"error": "Empty device_id"}), 400

    device = Device.query.filter_by(device_id=device_id).first()
    if device and device.status == 'active':
        return jsonify({"access": True})
    else:
        # If device not found OR banned -> access denied
        return jsonify({"access": False})

# ------------------------------------------------------------------------------
# Dashboard and device management
# ------------------------------------------------------------------------------
@app.route('/')
@login_required
def dashboard():
    devices = Device.query.order_by(Device.added_on.desc()).all()
    return render_template('dashboard.html', devices=devices)

@app.route('/add', methods=['POST'])
@login_required
def add_device():
    device_id = request.form.get('device_id', '').strip()
    if not device_id:
        flash('Device ID cannot be empty', 'danger')
        return redirect(url_for('dashboard'))

    existing = Device.query.filter_by(device_id=device_id).first()
    if existing:
        flash('Device ID already exists', 'warning')
        return redirect(url_for('dashboard'))

    new_device = Device(device_id=device_id, status='active')
    db.session.add(new_device)
    db.session.commit()
    flash(f'Device {device_id} added (active)', 'success')
    return redirect(url_for('dashboard'))

@app.route('/ban/<int:device_id>')
@login_required
def ban_device(device_id):
    device = Device.query.get_or_404(device_id)
    if device.status != 'banned':
        device.status = 'banned'
        db.session.commit()
        flash(f'Device {device.device_id} has been banned.', 'warning')
    else:
        flash('Device is already banned.', 'info')
    return redirect(url_for('dashboard'))

@app.route('/unban/<int:device_id>')
@login_required
def unban_device(device_id):
    device = Device.query.get_or_404(device_id)
    if device.status == 'banned':
        device.status = 'active'
        db.session.commit()
        flash(f'Device {device.device_id} is now active again.', 'success')
    else:
        flash('Device was not banned.', 'info')
    return redirect(url_for('dashboard'))

@app.route('/delete/<int:device_id>')
@login_required
def delete_device(device_id):
    device = Device.query.get_or_404(device_id)
    db.session.delete(device)
    db.session.commit()
    flash(f'Device {device.device_id} permanently removed.', 'danger')
    return redirect(url_for('dashboard'))

# ------------------------------------------------------------------------------
# Create tables
# ------------------------------------------------------------------------------
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
