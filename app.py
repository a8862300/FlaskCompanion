import os
import logging
from datetime import datetime
import secrets
from typing import Any
from dotenv import load_dotenv
from flask import Flask, g, session, jsonify
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager, current_user
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_wtf.csrf import CSRFProtect, generate_csrf
from models import db

logging.basicConfig(level=logging.INFO)

class Base(DeclarativeBase):
    pass

load_dotenv()

def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = os.environ.get("SESSION_SECRET", secrets.token_hex(32))
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///inventory.db")
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["WTF_CSRF_ENABLED"] = True
    app.config["WTF_CSRF_CHECK_DEFAULT"] = True
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SECURE"] = os.environ.get("FLASK_ENV") == "production"
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    # 日志级别按环境切换
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    app.logger.setLevel(getattr(logging, log_level, logging.INFO))

    # 日志格式优化，输出时间、等级、模块
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s in %(module)s: %(message)s')
    for handler in app.logger.handlers:
        handler.setFormatter(formatter)

    # 生产环境日志写入文件
    if os.environ.get("FLASK_ENV") == "production":
        file_handler = logging.FileHandler('flask_app.log', encoding='utf-8')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(getattr(logging, log_level, logging.INFO))
        app.logger.addHandler(file_handler)

    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    db.init_app(app)
    csrf = CSRFProtect()
    csrf.init_app(app)
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

    # 统一 JSON 错误响应，支持 API/页面
    @app.errorhandler(400)
    def bad_request(e):
        if hasattr(e, 'description'):
            msg = e.description
        else:
            msg = 'Bad Request'
        return jsonify(error=msg), 400

    @app.errorhandler(404)
    def not_found(e):
        return jsonify(error="Not Found"), 404
    @app.errorhandler(500)
    def server_error(e):
        return jsonify(error="Internal Server Error"), 500

    # 蓝图自动注册
    from routes import auth, dashboard, customer, supplier, category, product, raw_material, purchase, order, report, api
    blueprints = [
        auth.auth_bp, dashboard.dashboard_bp, customer.customer_bp, supplier.supplier_bp,
        category.category_bp, product.product_bp, raw_material.raw_material_bp,
        purchase.purchase_bp, order.order_bp, report.report_bp, api.api_bp
    ]
    for bp in blueprints:
        # API 路由禁用 CSRF
        if getattr(bp, 'name', '').startswith('api'):
            csrf.exempt(bp)
        # dashboard 和 auth 不加 url_prefix，其他蓝图加 None
        if bp.name == 'dashboard' or bp.name == 'auth':
            app.register_blueprint(bp)
        else:
            app.register_blueprint(bp)

    @login_manager.user_loader
    def load_user(user_id):
        from models import User
        return User.query.get(int(user_id))

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=os.environ.get("FLASK_ENV") != "production")
