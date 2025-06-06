from datetime import datetime
from typing import Any, Optional
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import secrets
import string

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

def generate_order_number() -> str:
    """生成唯一的订单号: 年月日 + 6位随机字符"""
    date_part = datetime.now().strftime('%Y%m%d')
    random_part = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
    return f"{date_part}{random_part}"

class User(UserMixin, db.Model):
    """用户模型"""
    __tablename__ = 'users'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(nullable=False)
    role: Mapped[str] = mapped_column(default='user')  # 'admin' 或 'user'
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    
    def __repr__(self):
        return f'<用户 {self.username}>'

class Customer(db.Model):
    """客户模型"""
    __tablename__ = 'customers'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    contact: Mapped[str] = mapped_column()
    phone: Mapped[str] = mapped_column()
    address: Mapped[str] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    
    # 关系
    orders: Mapped[list['Order']] = relationship('Order', back_populates='customer', lazy=True)
    
    def __repr__(self):
        return f'<客户 {self.name}>'

class Supplier(db.Model):
    """供应商模型"""
    __tablename__ = 'suppliers'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True, nullable=False)
    contact: Mapped[str] = mapped_column()
    phone: Mapped[str] = mapped_column()
    address: Mapped[str] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    
    # 关系
    products: Mapped[list['Product']] = relationship('Product', back_populates='supplier', lazy=True)
    raw_materials: Mapped[list['RawMaterial']] = relationship('RawMaterial', back_populates='supplier', lazy=True) # 新增关系
    raw_material_purchases: Mapped[list['RawMaterialPurchase']] = relationship('RawMaterialPurchase', back_populates='supplier', lazy=True)
    
    def __repr__(self):
        return f'<供应商 {self.name}>'

class Category(db.Model):
    """商品分类模型"""
    __tablename__ = 'categories'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True, nullable=False)
    description: Mapped[str] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    
    # 关系
    products: Mapped[list['Product']] = relationship('Product', back_populates='category', lazy=True)
    
    def __repr__(self):
        return f'<分类 {self.name}>'

class Product(db.Model):
    """商品模型"""
    __tablename__ = 'products'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    sku: Mapped[str] = mapped_column(unique=True, nullable=True) # SKU允许为空
    description: Mapped[str] = mapped_column()
    selling_price: Mapped[float] = mapped_column(nullable=False)
    cost_price: Mapped[float] = mapped_column(nullable=False)
    stock_quantity: Mapped[int] = mapped_column(default=0)
    
    # 外键
    category_id: Mapped[int] = mapped_column(db.ForeignKey('categories.id'), nullable=False)
    supplier_id: Mapped[Optional[int]] = mapped_column(db.ForeignKey('suppliers.id')) # 默认供应商
    
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.now, onupdate=datetime.now)
    
    # 关系
    category: Mapped['Category'] = relationship('Category', back_populates='products')
    supplier: Mapped['Supplier'] = relationship('Supplier', back_populates='products')
    order_items: Mapped[list['OrderItem']] = relationship('OrderItem', back_populates='product', lazy=True)
    stock_adjustments: Mapped[list['StockAdjustment']] = relationship('StockAdjustment', back_populates='product', lazy=True, primaryjoin="and_(StockAdjustment.product_id == Product.id, StockAdjustment.adjustment_type == 'product')")
    
    def __repr__(self):
        return f'<商品 {self.name} ({self.sku})>'

class RawMaterial(db.Model):
    """原材料模型"""
    __tablename__ = 'raw_materials'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    unit: Mapped[str] = mapped_column(nullable=False)  # 例如：千克, 米, 个
    stock_quantity: Mapped[float] = mapped_column(default=0)
    unit_cost: Mapped[float] = mapped_column(nullable=False)
    safety_stock: Mapped[float] = mapped_column(default=0) # 安全库存量
    
    # 新增外键和关系
    supplier_id: Mapped[Optional[int]] = mapped_column(db.ForeignKey('suppliers.id'), nullable=True) # 可以为空
    supplier: Mapped['Supplier'] = relationship('Supplier', back_populates='raw_materials')
    
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.now, onupdate=datetime.now)
    
    # 关系
    purchases: Mapped[list['RawMaterialPurchase']] = relationship('RawMaterialPurchase', back_populates='raw_material', lazy=True)
    stock_adjustments: Mapped[list['StockAdjustment']] = relationship('StockAdjustment', back_populates='raw_material', lazy=True, primaryjoin="and_(StockAdjustment.raw_material_id == RawMaterial.id, StockAdjustment.adjustment_type == 'raw_material')")
    
    def __repr__(self):
        return f'<原材料 {self.name}>'

