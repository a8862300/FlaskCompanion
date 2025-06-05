from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required

from models import db
from models import Product, Customer, Supplier, Category, RawMaterial

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/products')
@login_required
def get_products():
    """获取所有商品的API接口"""
    products = Product.query.all()
    result = [{
        'id': p.id,
        'name': p.name,
        'sku': p.sku,
        'selling_price': p.selling_price,
        'cost_price': p.cost_price,
        'stock_quantity': p.stock_quantity,
        'category_id': p.category_id,
        'category_name': p.category.name
    } for p in products]
    return jsonify(result)

@api_bp.route('/products/<int:id>')
@login_required
def get_product(id):
    """获取单个商品详情的API接口"""
    product = Product.query.get_or_404(id)
    result = {
        'id': product.id,
        'name': product.name,
        'sku': product.sku,
        'description': product.description,
        'selling_price': product.selling_price,
        'cost_price': product.cost_price,
        'stock_quantity': product.stock_quantity,
        'category_id': product.category_id,
        'category_name': product.category.name,
        'supplier_id': product.supplier_id,
        'supplier_name': product.supplier.name if product.supplier else None
    }
    return jsonify(result)

@api_bp.route('/customers')
@login_required
def get_customers():
    """获取所有客户的API接口"""
    customers = Customer.query.all()
    result = [{
        'id': c.id,
        'name': c.name,
        'contact': c.contact,
        'phone': c.phone,
        'address': c.address
    } for c in customers]
    return jsonify(result)

@api_bp.route('/suppliers')
@login_required
def get_suppliers():
    """获取所有供应商的API接口"""
    suppliers = Supplier.query.all()
    result = [{
        'id': s.id,
        'name': s.name,
        'contact': s.contact,
        'phone': s.phone,
        'address': s.address
    } for s in suppliers]
    return jsonify(result)

@api_bp.route('/categories')
@login_required
def get_categories():
    """获取所有商品分类的API接口"""
    categories = Category.query.all()
    result = [{
        'id': c.id,
        'name': c.name,
        'description': c.description
    } for c in categories]
    return jsonify(result)

@api_bp.route('/raw-materials')
@login_required
def get_raw_materials():
    """获取所有原材料的API接口"""
    raw_materials = RawMaterial.query.all()
    result = [{
        'id': m.id,
        'name': m.name,
        'unit': m.unit,
        'stock_quantity': m.stock_quantity,
        'unit_cost': m.unit_cost,
        'safety_stock': m.safety_stock
    } for m in raw_materials]
    return jsonify(result)

@api_bp.route('/raw-materials/<int:id>')
@login_required
def get_raw_material(id):
    """获取单个原材料详情的API接口"""
    raw_material = RawMaterial.query.get_or_404(id)
    result = {
        'id': raw_material.id,
        'name': raw_material.name,
        'unit': raw_material.unit,
        'stock_quantity': raw_material.stock_quantity,
        'unit_cost': raw_material.unit_cost,
        'safety_stock': raw_material.safety_stock
    }
    return jsonify(result)

@api_bp.route('/search/products')
@login_required
def search_products():
    """搜索商品的API接口"""
    query = request.args.get('q', '')
    category_id = request.args.get('category_id', type=int)
    
    # 构建查询
    products_query = Product.query
    
    # 应用筛选条件
    if query:
        products_query = products_query.filter(
            Product.name.like(f'%{query}%') | 
            Product.sku.like(f'%{query}%')
        )
    
    if category_id:
        products_query = products_query.filter(Product.category_id == category_id)
    
    # 执行查询
    products = products_query.all()
    
    result = [{
        'id': p.id,
        'name': p.name,
        'sku': p.sku,
        'selling_price': p.selling_price,
        'cost_price': p.cost_price,
        'stock_quantity': p.stock_quantity,
        'category_id': p.category_id,
        'category_name': p.category.name
    } for p in products]
    
    return jsonify(result)
