from flask import Blueprint, render_template
from flask_login import login_required
from sqlalchemy import func

from app import db
from models import User, Customer, Product, RawMaterial, Order, Category, OrderItem

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def index():
    """仪表盘首页"""
    # 统计数据
    stats = {
        'user_count': User.query.count(),
        'customer_count': Customer.query.count(),
        'product_count': Product.query.count(),
        'raw_material_count': RawMaterial.query.count(),
        'order_count': Order.query.count(),
    }
    
    # 获取最近订单
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    
    # 获取低库存商品
    low_stock_products = Product.query.filter(
        Product.stock_quantity <= 10
    ).order_by(Product.stock_quantity).limit(5).all()
    
    # 获取低库存原材料
    low_stock_materials = RawMaterial.query.filter(
        RawMaterial.safety_stock != None,
        RawMaterial.stock_quantity <= RawMaterial.safety_stock
    ).order_by(
        (RawMaterial.stock_quantity / RawMaterial.safety_stock)
    ).limit(5).all()
    
    # 获取按分类的商品数量 - 使用 ORM 方式替代原 db.session.query
    category_products = []
    categories = Category.query.all()
    for category in categories:
        category_products.append({
            'name': category.name,
            'count': Product.query.filter_by(category_id=category.id).count()
        })
    
    # 初始化 top_products
    top_products = []
    
    return render_template(
        'dashboard.html',
        stats=stats,
        recent_orders=recent_orders,
        low_stock_products=low_stock_products,
        low_stock_materials=low_stock_materials,
        category_products=category_products,
        top_products=top_products
    )
