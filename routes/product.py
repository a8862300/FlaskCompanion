from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from models import db
# 确保导入了 RawMaterial，因为 StockAdjustmentForm 中会用到
from models import Product, Category, Supplier, StockAdjustment, RawMaterial 

# 引入 pypinyin 库和 time
from pypinyin import Style, pinyin
import time

# 引入 IntegrityError
from sqlalchemy.exc import IntegrityError

from forms import ProductForm, StockAdjustmentForm # 确保 StockAdjustmentForm 导入正确


product_bp = Blueprint('product', __name__, url_prefix='/product')

@product_bp.route('/list')
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
        
        # --- SKU 自动生成逻辑开始 ---
        sku = form.sku.data # 获取表单中输入的 SKU
        
        if not sku: # 如果用户没有输入 SKU (即表单 SKU 字段为空)
            product_name = form.name.data
            # 将产品名称转换为拼音首字母，并转为大写
            pinyin_initials = ''.join([i[0][0].upper() for i in pinyin(product_name, style=Style.NORMAL)])
            
            # 为了确保 SKU 唯一性，可以在后面添加一个简短的时间戳或随机数
            unique_suffix = str(int(time.time() * 100))[-6:] # 取时间戳后6位，足够随机且简短
            
            sku = f"{pinyin_initials}-{unique_suffix}"
            current_app.logger.debug(f"DEBUG: Auto-generated SKU: {sku} for product: {product_name}")
            
        # --- SKU 自动生成逻辑结束 ---

        product = Product(
            name=form.name.data,
            sku=sku, # 使用生成的或用户输入的 SKU
            description=form.description.data,
            selling_price=form.selling_price.data,
            cost_price=form.cost_price.data,
            stock_quantity=form.stock_quantity.data,
            category_id=form.category_id.data,
            supplier_id=supplier_id
        )
        
        try:
            db.session.add(product)
            db.session.commit()
            flash('商品添加成功', 'success')
            return redirect(url_for('product.list'))
        except IntegrityError: # 捕获唯一性约束错误
            db.session.rollback() # 回滚事务
            flash('错误：生成的 SKU 可能已存在，请尝试手动输入 SKU 或稍后重试。', 'danger')
        
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
        product.sku = form.sku.data # SKU 从表单获取，用户可修改
        product.description = form.description.data
        product.selling_price = form.selling_price.data
        product.cost_price = form.cost_price.data
        product.stock_quantity = form.stock_quantity.data
        product.category_id = form.category_id.data
        product.supplier_id = supplier_id
        
        try: # 同样在编辑时也需要捕获唯一性错误
            db.session.commit()
            flash('商品更新成功', 'success')
            return redirect(url_for('product.list'))
        except IntegrityError:
            db.session.rollback()
            flash('错误：更新后的 SKU 已存在，请尝试其他 SKU。', 'danger')
    
    return render_template('product/form.html', form=form, product=product, title='编辑商品')

@product_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    """删除商品"""
    product = Product.query.get_or_404(id)
    
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
    
    # 设置 SelectField 的 choices 和 default 值
    # adjustment_type 总是 'product'
    form.adjustment_type.choices = [('product', '成品商品')]
    form.adjustment_type.default = 'product'
    
    # product_id 总是当前商品的 ID
    form.product_id.choices = [(product.id, product.name)]
    form.product_id.default = product.id
    
    # raw_material_id 选项（如果需要，可以从数据库加载）
    # 由于是调整商品库存，raw_material_id 通常不需要用户选择，可以隐藏并设置默认值
    form.raw_material_id.choices = [(0, 'N/A')] + [(rm.id, rm.name) for rm in RawMaterial.query.order_by('name').all()]
    form.raw_material_id.default = 0 # 设置一个默认值，例如 0 或 None
    form.raw_material_id.render_kw = {'style': 'display: none;'} # 隐藏字段

    # 调用 process() 方法来应用默认值和处理请求数据
    # 注意：如果 form.data 已经被手动设置，process() 可能会覆盖它，
    # 但对于 SelectField 的 default 属性，process() 应该能正确处理
    # 移除 form.process()，因为它可能干扰手动设置的 default 值
    # form.process() 
    
    # --- 新增调试日志：打印浏览器发送的表单数据 ---
    if request.method == 'POST':
        current_app.logger.debug(f"DEBUG: Form data received from browser (POST): {request.form}") # 使用 request.form 获取数据
        current_app.logger.debug(f"DEBUG: CSRF token from browser (POST): {request.form.get('csrf_token')}") # 直接从 request.form 获取 csrf_token
    # --- 调试日志结束 ---

    if form.validate_on_submit():
        adjustment = StockAdjustment()
        adjustment.adjustment_type = form.adjustment_type.data # 从表单数据获取
        adjustment.product_id = form.product_id.data # 从表单数据获取
        adjustment.raw_material_id = form.raw_material_id.data if form.raw_material_id.data > 0 else None # 根据业务逻辑处理
        
        adjustment.quantity_before = product.stock_quantity
        adjustment.quantity_after = product.stock_quantity + form.adjustment_quantity.data
        adjustment.adjustment_quantity = form.adjustment_quantity.data
        
        reason_text = form.reason.data
        if form.reason_detail.data:
            reason_text += f": {form.reason_detail.data}"
        adjustment.reason = reason_text
        adjustment.created_by = current_user.id
        
        # 更新商品库存
        product.stock_quantity += form.adjustment_quantity.data
        
        db.session.add(adjustment)
        db.session.commit()
        
        flash(f'库存调整成功：{product.name} 当前库存 {product.stock_quantity}', 'success')
        return redirect(url_for('product.detail', id=product.id))
    else:
        # 如果验证失败，打印表单错误，这对于调试非常有用
        current_app.logger.debug(f"DEBUG: Form validation failed. Errors: {form.errors}")
        if 'csrf_token' in form.errors:
            current_app.logger.debug(f"DEBUG: CSRF token specific errors: {form.errors['csrf_token']}")
    
    return render_template(
        'product/adjust.html', 
        form=form, 
        product=product, 
        title='调整商品库存'
    )
