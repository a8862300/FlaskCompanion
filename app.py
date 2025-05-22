import os
import logging
from datetime import datetime
import secrets # 导入 secrets 模块用于生成密钥

from flask import Flask, g, session # 导入 session 模块
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager, current_user # 导入 current_user
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_wtf.csrf import CSRFProtect # 导入 CSRFProtect

# 配置日志
logging.basicConfig(level=logging.DEBUG) # 确保日志级别为 DEBUG，以便看到更多信息

# 创建SQLAlchemy基类
class Base(DeclarativeBase):
    pass

# 创建SQLAlchemy实例
db = SQLAlchemy(model_class=Base)

# 创建Flask应用
app = Flask(__name__)

# --- SECRET_KEY 配置 (生产环境推荐设置) ---
# 在生产环境中，务必通过环境变量 SESSION_SECRET 来设置一个强大且一致的密钥。
# 如果环境变量未设置 (例如在开发环境中)，secrets.token_hex(32) 会生成一个随机密钥。
# 注意：如果每次运行都随机生成，会导致会话不一致，CSRF 令牌失效。
# 因此，即使在开发环境中，也建议通过 shell 临时设置 SESSION_SECRET。
app.secret_key = os.environ.get("SESSION_SECRET", secrets.token_hex(32))

# 添加调试日志，打印实际使用的 SECRET_KEY
app.logger.debug(f"DEBUG: Flask app.secret_key is set to: {app.secret_key}")


# 用于正确处理代理后的HTTP/HTTPS URL
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# --- 修正后的数据库配置 ---
# app.config 是一个字典，所有配置都应该作为键值对添加到其中
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///inventory.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300, # 连接池回收时间
    "pool_pre_ping": True, # 连接池预检查，确保连接有效
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False # 禁用SQLAlchemy事件追踪，减少内存消耗

# --- 修复 CSRF 令牌验证的关键配置 ---
# 确保 CSRF 保护是开启的
app.config["WTF_CSRF_ENABLED"] = True 
# 重新引入 WTF_CSRF_CHECK_DEFAULT = False，解决会话原始令牌与浏览器签名令牌不匹配的问题
app.config["WTF_CSRF_CHECK_DEFAULT"] = False 


# 显式初始化 CSRFProtect 扩展，确保其在 app.secret_key 设置之后
csrf = CSRFProtect(app) 

# 初始化数据库
db.init_app(app)

# 初始化LoginManager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login' # 设置登录页面的路由
login_manager.login_message = '请先登录' # 未登录时显示的消息

# 在请求前设置全局变量 (例如当前年份)
@app.before_request
def before_request():
    g.year = datetime.now().year
    # 添加调试日志，打印会话ID (如果存在)
    # 检查 current_user 是否已认证，而不是直接检查 session['user_id']
    if current_user.is_authenticated:
        app.logger.debug(f"DEBUG: Session active for authenticated user: {current_user.id} ({current_user.username})")
    else:
        app.logger.debug("DEBUG: No active authenticated user session.")
    
    # 打印整个 session 对象的内容，以便检查 CSRF 令牌是否存在
    app.logger.debug(f"DEBUG: Current session content: {dict(session)}")


# 在应用上下文环境中创建所有数据库表并检查/创建管理员账户
with app.app_context():
    # 导入模型 (必须在 db.create_all() 之前导入，以便SQLAlchemy发现所有模型)
    import models
    
    # 创建所有表
    db.create_all()
    
    # 检查是否需要创建默认管理员账户
    from models import User # 从models导入User模型
    from werkzeug.security import generate_password_hash # 用于密码哈希

    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            password_hash=generate_password_hash('admin'), # 默认密码 'admin'
            role='admin' # 设定为管理员角色
        )
        db.session.add(admin)
        db.session.commit()
        app.logger.info('创建了默认管理员账户: admin/admin') # 记录日志

# 导入并注册所有蓝图
# 确保 'routes' 文件夹下有对应的 __init__.py 文件，并且每个蓝图文件 (如auth.py) 中有对应的 auth_bp 实例
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

# 注册 Flask-Login 的 user_loader 回调函数
@login_manager.user_loader
def load_user(user_id):
    from models import User # 再次从models导入User模型 (避免循环引用)
    return User.query.get(int(user_id))

# 应用入口点
if __name__ == '__main__':
    # 在开发模式下运行应用
    # 警告: 在生产环境请不要使用 debug=True，这会暴露敏感信息！
    app.run(debug=True)