class Order(db.Model):
    """订单模型"""
    __tablename__ = 'orders'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    order_number: Mapped[str] = mapped_column(unique=True, nullable=False, default=generate_order_number)
    order_date: Mapped[datetime] = mapped_column(default=datetime.now)
    customer_id: Mapped[int] = mapped_column(db.ForeignKey('customers.id'), nullable=False)
    total_amount: Mapped[float] = mapped_column(default=0.0)
    status: Mapped[str] = mapped_column(default='待支付')
    payment_method: Mapped[str] = mapped_column()
    notes: Mapped[str] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.now, onupdate=datetime.now)
    
    # 关系
    customer: Mapped['Customer'] = relationship('Customer', back_populates='orders')
    items: Mapped[list['OrderItem']] = relationship('OrderItem', back_populates='order', cascade='all, delete-orphan', lazy=True)
    
    def __repr__(self):
        return f'<订单 {self.order_number}>'

class OrderItem(db.Model):
    """订单项模型"""
    __tablename__ = 'order_items'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(db.ForeignKey('orders.id'), nullable=False)
    product_id: Mapped[int] = mapped_column(db.ForeignKey('products.id'), nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False)
    unit_price: Mapped[float] = mapped_column(nullable=False)
    subtotal: Mapped[float] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    
    # 关系
    order: Mapped['Order'] = relationship('Order', back_populates='items')
    product: Mapped['Product'] = relationship('Product', back_populates='order_items')
    
    def __repr__(self):
        return f'<订单项 {self.id} - 订单 {self.order_id} - 商品 {self.product_id}>'

class RawMaterialPurchase(db.Model):
    """原材料采购记录"""
    __tablename__ = 'raw_material_purchases'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    purchase_date: Mapped[datetime] = mapped_column(default=datetime.now)
    raw_material_id: Mapped[int] = mapped_column(db.ForeignKey('raw_materials.id'), nullable=False)
    supplier_id: Mapped[int] = mapped_column(db.ForeignKey('suppliers.id'), nullable=False)
    quantity: Mapped[float] = mapped_column(nullable=False)
    unit_price: Mapped[float] = mapped_column(nullable=False)
    total_price: Mapped[float] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    
    # 关系
    raw_material: Mapped['RawMaterial'] = relationship('RawMaterial', back_populates='purchases')
    supplier: Mapped['Supplier'] = relationship('Supplier', back_populates='raw_material_purchases')
    
    def __repr__(self):
        return f'<原材料采购 {self.id}>'
    
    def calculate_total(self):
        """计算采购总价"""
        self.total_price = self.quantity * self.unit_price
        return self.total_price

class StockAdjustment(db.Model):
    """库存调整记录"""
    __tablename__ = 'stock_adjustments'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    adjustment_date: Mapped[datetime] = mapped_column(default=datetime.now)
    adjustment_type: Mapped[str] = mapped_column(nullable=False)  # 'product' 或 'raw_material'
    product_id: Mapped[Optional[int]] = mapped_column(db.ForeignKey('products.id'))
    raw_material_id: Mapped[Optional[int]] = mapped_column(db.ForeignKey('raw_materials.id'))
    quantity_before: Mapped[float] = mapped_column(nullable=False)
    quantity_after: Mapped[float] = mapped_column(nullable=False)
    adjustment_quantity: Mapped[float] = mapped_column(nullable=False)  # 正数表示增加，负数表示减少
    reason: Mapped[str] = mapped_column(nullable=False)
    created_by: Mapped[str] = mapped_column() # 记录操作者
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    
    # 关系
    product: Mapped['Product'] = relationship('Product', back_populates='stock_adjustments', primaryjoin="and_(StockAdjustment.product_id == Product.id, StockAdjustment.adjustment_type == 'product')")
    raw_material: Mapped['RawMaterial'] = relationship('RawMaterial', back_populates='stock_adjustments', primaryjoin="and_(StockAdjustment.raw_material_id == RawMaterial.id, StockAdjustment.adjustment_type == 'raw_material')")
    
    def __repr__(self):
        return f'<库存调整 {self.id}>'