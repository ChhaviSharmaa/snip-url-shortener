import os
import csv
import io
import string
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from sqlalchemy import func
from models import db, User, URL, Visit

load_dotenv()

app = Flask(__name__)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')

# Render.
database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url

app.config['RATELIMIT_ENABLED'] = os.environ.get('TESTING') != 'true'

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists!')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password_hash=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash('Registered successfully! Please login.')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password!')
            return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route('/dashboard')
@login_required
def dashboard():
    links = URL.query.filter_by(user_id=current_user.id).order_by(URL.created_at.desc()).all()

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())

    analytics = {}
    for link in links:
        clicks_today = Visit.query.filter(
            Visit.url_id == link.id,
            Visit.visited_at >= today_start
        ).count()

        clicks_week = Visit.query.filter(
            Visit.url_id == link.id,
            Visit.visited_at >= week_start
        ).count()

        last_visit = Visit.query.filter_by(url_id=link.id).order_by(Visit.visited_at.desc()).first()
        last_accessed = last_visit.visited_at if last_visit else None

        analytics[link.id] = {
            'today': clicks_today,
            'week': clicks_week,
            'last_accessed': last_accessed
        }

    top_urls = URL.query.filter_by(user_id=current_user.id).order_by(URL.click_count.desc()).limit(5).all()

    chart_labels = [url.short_code for url in top_urls]
    chart_data = [url.click_count for url in top_urls]

    last_7_days_labels = []
    last_7_days_counts = []

    for i in range(6, -1, -1):
        day = today_start - timedelta(days=i)
        next_day = day + timedelta(days=1)

        count = Visit.query.join(URL).filter(
            URL.user_id == current_user.id,
            Visit.visited_at >= day,
            Visit.visited_at < next_day
        ).count()

        last_7_days_labels.append(day.strftime('%d-%m'))
        last_7_days_counts.append(count)

    return render_template(
        'dashboard.html',
        links=links,
        analytics=analytics,
        top_urls=top_urls,
        chart_labels=chart_labels,
        chart_data=chart_data,
        last_7_days_labels=last_7_days_labels,
        last_7_days_counts=last_7_days_counts
    )


def is_safe_url(url):
    """Basic keyword-based check to block obviously malicious URLs."""
    suspicious_keywords = ['phishing', 'malware', 'virus', 'hack', 'scam']
    url_lower = url.lower()

    for keyword in suspicious_keywords:
        if keyword in url_lower:
            return False

    return True


def generate_short_code(length=6):
    """Generate a random alphanumeric short code, retrying on collision."""
    characters = string.ascii_letters + string.digits
    while True:
        code = ''.join(random.choice(characters) for _ in range(length))
        existing = URL.query.filter_by(short_code=code).first()
        if not existing:
            return code


@app.route('/shorten', methods=['POST'])
@login_required
@limiter.limit("10 per minute")
def shorten():
    original_url = request.form['original_url']

    if not is_safe_url(original_url):
        flash('This URL appears unsafe and cannot be shortened!')
        return redirect(url_for('dashboard'))

    custom_code = request.form.get('custom_code')
    expiry_days = request.form.get('expiry_days')

    if custom_code:
        existing = URL.query.filter_by(short_code=custom_code).first()
        if existing:
            flash('This custom code is already taken! Try another.')
            return redirect(url_for('dashboard'))
        short_code = custom_code
    else:
        short_code = generate_short_code()

    expires_at = None
    if expiry_days:
        expires_at = datetime.utcnow() + timedelta(days=int(expiry_days))

    new_url = URL(
        short_code=short_code,
        original_url=original_url,
        user_id=current_user.id,
        expires_at=expires_at
    )
    db.session.add(new_url)
    db.session.commit()

    flash(f'Short URL created: {short_code}')
    return redirect(url_for('dashboard'))


@app.route('/bulk-upload', methods=['POST'])
@login_required
def bulk_upload():
    file = request.files.get('csv_file')

    if not file or file.filename == '':
        flash('No file selected!')
        return redirect(url_for('dashboard'))

    if not file.filename.endswith('.csv'):
        flash('Please upload a valid CSV file!')
        return redirect(url_for('dashboard'))

    raw_data = file.stream.read()
    try:
        decoded_data = raw_data.decode("utf-8-sig")
    except UnicodeDecodeError:
        decoded_data = raw_data.decode("utf-8")

    stream = io.StringIO(decoded_data, newline=None)
    csv_reader = csv.DictReader(stream)

    success_count = 0
    fail_count = 0

    for row in csv_reader:
        original_url = row.get('url', '').strip()

        if not original_url:
            fail_count += 1
            continue

        if not is_safe_url(original_url):
            fail_count += 1
            continue

        custom_code = row.get('custom_code', '').strip()

        if custom_code:
            existing = URL.query.filter_by(short_code=custom_code).first()
            if existing:
                fail_count += 1
                continue
            short_code = custom_code
        else:
            short_code = generate_short_code()

        new_url = URL(
            short_code=short_code,
            original_url=original_url,
            user_id=current_user.id
        )
        db.session.add(new_url)
        success_count += 1

    db.session.commit()
    flash(f'{success_count} URLs created successfully! {fail_count} failed.')
    return redirect(url_for('dashboard'))


@app.route('/delete/<int:url_id>', methods=['POST'])
@login_required
def delete_url(url_id):
    url_entry = URL.query.get(url_id)

    if url_entry and url_entry.user_id == current_user.id:
        db.session.delete(url_entry)
        db.session.commit()
        flash('URL deleted successfully!')
    else:
        flash('URL not found or unauthorized!')

    return redirect(url_for('dashboard'))


@app.route('/<short_code>')
def redirect_to_url(short_code):
    url_entry = URL.query.filter_by(short_code=short_code).first()

    if url_entry:
        if url_entry.expires_at and datetime.utcnow() > url_entry.expires_at:
            return "This link has expired!", 410

        url_entry.click_count += 1

        new_visit = Visit(url_id=url_entry.id)
        db.session.add(new_visit)

        db.session.commit()
        return redirect(url_entry.original_url)
    else:
        return "URL not found!", 404


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)