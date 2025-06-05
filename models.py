from datetime import datetime
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
import secrets
import string

db = SQLAlchemy()

def generate_order_number():
    """生成唯一的订单号: 年月日 + 6位随机字符"""
    date_part = datetime.now().strftime('%Y%m%d')
    random_part = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
    return f"{date_part}{random_part}"

class User(UserMixin, db.Model):
    """用户模型"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='user')  # 'admin' 或 'user'
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    def __repr__(self):
        return f'<用户 {self.username}>'

class Customer(db.Model):
    """客户模型"""
    __tablename__ = 'customers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    contact = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    address = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # 关系
    orders = db.relationship('Order', back_populates='customer', lazy=True)
    
    def __repr__(self):
        return f'<客户 {self.name}>'

class Supplier(db.Model):
    """供应商模型"""
    __tablename__ = 'suppliers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    contact = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    address = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # 关系
    products = db.relationship('Product', back_populates='supplier', lazy=True)
    raw_materials = db.relationship('RawMaterial', back_populates='supplier', lazy=True) # 新增关系
    raw_material_purchases = db.relationship('RawMaterialPurchase', back_populates='supplier', lazy=True)
    
    def __repr__(self):
        return f'<供应商 {self.name}>'

class Category(db.Model):
    """商品分类模型"""
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # 关系
    products = db.relationship('Product', back_populates='category', lazy=True)
    
    def __repr__(self):
        return f'<分类 {self.name}>'

class Product(db.Model):
    """商品模型"""
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    sku = db.Column(db.String(50), unique=True, nullable=True) # SKU允许为空
    description = db.Column(db.Text)
    selling_price = db.Column(db.Float, nullable=False)
    cost_price = db.Column(db.Float, nullable=False)
    stock_quantity = db.Column(db.Integer, default=0)
    
    # 外键
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id')) # 默认供应商
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关系
    category = db.relationship('Category', back_populates='products')
    supplier = db.relationship('Supplier', back_populates='products')
    order_items = db.relationship('OrderItem', back_populates='product', lazy=True)
    stock_adjustments = db.relationship('StockAdjustment', back_populates='product', lazy=True, primaryjoin="and_(StockAdjustment.product_id == Product.id, StockAdjustment.adjustment_type == 'product')")
    
    def __repr__(self):
        return f'<商品 {self.name} ({self.sku})>'

class RawMaterial(db.Model):
    """原材料模型"""
    __tablename__ = 'raw_materials'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    unit = db.Column(db.String(20), nullable=False)  # 例如：千克, 米, 个
    stock_quantity = db.Column(db.Float, default=0)
    unit_cost = db.Column(db.Float, nullable=False)
    safety_stock = db.Column(db.Float, default=0) # 安全库存量
    
    # 新增外键和关系
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=True) # 可以为空
    supplier = db.relationship('Supplier', back_populates='raw_materials')
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关系
    purchases = db.relationship('RawMaterialPurchase', back_populates='raw_material', lazy=True)
    stock_adjustments = db.relationship('StockAdjustment', back_populates='raw_material', lazy=True, primaryjoin="and_(StockAdjustment.raw_material_id == RawMaterial.id, StockAdjustment.adjustment_type == 'raw_material')")
    
    def __repr__(self):
        return f'<原材料 {self.name}>'

class Order(db.Model):
    """订单模型"""
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(50), unique=True, nullable=False, default=generate_order_number)
    order_date = db.Column(db.DateTime, default=datetime.now)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    total_amount = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(50), default='待支付')
    payment_method = db.Column(db.String(50))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关系
    customer = db.relationship('Customer', back_populates='orders')
    items = db.relationship('OrderItem', back_populates='order', cascade='all, delete-orphan', lazy=True)
    
    def __repr__(self):
        return f'<订单 {self.order_number}>'

class OrderItem(db.Model):
    """订单项模型"""
    __tablename__ = 'order_items'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # 关系
    order = db.relationship('Order', back_populates='items')
    product = db.relationship('Product', back_populates='order_items')
    
    def __repr__(self):
        return f'<订单项 {self.id} - 订单 {self.order_id} - 商品 {self.product_id}>'

class RawMaterialPurchase(db.Model):
    """原材料采购记录"""
    __tablename__ = 'raw_material_purchases'
    
    id = db.Column(db.Integer, primary_key=True)
    purchase_date = db.Column(db.DateTime, default=datetime.now)
    raw_material_id = db.Column(db.Integer, db.ForeignKey('raw_materials.id'), nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # 关系
    raw_material = db.relationship('RawMaterial', back_populates='purchases')
    supplier = db.relationship('Supplier', back_populates='raw_material_purchases')
    
    def __repr__(self):
        return f'<原材料采购 {self.id}>'
    
    def calculate_total(self):
        """计算采购总价"""
        self.total_price = self.quantity * self.unit_price
        return self.total_price

class StockAdjustment(db.Model):
    """库存调整记录"""
    __tablename__ = 'stock_adjustments'
    
    id = db.Column(db.Integer, primary_key=True)
    adjustment_date = db.Column(db.DateTime, default=datetime.now)
    adjustment_type = db.Column(db.String(20), nullable=False)  # 'product' 或 'raw_material'
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'))
    raw_material_id = db.Column(db.Integer, db.ForeignKey('raw_materials.id'))
    quantity_before = db.Column(db.Float, nullable=False)
    quantity_after = db.Column(db.Float, nullable=False)
    adjustment_quantity = db.Column(db.Float, nullable=False)  # 正数表示增加，负数表示减少
    reason = db.Column(db.Text, nullable=False)
    created_by = db.Column(db.String(100)) # 记录操作者
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # 关系
    product = db.relationship('Product', back_populates='stock_adjustments', primaryjoin="and_(StockAdjustment.product_id == Product.id, StockAdjustment.adjustment_type == 'product')")
    raw_material = db.relationship('RawMaterial', back_populates='stock_adjustments', primaryjoin="and_(StockAdjustment.raw_material_id == RawMaterial.id, StockAdjustment.adjustment_type == 'raw_material')")
    
    def __repr__(self):
        return f'<库存调整 {self.id}>'