from datetime import datetime
from flask_login import UserMixin
from app import db
from sqlalchemy.sql import func
import secrets
import string

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
    orders = db.relationship('Order', back_populates='customer', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<客户 {self.name}>'

class Supplier(db.Model):
    """供应商模型"""
    __tablename__ = 'suppliers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    contact = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    address = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # 关系
    products = db.relationship('Product', back_populates='supplier')
    raw_material_purchases = db.relationship('RawMaterialPurchase', back_populates='supplier')
    
    def __repr__(self):
        return f'<供应商 {self.name}>'

class Category(db.Model):
    """商品分类模型"""
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # 关系
    products = db.relationship('Product', back_populates='category', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<分类 {self.name}>'

class Product(db.Model):
    """商品模型"""
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    sku = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)
    selling_price = db.Column(db.Float, nullable=False)
    cost_price = db.Column(db.Float, nullable=False)
    stock_quantity = db.Column(db.Integer, default=0)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'))
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # 关系
    category = db.relationship('Category', back_populates='products')
    supplier = db.relationship('Supplier', back_populates='products')
    order_items = db.relationship('OrderItem', back_populates='product')
    
    def __repr__(self):
        return f'<商品 {self.name}>'

class RawMaterial(db.Model):
    """原材料模型"""
    __tablename__ = 'raw_materials'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    unit = db.Column(db.String(20), nullable=False)  # 如：千克, 米, 个
    stock_quantity = db.Column(db.Float, default=0)
    unit_cost = db.Column(db.Float, nullable=False)
    safety_stock = db.Column(db.Float)  # 安全库存量
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # 关系
    purchases = db.relationship('RawMaterialPurchase', back_populates='raw_material', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<原材料 {self.name}>'

class Order(db.Model):
    """订单模型"""
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(20), default=generate_order_number, unique=True, nullable=False)
    order_date = db.Column(db.DateTime, default=datetime.now)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    status = db.Column(db.String(20), default='待支付')  # 待支付, 已支付, 已发货, 已完成, 已取消
    payment_method = db.Column(db.String(20))  # 支付宝, 微信支付, 货到付款
    total_amount = db.Column(db.Float, default=0)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # 关系
    customer = db.relationship('Customer', back_populates='orders')
    order_items = db.relationship('OrderItem', back_populates='order', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<订单 {self.order_number}>'
    
    def calculate_total(self):
        """计算订单总金额"""
        total = sum(item.subtotal for item in self.order_items)
        self.total_amount = total
        return total

class OrderItem(db.Model):
    """订单项模型"""
    __tablename__ = 'order_items'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)
    
    # 关系
    order = db.relationship('Order', back_populates='order_items')
    product = db.relationship('Product', back_populates='order_items')
    
    def __repr__(self):
        return f'<订单项 {self.id}>'
    
    def calculate_subtotal(self):
        """计算小计金额"""
        self.subtotal = self.quantity * self.unit_price
        return self.subtotal

class RawMaterialPurchase(db.Model):
    """原材料采购记录模型"""
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
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # 关系
    product = db.relationship('Product')
    raw_material = db.relationship('RawMaterial')
    user = db.relationship('User')
    
    def __repr__(self):
        return f'<库存调整 {self.id}>'
