import os

# Point the app at an in-memory SQLite database for tests, before app.py is imported
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['TESTING'] = 'true'
os.environ.setdefault('SECRET_KEY', 'test-secret-key')

import pytest
from app import app as flask_app
from models import db


@pytest.fixture
def app():
    flask_app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
    })

    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()