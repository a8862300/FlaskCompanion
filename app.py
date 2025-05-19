import os
import logging
from datetime import datetime

from flask import Flask, g
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager
from werkzeug.middleware.proxy_fix import ProxyFix

# 配置日志
logging.basicConfig(level=logging.DEBUG)

# 创建SQLAlchemy基类
class Base(DeclarativeBase):
    pass

# 创建SQLAlchemy实例
db = SQLAlchemy(model_class=Base)

# 创建Flask应用
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # 用于正确生成https URL

# 配置数据库
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///inventory.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# 初始化数据库
db.init_app(app)

# 初始化LoginManager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = '请先登录'

# 在请求前设置全局变量
@app.before_request
def before_request():
    g.year = datetime.now().year

# 在应用上下文中创建所有表
with app.app_context():
    # 导入模型
    import models
    
    # 创建所有表
    db.create_all()
    
    # 检查是否需要创建管理员账户
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
        app.logger.info('创建了默认管理员账户')

# 导入并注册蓝图
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

# 注册user_loader回调
@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))
