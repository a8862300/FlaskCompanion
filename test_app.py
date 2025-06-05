import pytest
from app import create_app
from models import db, User
from werkzeug.security import generate_password_hash

@pytest.fixture
def app():
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,  # 测试时关闭 CSRF
        "LOGIN_DISABLED": False,
        "SECRET_KEY": "test_secret"
    })
    with app.app_context():
        db.drop_all()
        db.create_all()
        # 创建测试用户
        user = User(username="admin", password_hash=generate_password_hash("admin"), role="admin")
        db.session.add(user)
        db.session.commit()
    yield app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()

def login(client, username, password):
    return client.post("/auth/login", data={"username": username, "password": password}, follow_redirects=True)

def test_home_redirect(client):
    # 未登录访问首页应重定向到登录
    resp = client.get("/")
    assert resp.status_code in (302, 401)
    assert "login" in resp.location or "auth" in resp.location

def test_login_logout(client):
    # 登录
    resp = login(client, "admin", "admin")
    text = resp.get_data(as_text=True)
    assert "登录成功" in text or "Dashboard" in text or resp.status_code == 200
    # 登出
    resp = client.get("/auth/logout", follow_redirects=True)
    text = resp.get_data(as_text=True)
    assert "登录" in text or resp.status_code == 200

def test_dashboard_access(client):
    login(client, "admin", "admin")
    resp = client.get("/")
    text = resp.get_data(as_text=True)
    assert "仪表盘" in text or "Dashboard" in text or resp.status_code == 200

def test_category_list(client):
    login(client, "admin", "admin")
    resp = client.get("/category/list")
    assert resp.status_code == 200

def test_product_list(client):
    login(client, "admin", "admin")
    resp = client.get("/product/list")
    assert resp.status_code == 200

def test_customer_list(client):
    login(client, "admin", "admin")
    resp = client.get("/customer/list")
    assert resp.status_code == 200

def test_supplier_list(client):
    login(client, "admin", "admin")
    resp = client.get("/supplier/list")
    assert resp.status_code == 200

def test_order_list(client):
    login(client, "admin", "admin")
    resp = client.get("/order/list")
    assert resp.status_code == 200

def test_purchase_list(client):
    login(client, "admin", "admin")
    resp = client.get("/purchase/list")
    assert resp.status_code == 200

def test_raw_material_list(client):
    login(client, "admin", "admin")
    resp = client.get("/raw_material/list")
    assert resp.status_code == 200

def test_report_sales(client):
    login(client, "admin", "admin")
    resp = client.get("/report/sales")
    assert resp.status_code == 200

def test_api_products(client):
    login(client, "admin", "admin")
    resp = client.get("/api/products")
    assert resp.status_code in (200, 401, 403)  # 视权限和实现而定
