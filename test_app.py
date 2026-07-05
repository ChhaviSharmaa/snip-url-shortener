def register_and_login(client, username='testuser', password='testpass123'):
    """Helper to register and log in a user, reused across multiple tests."""
    client.post('/register', data={'username': username, 'password': password})
    client.post('/login', data={'username': username, 'password': password})


def test_register(client):
    response = client.post('/register', data={
        'username': 'testuser',
        'password': 'testpass123'
    }, follow_redirects=True)
    assert response.status_code == 200


def test_register_duplicate_username(client):
    client.post('/register', data={'username': 'testuser', 'password': 'testpass123'})
    response = client.post('/register', data={
        'username': 'testuser',
        'password': 'anotherpass'
    }, follow_redirects=True)
    assert b'Username already exists' in response.data


def test_login_success(client):
    client.post('/register', data={'username': 'testuser', 'password': 'testpass123'})
    response = client.post('/login', data={
        'username': 'testuser',
        'password': 'testpass123'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Welcome' in response.data


def test_login_wrong_password(client):
    client.post('/register', data={'username': 'testuser', 'password': 'testpass123'})
    response = client.post('/login', data={
        'username': 'testuser',
        'password': 'wrongpass'
    }, follow_redirects=True)
    assert b'Invalid username or password' in response.data


def test_dashboard_requires_login(client):
    response = client.get('/dashboard', follow_redirects=True)
    assert b'Login' in response.data


def test_shorten_url(client):
    register_and_login(client)
    response = client.post('/shorten', data={
        'original_url': 'https://www.example.com',
        'custom_code': '',
        'expiry_days': ''
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Short URL created' in response.data


def test_shorten_with_custom_code(client):
    register_and_login(client)
    response = client.post('/shorten', data={
        'original_url': 'https://www.example.com',
        'custom_code': 'mylink123',
        'expiry_days': ''
    }, follow_redirects=True)
    assert b'mylink123' in response.data


def test_redirect_to_original_url(client):
    register_and_login(client)
    client.post('/shorten', data={
        'original_url': 'https://www.example.com',
        'custom_code': 'testcode1',
        'expiry_days': ''
    })
    response = client.get('/testcode1', follow_redirects=False)
    assert response.status_code == 302
    assert response.location == 'https://www.example.com'


def test_redirect_invalid_code(client):
    response = client.get('/nonexistentcode123')
    assert response.status_code == 404


def test_delete_url(client):
    register_and_login(client)
    client.post('/shorten', data={
        'original_url': 'https://www.example.com',
        'custom_code': 'deleteme',
        'expiry_days': ''
    })

    from models import URL
    from app import app as flask_app
    with flask_app.app_context():
        url_entry = URL.query.filter_by(short_code='deleteme').first()
        url_id = url_entry.id

    response = client.post(f'/delete/{url_id}', follow_redirects=True)
    assert b'URL deleted successfully' in response.data


def test_expired_link(client):
    register_and_login(client)
    client.post('/shorten', data={
        'original_url': 'https://www.example.com',
        'custom_code': 'expiredlink',
        'expiry_days': '1'
    })

    # Force the expiry date into the past to simulate an expired link
    from models import URL, db as models_db
    from app import app as flask_app
    from datetime import datetime, timedelta

    with flask_app.app_context():
        url_entry = URL.query.filter_by(short_code='expiredlink').first()
        url_entry.expires_at = datetime.utcnow() - timedelta(days=1)
        models_db.session.commit()

    response = client.get('/expiredlink')
    assert response.status_code == 410
    assert b'expired' in response.data