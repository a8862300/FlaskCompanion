import os
import logging
from datetime import datetime
import secrets
from flask import Flask, g, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager, current_user
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_wtf.csrf import CSRFProtect, generate_csrf

logging.basicConfig(level=logging.INFO)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", secrets.token_hex(32))
app.logger.debug(f"DEBUG: Flask app.secret_key is set to: {app.secret_key}")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///inventory.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["WTF_CSRF_ENABLED"] = True
app.config["WTF_CSRF_CHECK_DEFAULT"] =True
csrf = CSRFProtect(app)
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = '请先登录'

@app.before_request
def before_request():
    g.year = datetime.now().year
    if current_user.is_authenticated:
        app.logger.debug(f"DEBUG: Session active for authenticated user: {current_user.id} ({current_user.username})")
    else:
        app.logger.debug("DEBUG: No active authenticated user session.")
    app.logger.debug(f"DEBUG: Current session content: {dict(session)}")

@app.context_processor
def inject_csrf_token():
    return dict(csrf_token=generate_csrf)

with app.app_context():
    import models
    db.create_all()
    from models import User
    from werkzeug.security import generate_password_hash
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            password_hash=generate_password_hash('admin'),
            role='admin'
        )
        db.session.add(admin)
        db.session.commit()
        app.logger.info('创建了默认管理员账户: admin/admin')

from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.customer import customer_bp
from routes.supplier import supplier_bp
from routes.category import category_bp
from routes.product import product_bp
from routes.raw_material import raw_material_bp
from routes.purchase import purchase_bp
from routes.order import order_bp
from routes.report import report_bp
from routes.api import api_bp

app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(customer_bp)
app.register_blueprint(supplier_bp)
app.register_blueprint(category_bp)
app.register_blueprint(product_bp)
app.register_blueprint(raw_material_bp)
app.register_blueprint(purchase_bp)
app.register_blueprint(order_bp)
app.register_blueprint(report_bp)
app.register_blueprint(api_bp)

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

if __name__ == '__main__':
    app.run(debug=True)
