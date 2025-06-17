# FareFlow: Automated Parking Management System

![FareFlow Logo](static/images/logo.png)

## Table of Contents

1. [Project Overview](#project-overview)
2. [Features](#features)
3. [Architecture & Workflow](#architecture--workflow)
4. [Tech Stack](#tech-stack)
5. [Prerequisites](#prerequisites)
6. [Installation & Setup](#installation--setup)

   * [Clone the Repository](#clone-the-repository)
   * [Python Environment](#python-environment)
   * [Configuration](#configuration)
   * [Database Initialization](#database-initialization)
7. [Running the Application](#running-the-application)
8. [Usage](#usage)
9. [Folder Structure](#folder-structure)
10. [Contributing](#contributing)
11. [License](#license)

---

## Project Overview

FareFlow is a web-based, automated parking management system that leverages license plate recognition (LPR) and dynamic fare calculation to streamline vehicle entry and exit. Built with Flask and an ESP32-CAM for image capture, FareFlow provides separate dashboards for admins and users, ensuring secure, role-based access and detailed audit logs.

---

## Features

* **Automated License Plate Recognition** via Plate Recognizer API
* **Dynamic Fare Calculation** at ₹1 per minute
* **User Authentication & Authorization** with Flask-Login
* **Admin PIN Verification** for enhanced security
* **Real-Time Video Stream** from ESP32-CAM module
* **Dual Dashboards**:

  * **Admin Dashboard**: live feed control, view all entries/users, audit logs
  * **User Dashboard**: view personal parking history and ongoing session fares
* **RESTful Data Endpoints** for JSON integration

---

## Architecture & Workflow

1. **User Authentication**: Users register and login; role (`admin` or `user`) is determined.
2. **Admin Access**: Admins verify a PIN post-login, then access the live camera feed.
3. **Image Capture**: Admin triggers ESP32-CAM to capture an image via HTTP.
4. **Plate Recognition**: Captured images are sent to Plate Recognizer API; returned text is cross-checked against SQLite database.
5. **Fare Logic**:

   * **Entry**: First detection → fare = 0
   * **Exit**: Second detection → compute time difference × ₹1/min
6. **Data Persistence**: Transactions (image path, plate number, timestamp, fare) stored in SQLite.
7. **Dashboards & APIs**: Data surfaced via Flask templates and JSON endpoints.

---

## Tech Stack

* **Backend**: Python, Flask, Flask-Login, SQLite
* **Frontend**: HTML5, CSS3, JavaScript, Jinja2 templates
* **Hardware**: ESP32-CAM module
* **APIs**: Plate Recognizer (OCR)
* **Libraries**: OpenCV, NumPy, Requests

---

## Prerequisites

* Python 3.8+
* pip (package installer)
* ESP32-CAM connected to the same network
* Plate Recognizer API key (sign up at [https://platerecognizer.com](https://platerecognizer.com))

---

## Installation & Setup

### Clone the Repository

```bash
git clone https://github.com/<your-username>/FareFlow.git
cd FareFlow
```

### Python Environment

```bash
python -m venv venv
source venv/bin/activate        # On Windows: venv\\Scripts\\activate
pip install -r requirements.txt
```

### Configuration

1. Copy the example config:

   ```bash
   cp config.example.py config.py
   ```
2. Open `config.py` and fill in:

   ```python
   # config.py
   SECRET_KEY = 'your_flask_secret'
   PLATE_RECOGNIZER_API_KEY = 'your_plate_recognizer_key'
   ESP32_CAM_URL = 'http://<ESP32_CAM_IP>'
   DATABASE_PATH = 'instance/number_plates.db'
   ```

### Database Initialization

You can initialize the SQLite database in two ways:

1. **Using the SQL dump**:

   ```bash
   sqlite3 instance/number_plates.db < dump.sql
   ```
2. **Using the Flask helper**:

   ```bash
   python app.py init_db
   ```

---

## Running the Application

```bash
export FLASK_APP=app.py
export FLASK_ENV=development     # enables debug mode
flask run --host=0.0.0.0 --port=5000
```

Visit `http://localhost:5000` in your browser.

---

## Usage

1. **Signup/Login** as a user or admin.
2. **Admin Workflow**:

   * Verify PIN
   * Trigger image capture and monitor live feed
   * View all entries and users
3. **User Workflow**:

   * View parking history and current session fare

---

## Folder Structure

```
FareFlow/
├── app.py                # Main Flask application
├── db_view.py            # Optional database inspection scripts
├── ocr.py                # OCR helper (Plate Recognizer integration)
├── requirements.txt      # Python dependencies
├── dump.sql              # SQL schema dump
├── config.example.py     # Example configuration file
├── instance/             # Runtime config & database (ignored by Git)
│   └── number_plates.db  # SQLite DB (do not commit)
├── static/               # Static assets (CSS, JS, images)
└── templates/            # Jinja2 HTML templates
    ├── login.html
    ├── signup.html
    ├── user_dashboard.html
    ├── admin_dashboard.html
    └── ...
```

---

## Contributing

1. Fork this repository
2. Create a feature branch (`git checkout -b feature/YourFeature`)
3. Commit your changes (`git commit -m 'Add your feature'`)
4. Push to the branch (`git push origin feature/YourFeature`)
5. Open a Pull Request

Please ensure code quality, add tests, and update documentation as needed.

---

## License

This project is licensed under the [MIT License](LICENSE).
