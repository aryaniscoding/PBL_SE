from functools import wraps  # Import wraps for decorators
from flask import Flask, render_template, Response, request, jsonify, redirect, url_for, flash, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import cv2
import urllib.request
import numpy as np
import time
import sqlite3
import requests
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = '123'  # Replace with a strong secret key

# ESP32-CAM URL (Update to your ESP32-CAM IP)
ESP32_CAM_URL = "http://192.168.37.158"

# Plate Recognizer API Key
PLATE_RECOGNIZER_API_KEY = "xxx"
PLATE_RECOGNIZER_URL = "https://api.platerecognizer.com/v1/plate-reader/"

# Database setup
DB_FILE = "number_plates.db"

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Database initialization
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            plate_number TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS number_plates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_path TEXT,
            plate_number TEXT,
            timestamp TEXT,
            fare REAL
        )
    ''')
    conn.commit()
    conn.close()

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, id, username, role, plate_number):
        self.id = id
        self.username = username
        self.role = role
        self.plate_number = plate_number

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, role, plate_number FROM users WHERE id = ?", (user_id,))
    user_data = cursor.fetchone()
    conn.close()
    if user_data:
        return User(*user_data)
    return None

# Define the @admin_required decorator
def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if current_user.role != 'admin' or not session.get('pin_verified'):
            return redirect(url_for('verify_pin'))
        return view(*args, **kwargs)
    return wrapped_view

# Routes
@app.route('/')
def home():
    return redirect(url_for('login'))
# Add these routes with your existing routes in app.py

@app.route('/about_us')
def about_us():
    return render_template('about_us.html')

@app.route('/about_website')
def about_website():
    return render_template('about_website.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user_data = cursor.fetchone()
        conn.close()
        
        if user_data and check_password_hash(user_data[2], password):
            user = User(id=user_data[0], username=user_data[1], role=user_data[3], plate_number=user_data[4])
            login_user(user)
            if user.role == 'admin':
                session['pin_verified'] = False  # Require PIN verification
                return redirect(url_for('verify_pin'))
            return redirect(url_for('user_dashboard'))
        return "Invalid credentials"
    return render_template('login.html')

# New PIN Verification Route
@app.route('/admin/verify_pin', methods=['GET', 'POST'])
@login_required
def verify_pin():
    if current_user.role != 'admin':
        return redirect(url_for('user_dashboard'))
    
    if request.method == 'POST':
        if request.form.get('pin') == app.secret_key:
            session['pin_verified'] = True
            return redirect(url_for('admin_dashboard'))
        flash('Invalid PIN. Please try again.')
    return render_template('verify_pin.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        role = request.form['role']
        plate_number = request.form.get('plate_number', None)
        
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (username, password_hash, role, plate_number) VALUES (?, ?, ?, ?)",
                (username, password, role, plate_number)
            )
            conn.commit()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return "Username exists"
        finally:
            conn.close()
    return render_template('signup.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.pop('pin_verified', None)  # Clear PIN verification status
    return redirect(url_for('login'))

# Admin Dashboard
@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    return render_template('admin_dashboard.html')

# User Dashboard
@app.route('/user/dashboard')
@login_required
def user_dashboard():
    if current_user.role != 'user':
        return "Unauthorized", 403
    return render_template('user_dashboard.html', plate_number=current_user.plate_number)

# Video feed
@app.route('/video_feed')
@login_required
def video_feed():
    def generate_frames():
        while True:
            img_resp = urllib.request.urlopen(f"{ESP32_CAM_URL}/capture")
            img_array = np.array(bytearray(img_resp.read()), dtype=np.uint8)
            frame = cv2.imdecode(img_array, -1)
            _, buffer = cv2.imencode('.jpg', frame)
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# Capture image
@app.route('/capture', methods=['POST'])
@login_required
@admin_required
def capture():
    try:
        # Capture frame from ESP32-CAM
        frame = capture_frame()
        if frame is None:
            return jsonify({'error': 'Failed to capture image from ESP32-CAM'}), 500

        # Save the captured image
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        filename = f"captured_{int(time.time())}.jpg"
        filepath = os.path.join("static", filename)
        cv2.imwrite(filepath, frame)
        print(f"Image saved at: {filepath}")

        # Recognize the license plate
        plate_text = recognize_plate(filepath)
        if plate_text == "Not Detected":
            return jsonify({'error': 'License plate not detected'}), 400

        # Normalize plate number (uppercase and trim)
        plate_text = plate_text.strip().upper()
        print(f"Detected plate: {plate_text}")

        # Calculate fare based on session logic
        fare = calculate_fare(plate_text, timestamp)
        print(f"Calculated fare: {fare}")

        # Update the database
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO number_plates (image_path, plate_number, timestamp, fare) VALUES (?, ?, ?, ?)",
            (f"/static/{filename}", plate_text, timestamp, fare)  # Store the correct path
        )
        conn.commit()
        conn.close()
        print("Database updated successfully")

        # Return the response
        return jsonify({
            'image': f"/static/{filename}",  # Return the correct path
            'plate': plate_text,
            'timestamp': timestamp,
            'fare': fare
        })
    except Exception as e:
        print(f"Error in /capture route: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# Helper functions
def capture_frame():
    img_resp = urllib.request.urlopen(f"{ESP32_CAM_URL}/capture")
    img_array = np.array(bytearray(img_resp.read()), dtype=np.uint8)
    return cv2.imdecode(img_array, -1)

def recognize_plate(image_path):
    with open(image_path, 'rb') as f:
        response = requests.post(
            PLATE_RECOGNIZER_URL,
            files={'upload': f},
            headers={'Authorization': f'Token {PLATE_RECOGNIZER_API_KEY}'}
        )
    if response.status_code in [200, 201] and response.json().get('results'):
        return response.json()['results'][0]['plate'].upper()
    return "Not Detected"

def calculate_fare(plate_number, current_timestamp):
    """
    Fare Logic:
    - If no previous record exists for the plate, treat this as an entry (fare = 0).
    - If the last record for this plate has fare == 0, it means the car is exiting;
      calculate fare as time difference (in minutes * 20 units).
    - If the last record has a non-zero fare, the previous session is complete;
      treat this as a new entry (fare = 0).
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT timestamp, fare FROM number_plates WHERE plate_number = ? ORDER BY id DESC LIMIT 1",
        (plate_number,)
    )
    result = cursor.fetchone()
    conn.close()
    
    current_time = datetime.strptime(current_timestamp, "%Y-%m-%d %H:%M:%S")
    
    if not result:
        # No previous record: car entering -> fare = 0
        return 0
    
    previous_time_str, previous_fare = result
    previous_time = datetime.strptime(previous_time_str, "%Y-%m-%d %H:%M:%S")
    
    if previous_fare == 0:
        # Last record indicates the car entered earlier; now it's exiting. Calculate fare.
        minutes = (current_time - previous_time).total_seconds() / 60
        fare = round(minutes * 0.5, 2)
        return fare
    else:
        # Last record was an exit event; this is a new entry.
        return 0

# Data endpoints
@app.route('/user/data')
@login_required
def user_data():
    if current_user.role != 'user' or not current_user.plate_number:
        return "Unauthorized", 403
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT image_path, timestamp, fare FROM number_plates WHERE plate_number = ? ORDER BY timestamp DESC",
        (current_user.plate_number,)
    )
    data = [{'image': row[0], 'timestamp': row[1], 'fare': row[2]} for row in cursor.fetchall()]
    conn.close()
    return jsonify(data)

@app.route('/get_data')
@login_required
@admin_required
def get_data():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT image_path, plate_number, timestamp, fare FROM number_plates ORDER BY id DESC")
    data = [dict(zip(['image', 'plate', 'timestamp', 'fare'], row)) for row in cursor.fetchall()]
    conn.close()
    return jsonify(data)

@app.route('/view_entries')
@login_required
@admin_required
def view_entries():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM number_plates ORDER BY timestamp DESC")
    entries = cursor.fetchall()
    conn.close()
    return render_template('view_entries.html', entries=entries)

@app.route('/view_users')
@login_required
@admin_required
def view_users():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users ORDER BY id DESC")
    users = cursor.fetchall()
    conn.close()
    return render_template('view_users.html', users=users)

if __name__ == "__main__":
    init_db()  # Ensure the database tables are created
    app.run(host='0.0.0.0', port=5000, debug=True)
