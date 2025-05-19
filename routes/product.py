from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from app import db
from models import Product, Category, Supplier, StockAdjustment
from forms import ProductForm, StockAdjustmentForm

product_bp = Blueprint('product', __name__, url_prefix='/products')

@product_bp.route('/')
@login_required
def list():
    """商品列表"""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # 获取所有分类，用于筛选
    categories = Category.query.all()
    
    # 分类筛选
    category_id = request.args.get('category_id', type=int)
    
    # 搜索功能
    search = request.args.get('search', '')
    
    # 构建查询
    query = Product.query
    
    # 应用筛选条件
    if category_id:
        query = query.filter(Product.category_id == category_id)
    
    if search:
        query = query.filter(
            Product.name.like(f'%{search}%') | 
            Product.sku.like(f'%{search}%') | 
            Product.description.like(f'%{search}%')
        )
    
    # 执行分页查询
    products = query.paginate(page=page, per_page=per_page)
    
    return render_template(
        'product/list.html', 
        products=products, 
        categories=categories,
        category_id=category_id,
        search=search
    )

@product_bp.route('/<int:id>')
@login_required
def detail(id):
    """商品详情"""
    product = Product.query.get_or_404(id)
    
    # 获取库存调整历史
    adjustments = StockAdjustment.query.filter(
        StockAdjustment.adjustment_type == 'product',
        StockAdjustment.product_id == id
    ).order_by(StockAdjustment.adjustment_date.desc()).limit(5).all()
    
    return render_template('product/detail.html', product=product, adjustments=adjustments)

@product_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """添加商品"""
    form = ProductForm()
    
    # 设置分类和供应商下拉列表
    form.category_id.choices = [(c.id, c.name) for c in Category.query.order_by('name')]
    form.supplier_id.choices = [(0, '-- 选择供应商 --')] + [(s.id, s.name) for s in Supplier.query.order_by('name')]
    
    if form.validate_on_submit():
        supplier_id = form.supplier_id.data if form.supplier_id.data > 0 else None
        
        product = Product(
            name=form.name.data,
            sku=form.sku.data,
            description=form.description.data,
            selling_price=form.selling_price.data,
            cost_price=form.cost_price.data,
            stock_quantity=form.stock_quantity.data,
            category_id=form.category_id.data,
            supplier_id=supplier_id
        )
        db.session.add(product)
        db.session.commit()
        
        flash('商品添加成功', 'success')
        return redirect(url_for('product.list'))
    
    return render_template('product/form.html', form=form, title='添加商品')

@product_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    """编辑商品"""
    product = Product.query.get_or_404(id)
    form = ProductForm(obj=product)
    
    # 设置分类和供应商下拉列表
    form.category_id.choices = [(c.id, c.name) for c in Category.query.order_by('name')]
    form.supplier_id.choices = [(0, '-- 选择供应商 --')] + [(s.id, s.name) for s in Supplier.query.order_by('name')]
    
    # 处理supplier_id为None的情况
    if request.method == 'GET' and product.supplier_id is None:
        form.supplier_id.data = 0
    
    if form.validate_on_submit():
        supplier_id = form.supplier_id.data if form.supplier_id.data > 0 else None
        
        # 记录库存变化
        if product.stock_quantity != form.stock_quantity.data:
            adjustment = StockAdjustment(
                adjustment_type='product',
                product_id=product.id,
                quantity_before=product.stock_quantity,
                quantity_after=form.stock_quantity.data,
                adjustment_quantity=form.stock_quantity.data - product.stock_quantity,
                reason='通过商品编辑页面手动调整',
                created_by=current_user.id
            )
            db.session.add(adjustment)
        
        product.name = form.name.data
        product.sku = form.sku.data
        product.description = form.description.data
        product.selling_price = form.selling_price.data
        product.cost_price = form.cost_price.data
        product.stock_quantity = form.stock_quantity.data
        product.category_id = form.category_id.data
        product.supplier_id = supplier_id
        
        db.session.commit()
        flash('商品更新成功', 'success')
        return redirect(url_for('product.list'))
    
    return render_template('product/form.html', form=form, product=product, title='编辑商品')

@product_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    """删除商品"""
    product = Product.query.get_or_404(id)
    
    # 检查商品是否有关联订单项
    if product.order_items:
        flash('无法删除：该商品已有关联订单', 'danger')
        return redirect(url_for('product.list'))
    
    db.session.delete(product)
    db.session.commit()
    flash('商品删除成功', 'success')
    
    return redirect(url_for('product.list'))

@product_bp.route('/adjust/<int:id>', methods=['GET', 'POST'])
@login_required
def adjust_stock(id):
    """调整商品库存"""
    product = Product.query.get_or_404(id)
    form = StockAdjustmentForm()
    
    # 预设调整类型为商品
    form.adjustment_type.data = 'product'
    form.adjustment_type.render_kw = {'disabled': 'disabled'}
    
    # 预设商品
    form.product_id.choices = [(product.id, product.name)]
    form.product_id.default = product.id
    form.product_id.render_kw = {'disabled': 'disabled'}
    
    # 隐藏原材料选择
    form.raw_material_id.render_kw = {'style': 'display: none;'}
    
    if form.validate_on_submit():
        adjustment = StockAdjustment(
            adjustment_type='product',
            product_id=product.id,
            quantity_before=product.stock_quantity,
            quantity_after=product.stock_quantity + form.adjustment_quantity.data,
            adjustment_quantity=form.adjustment_quantity.data,
            reason=form.reason.data,
            created_by=current_user.id
        )
        
        # 更新商品库存
        product.stock_quantity += form.adjustment_quantity.data
        
        db.session.add(adjustment)
        db.session.commit()
        
        flash(f'库存调整成功：{product.name} 当前库存 {product.stock_quantity}', 'success')
        return redirect(url_for('product.detail', id=product.id))
    
    return render_template(
        'product/adjust.html', 
        form=form, 
        product=product, 
        title='调整商品库存'
    )
