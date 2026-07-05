# Snip - URL Shortener

A full-stack URL shortening application built with Flask, featuring user authentication, click analytics, QR code generation, and bulk URL processing.

## Features

- User authentication with hashed passwords (register/login/logout)
- Custom short codes or auto-generated codes
- Link expiry (set URLs to expire after N days)
- QR code generation for each shortened link
- Detailed click analytics (total, today, this week, last accessed)
- Top 5 most visited URLs
- Interactive charts (bar chart, 7-day trend line chart)
- Bulk URL shortening via CSV upload
- Rate limiting to prevent abuse
- Basic URL safety checks
- Delete links

## Tech Stack

- **Backend:** Flask, Flask-SQLAlchemy, Flask-Login
- **Database:** MySQL
- **Frontend:** HTML, Jinja2, CSS, JavaScript
- **Charts:** Chart.js
- **QR Codes:** QRCode.js
- **Testing:** Pytest (11 tests covering auth, CRUD, redirects, expiry)
- **Security:** Werkzeug password hashing, Flask-Limiter rate limiting, environment-based secrets

## Setup

1. Clone the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate it: `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Mac/Linux)
4. Install dependencies: `pip install -r requirements.txt`
5. Create a `.env` file with:
SECRET_KEY=your-secret-key
DATABASE_URL=mysql+pymysql://username:password@localhost/url_shortener
6. Create the MySQL database: `CREATE DATABASE url_shortener;`
7. Run the app: `python app.py`

## Running Tests

```bash
pytest test_app.py -v
```

## Project Structure
snip-url-shortener/
├── app.py
├── models.py
├── conftest.py
├── test_app.py
├── requirements.txt
├── templates/
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   └── dashboard.html
└── static/
└── style.css