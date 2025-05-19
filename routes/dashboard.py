from flask import Blueprint, render_template
from flask_login import login_required
from sqlalchemy import func

from models import User, Customer, Product, RawMaterial, Order, Category

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
    
    # 获取按分类的商品数量
    category_products = db.session.query(
        Category.name, 
        func.count(Product.id).label('count')
    ).join(
        Product, 
        Product.category_id == Category.id
    ).group_by(
        Category.name
    ).all()
    
    # 获取销售额最高的5个商品
    top_products = db.session.query(
        Product.name,
        func.sum(Order.total_amount).label('total_sales')
    ).join(
        OrderItem, 
        OrderItem.product_id == Product.id
    ).join(
        Order, 
        OrderItem.order_id == Order.id
    ).filter(
        Order.status != '已取消'
    ).group_by(
        Product.name
    ).order_by(
        func.sum(Order.total_amount).desc()
    ).limit(5).all()
    
    return render_template(
        'dashboard.html',
        stats=stats,
        recent_orders=recent_orders,
        low_stock_products=low_stock_products,
        low_stock_materials=low_stock_materials,
        category_products=category_products,
        top_products=top_products
    )
