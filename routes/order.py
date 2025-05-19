from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime

from app import db
from models import Order, OrderItem, Customer, Product, Category, StockAdjustment
from forms import OrderForm

order_bp = Blueprint('order', __name__, url_prefix='/orders')

@order_bp.route('/')
@login_required
def list():
    """订单列表"""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # 高级筛选条件
    customer_id = request.args.get('customer_id', type=int)
    status = request.args.get('status')
    category_id = request.args.get('category_id', type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    period = request.args.get('period')
    
    # 转换日期字符串为日期对象（如果提供）
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
        # 设置为当天结束时间
        end_date = end_date.replace(hour=23, minute=59, second=59)
    
    # 根据周期设置日期范围
    today = datetime.now()
    if period == 'today':
        start_date = today.replace(hour=0, minute=0, second=0)
        end_date = today.replace(hour=23, minute=59, second=59)
    elif period == 'week':
        # 获取当前周的开始（周一）和结束（周日）
        start_date = today.replace(hour=0, minute=0, second=0) - timedelta(days=today.weekday())
        end_date = start_date + timedelta(days=6, hours=23, minutes=59, seconds=59)
    elif period == 'month':
        # 获取当前月的开始和结束
        start_date = today.replace(day=1, hour=0, minute=0, second=0)
        # 获取下个月的第一天，然后减去1秒
        if today.month == 12:
            end_date = datetime(today.year + 1, 1, 1, 23, 59, 59) - timedelta(seconds=1)
        else:
            end_date = datetime(today.year, today.month + 1, 1, 23, 59, 59) - timedelta(seconds=1)
    elif period == 'quarter':
        # 获取当前季度的开始和结束
        quarter = (today.month - 1) // 3 + 1
        start_date = datetime(today.year, 3 * quarter - 2, 1, 0, 0, 0)
        if quarter == 4:
            end_date = datetime(today.year + 1, 1, 1, 23, 59, 59) - timedelta(seconds=1)
        else:
            end_date = datetime(today.year, 3 * quarter + 1, 1, 23, 59, 59) - timedelta(seconds=1)
    elif period == 'year':
        # 获取当前年的开始和结束
        start_date = datetime(today.year, 1, 1, 0, 0, 0)
        end_date = datetime(today.year, 12, 31, 23, 59, 59)
    
    # 构建查询
    query = Order.query
    
    # 应用基本筛选条件
    if customer_id:
        query = query.filter(Order.customer_id == customer_id)
    
    if status:
        query = query.filter(Order.status == status)
    
    if start_date:
        query = query.filter(Order.order_date >= start_date)
    
    if end_date:
        query = query.filter(Order.order_date <= end_date)
    
    # 应用分类筛选（需要连接OrderItem和Product表）
    if category_id:
        query = query.join(OrderItem, Order.id == OrderItem.order_id) \
                    .join(Product, OrderItem.product_id == Product.id) \
                    .filter(Product.category_id == category_id) \
                    .group_by(Order.id)
    
    # 按日期降序排序
    query = query.order_by(Order.order_date.desc())
    
    # 执行分页查询
    orders = query.paginate(page=page, per_page=per_page)
    
    # 获取筛选选项数据
    customers = Customer.query.all()
    categories = Category.query.all()
    
    # 订单状态选项
    status_options = [
        ('待支付', '待支付'),
        ('已支付', '已支付'),
        ('已发货', '已发货'),
        ('已完成', '已完成'),
        ('已取消', '已取消')
    ]
    
    # 时间周期选项
    period_options = [
        ('today', '今日'),
        ('week', '本周'),
        ('month', '本月'),
        ('quarter', '本季度'),
        ('year', '本年度')
    ]
    
    return render_template(
        'order/list.html', 
        orders=orders, 
        customers=customers,
        categories=categories,
        status_options=status_options,
        period_options=period_options,
        filter={
            'customer_id': customer_id,
            'status': status,
            'category_id': category_id,
            'start_date': start_date.strftime('%Y-%m-%d') if start_date else '',
            'end_date': end_date.strftime('%Y-%m-%d') if end_date else '',
            'period': period
        }
    )

@order_bp.route('/<int:id>')
@login_required
def detail(id):
    """订单详情"""
    order = Order.query.get_or_404(id)
    return render_template('order/detail.html', order=order)

@order_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """添加订单"""
    form = OrderForm()
    
    # 设置客户下拉列表
    form.customer_id.choices = [(c.id, c.name) for c in Customer.query.order_by('name')]
    
    # 获取所有商品，用于前端选择
    products = Product.query.all()
    
    if request.method == 'POST':
        # 从表单获取基本订单信息
        if form.validate_on_submit():
            # 创建订单
            order = Order(
                order_date=form.order_date.data,
                customer_id=form.customer_id.data,
                status=form.status.data,
                payment_method=form.payment_method.data,
                notes=form.notes.data
            )
            db.session.add(order)
            db.session.flush()  # 获取订单ID
            
            # 处理订单项
            total_amount = 0
            product_ids = request.form.getlist('product_id[]')
            quantities = request.form.getlist('quantity[]')
            unit_prices = request.form.getlist('unit_price[]')
            
            if not product_ids:
                flash('订单必须包含至少一项商品', 'danger')
                return render_template('order/form.html', form=form, products=products, title='添加订单')
            
            for i in range(len(product_ids)):
                product_id = int(product_ids[i])
                quantity = int(quantities[i])
                unit_price = float(unit_prices[i])
                
                # 验证数据
                if quantity <= 0:
                    flash(f'商品数量必须大于0', 'danger')
                    return render_template('order/form.html', form=form, products=products, title='添加订单')
                
                if unit_price < 0:
                    flash(f'商品单价不能为负数', 'danger')
                    return render_template('order/form.html', form=form, products=products, title='添加订单')
                
                # 获取商品
                product = Product.query.get(product_id)
                if not product:
                    flash(f'商品ID {product_id} 不存在', 'danger')
                    return render_template('order/form.html', form=form, products=products, title='添加订单')
                
                # 检查库存
                if quantity > product.stock_quantity:
                    flash(f'商品 "{product.name}" 库存不足: 需要 {quantity}, 实际 {product.stock_quantity}', 'danger')
                    return render_template('order/form.html', form=form, products=products, title='添加订单')
                
                # 创建订单项
                subtotal = quantity * unit_price
                order_item = OrderItem(
                    order_id=order.id,
                    product_id=product_id,
                    quantity=quantity,
                    unit_price=unit_price,
                    subtotal=subtotal
                )
                db.session.add(order_item)
                
                # 减少商品库存
                old_stock = product.stock_quantity
                product.stock_quantity -= quantity
                
                # 记录库存变动
                adjustment = StockAdjustment(
                    adjustment_type='product',
                    product_id=product.id,
                    quantity_before=old_stock,
                    quantity_after=product.stock_quantity,
                    adjustment_quantity=-quantity,
                    reason=f'销售出库: 订单 {order.order_number}',
                    created_by=current_user.id
                )
                db.session.add(adjustment)
                
                # 累计订单总金额
                total_amount += subtotal
            
            # 设置订单总金额
            order.total_amount = total_amount
            
            db.session.commit()
            flash('订单创建成功', 'success')
            return redirect(url_for('order.detail', id=order.id))
    
    return render_template('order/form.html', form=form, products=products, title='添加订单')

@order_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    """编辑订单"""
    order = Order.query.get_or_404(id)
    form = OrderForm(obj=order)
    
    # 设置客户下拉列表
    form.customer_id.choices = [(c.id, c.name) for c in Customer.query.order_by('name')]
    
    # 获取所有商品，用于前端选择
    products = Product.query.all()
    
    # 获取现有订单项
    order_items = OrderItem.query.filter_by(order_id=order.id).all()
    
    if request.method == 'POST':
        # 从表单获取基本订单信息
        if form.validate_on_submit():
            # 更新订单基本信息
            order.order_date = form.order_date.data
            order.customer_id = form.customer_id.data
            order.status = form.status.data
            order.payment_method = form.payment_method.data
            order.notes = form.notes.data
            
            # 处理订单项变更
            # 记录现有订单项，用于跟踪删除
            existing_items = {item.id: item for item in order_items}
            
            # 收集提交的订单项ID，用于确定哪些被删除
            submitted_item_ids = set()
            
            # 处理新的或更新的订单项
            product_ids = request.form.getlist('product_id[]')
            quantities = request.form.getlist('quantity[]')
            unit_prices = request.form.getlist('unit_price[]')
            item_ids = request.form.getlist('item_id[]')  # 已有项目的ID
            
            if not product_ids:
                flash('订单必须包含至少一项商品', 'danger')
                return render_template('order/form.html', form=form, products=products, order=order, order_items=order_items, title='编辑订单')
            
            # 重置总金额
            total_amount = 0
            
            for i in range(len(product_ids)):
                product_id = int(product_ids[i])
                quantity = int(quantities[i])
                unit_price = float(unit_prices[i])
                item_id = item_ids[i] if i < len(item_ids) and item_ids[i] else None
                
                # 验证数据
                if quantity <= 0:
                    flash(f'商品数量必须大于0', 'danger')
                    return render_template('order/form.html', form=form, products=products, order=order, order_items=order_items, title='编辑订单')
                
                if unit_price < 0:
                    flash(f'商品单价不能为负数', 'danger')
                    return render_template('order/form.html', form=form, products=products, order=order, order_items=order_items, title='编辑订单')
                
                # 获取商品
                product = Product.query.get(product_id)
                if not product:
                    flash(f'商品ID {product_id} 不存在', 'danger')
                    return render_template('order/form.html', form=form, products=products, order=order, order_items=order_items, title='编辑订单')
                
                # 计算小计
                subtotal = quantity * unit_price
                
                # 处理现有订单项
                if item_id and item_id.isdigit() and int(item_id) in existing_items:
                    # 更新现有订单项
                    item_id = int(item_id)
                    item = existing_items[item_id]
                    
                    # 检查库存（考虑原订单项数量）
                    if quantity > item.quantity:
                        additional_qty = quantity - item.quantity
                        if additional_qty > product.stock_quantity:
                            flash(f'商品 "{product.name}" 库存不足: 需要额外 {additional_qty}, 实际 {product.stock_quantity}', 'danger')
                            return render_template('order/form.html', form=form, products=products, order=order, order_items=order_items, title='编辑订单')
                    
                    # 调整库存
                    old_stock = product.stock_quantity
                    stock_change = item.quantity - quantity  # 正数表示退回库存，负数表示额外扣减
                    product.stock_quantity += stock_change
                    
                    # 记录库存变动
                    if stock_change != 0:
                        adjustment = StockAdjustment(
                            adjustment_type='product',
                            product_id=product.id,
                            quantity_before=old_stock,
                            quantity_after=product.stock_quantity,
                            adjustment_quantity=stock_change,
                            reason=f'订单修改: 订单号 {order.order_number}',
                            created_by=current_user.id
                        )
                        db.session.add(adjustment)
                    
                    # 更新订单项
                    item.product_id = product_id
                    item.quantity = quantity
                    item.unit_price = unit_price
                    item.subtotal = subtotal
                    
                    # 标记为已处理
                    submitted_item_ids.add(item_id)
                else:
                    # 创建新订单项
                    # 检查库存
                    if quantity > product.stock_quantity:
                        flash(f'商品 "{product.name}" 库存不足: 需要 {quantity}, 实际 {product.stock_quantity}', 'danger')
                        return render_template('order/form.html', form=form, products=products, order=order, order_items=order_items, title='编辑订单')
                    
                    # 创建订单项
                    new_item = OrderItem(
                        order_id=order.id,
                        product_id=product_id,
                        quantity=quantity,
                        unit_price=unit_price,
                        subtotal=subtotal
                    )
                    db.session.add(new_item)
                    
                    # 减少商品库存
                    old_stock = product.stock_quantity
                    product.stock_quantity -= quantity
                    
                    # 记录库存变动
                    adjustment = StockAdjustment(
                        adjustment_type='product',
                        product_id=product.id,
                        quantity_before=old_stock,
                        quantity_after=product.stock_quantity,
                        adjustment_quantity=-quantity,
                        reason=f'订单新增项: 订单号 {order.order_number}',
                        created_by=current_user.id
                    )
                    db.session.add(adjustment)
                
                # 累计订单总金额
                total_amount += subtotal
            
            # 处理删除的订单项
            for item_id, item in existing_items.items():
                if item_id not in submitted_item_ids:
                    # 归还库存
                    product = Product.query.get(item.product_id)
                    old_stock = product.stock_quantity
                    product.stock_quantity += item.quantity
                    
                    # 记录库存变动
                    adjustment = StockAdjustment(
                        adjustment_type='product',
                        product_id=product.id,
                        quantity_before=old_stock,
                        quantity_after=product.stock_quantity,
                        adjustment_quantity=item.quantity,
                        reason=f'订单删除项: 订单号 {order.order_number}',
                        created_by=current_user.id
                    )
                    db.session.add(adjustment)
                    
                    # 删除订单项
                    db.session.delete(item)
            
            # 设置订单总金额
            order.total_amount = total_amount
            
            db.session.commit()
            flash('订单更新成功', 'success')
            return redirect(url_for('order.detail', id=order.id))
    
    return render_template('order/form.html', form=form, products=products, order=order, order_items=order_items, title='编辑订单')

@order_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    """删除订单"""
    order = Order.query.get_or_404(id)
    
    # 获取所有订单项
    order_items = OrderItem.query.filter_by(order_id=order.id).all()
    
    # 如果订单不是"已取消"状态，恢复库存
    if order.status != '已取消':
        for item in order_items:
            # 归还库存
            product = Product.query.get(item.product_id)
            old_stock = product.stock_quantity
            product.stock_quantity += item.quantity
            
            # 记录库存变动
            adjustment = StockAdjustment(
                adjustment_type='product',
                product_id=product.id,
                quantity_before=old_stock,
                quantity_after=product.stock_quantity,
                adjustment_quantity=item.quantity,
                reason=f'订单删除: 订单号 {order.order_number}',
                created_by=current_user.id
            )
            db.session.add(adjustment)
    
    # 删除订单和关联的订单项
    db.session.delete(order)  # 这会级联删除订单项
    db.session.commit()
    
    flash('订单删除成功', 'success')
    return redirect(url_for('order.list'))

@order_bp.route('/<int:id>/outbound_slip')
@login_required
def outbound_slip(id):
    """打印出库单"""
    order = Order.query.get_or_404(id)
    return render_template('order/outbound_slip.html', order=order)

@order_bp.route('/<int:id>/update_status', methods=['POST'])
@login_required
def update_status(id):
    """更新订单状态"""
    order = Order.query.get_or_404(id)
    
    status = request.form.get('status')
    if status in ['待支付', '已支付', '已发货', '已完成', '已取消']:
        # 如果从其他状态改为"已取消"，恢复库存
        if status == '已取消' and order.status != '已取消':
            for item in order.order_items:
                # 归还库存
                product = Product.query.get(item.product_id)
                old_stock = product.stock_quantity
                product.stock_quantity += item.quantity
                
                # 记录库存变动
                adjustment = StockAdjustment(
                    adjustment_type='product',
                    product_id=product.id,
                    quantity_before=old_stock,
                    quantity_after=product.stock_quantity,
                    adjustment_quantity=item.quantity,
                    reason=f'订单取消: 订单号 {order.order_number}',
                    created_by=current_user.id
                )
                db.session.add(adjustment)
        
        # 如果从"已取消"状态改为其他状态，重新扣减库存
        elif order.status == '已取消' and status != '已取消':
            for item in order.order_items:
                product = Product.query.get(item.product_id)
                
                # 检查库存
                if item.quantity > product.stock_quantity:
                    flash(f'无法恢复订单: 商品 "{product.name}" 库存不足: 需要 {item.quantity}, 实际 {product.stock_quantity}', 'danger')
                    return redirect(url_for('order.detail', id=id))
                
                # 减少库存
                old_stock = product.stock_quantity
                product.stock_quantity -= item.quantity
                
                # 记录库存变动
                adjustment = StockAdjustment(
                    adjustment_type='product',
                    product_id=product.id,
                    quantity_before=old_stock,
                    quantity_after=product.stock_quantity,
                    adjustment_quantity=-item.quantity,
                    reason=f'订单恢复: 订单号 {order.order_number}',
                    created_by=current_user.id
                )
                db.session.add(adjustment)
        
        order.status = status
        db.session.commit()
        flash('订单状态更新成功', 'success')
    else:
        flash('无效的订单状态', 'danger')
    
    return redirect(url_for('order.detail', id=id))
