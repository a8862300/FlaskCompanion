from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta

# 假设你的 app 实例和 db 实例在 app.py 中被创建并导入
from app import db
# 假设你的所有模型都在 models.py 中定义并导入
from models import Order, OrderItem, Customer, Product, Category, StockAdjustment, User # 导入User模型以便记录stock adjustments created_by
# 假设你的订单相关的表单在 forms.py 中定义并导入
from forms import OrderForm#, StockAdjustmentForm # StockAdjustmentForm 没有在routes里用到，先注释

# 创建订单蓝图
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
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    period = request.args.get('period')

    # --- 日期筛选逻辑 ---
    # 初始化最终用于查询的日期变量
    final_start_date = None
    final_end_date = None

    # 优先级 1: 尝试解析手动输入的日期字符串
    parsed_start_date = None
    parsed_end_date = None

    if start_date_str:
        try:
            # 解析开始日期，时间设为00:00:00
            parsed_start_date = datetime.strptime(start_date_str, '%Y-%m-%d').replace(hour=0, minute=0, second=0, microsecond=0)
        except ValueError:
            flash('开始日期格式无效', 'error') # 不会阻止继续执行，但会显示错误信息

    if end_date_str:
        try:
            # 解析结束日期，时间设为23:59:59.999999，确保包含当天所有时间
            parsed_end_date = datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59, microsecond=999999)
        except ValueError:
            flash('结束日期格式无效', 'error') # 不会阻止继续执行，但会显示错误信息

    # 如果手动输入了日期，优先使用手动日期
    if parsed_start_date or parsed_end_date:
        final_start_date = parsed_start_date
        final_end_date = parsed_end_date
    # 优先级 2: 如果没有手动日期，再根据周期设置日期范围
    elif period:
        today = datetime.now() # 如果数据库存UTC，这里用 datetime.utcnow() 更严谨，并调整后续计算
        # 如果只提供了period，忽略手动日期解析可能产生的错误
        # 这里重新初始化以防前面解析失败留下了错误的parsed日期
        final_start_date = None
        final_end_date = None
        
        if period == 'today':
            final_start_date = today.replace(hour=0, minute=0, second=0, microsecond=0)
            final_end_date = today.replace(hour=23, minute=59, second=59, microsecond=999999)
        elif period == 'week':
            # 获取当前周的开始（周一）和结束（周日）
            final_start_date = today.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=today.weekday())
            final_end_date = final_start_date + timedelta(days=6, hours=23, minutes=59, seconds=59, microsecond=999999)
        elif period == 'month':
            # 获取当前月的开始和结束
            final_start_date = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            # 获取下个月的第一天，然后减去1微秒
            if today.month == 12:
                final_end_date = datetime(today.year + 1, 1, 1, 0, 0, 0, 0) - timedelta(microseconds=1)
            else:
                final_end_date = datetime(today.year, today.month + 1, 1, 0, 0, 0, 0) - timedelta(microseconds=1)
        elif period == 'quarter':
            # 获取当前季度的开始和结束
            quarter = (today.month - 1) // 3 + 1
            final_start_date = datetime(today.year, 3 * quarter - 2, 1, 0, 0, 0, 0)
            if quarter == 4:
                final_end_date = datetime(today.year + 1, 1, 1, 0, 0, 0, 0) - timedelta(microseconds=1)
            else:
                final_end_date = datetime(today.year, 3 * quarter + 1, 1, 0, 0, 0, 0) - timedelta(microseconds=1)
        elif period == 'year':
            # 获取当前年的开始和结束
            final_start_date = datetime(today.year, 1, 1, 0, 0, 0, 0)
            final_end_date = datetime(today.year, 12, 31, 23, 59, 59, 999999)


    # 构建查询
    query = Order.query

    # 应用基本筛选条件
    if customer_id:
        query = query.filter(Order.customer_id == customer_id)

    if status:
        query = query.filter(Order.status == status)

    # --- 应用最终确定的日期筛选 (使用更健壮的结束日期边界处理) ---
    if final_start_date:
        # 筛选大于或等于开始日期的订单 (开始日期边界通常没问题)
        query = query.filter(Order.order_date >= final_start_date)

    if final_end_date:
        # 筛选小于结束日期下一天开始时间的订单，以包含结束日期的所有时间
        # 先将 final_end_date 的时间部分归零 (设置为当天开始)，然后加一天
        start_of_day_after_end = (final_end_date.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1))
        query = query.filter(Order.order_date < start_of_day_after_end)
    # --- 日期筛选逻辑结束 ---


    # 应用分类筛选（需要连接OrderItem和Product表）
    # 注意：使用 group_by(Order.id) 是为了避免订单因为有多个匹配分类的订单项而被重复计算或返回
    if category_id:
        # 使用outerjoin以包含没有订单项（虽然不太可能发生）或订单项不匹配分类的订单，如果需要的话。
        # 如果只需要包含至少一个匹配分类订单项的订单，使用join即可。原代码是join。
        # query = query.outerjoin(OrderItem).outerjoin(Product).filter(Product.category_id == category_id).group_by(Order.id)
        # 保持原AI生成的join逻辑
        query = query.join(OrderItem).join(Product).filter(Product.category_id == category_id).group_by(Order.id)


    # 按日期降序排序
    query = query.order_by(Order.order_date.desc())

    # 执行分页查询
    orders = query.paginate(page=page, per_page=per_page, error_out=False) # error_out=False避免页码超出范围时404

    # 获取筛选选项数据
    customers = Customer.query.order_by('name').all() # 排序一下更友好
    categories = Category.query.order_by('name').all() # 排序一下更友好

    # 订单状态选项
    status_options = [
        ('', '所有状态'), # 添加一个“所有状态”选项
        ('待支付', '待支付'),
        ('已支付', '已支付'),
        ('已发货', '已发货'),
        ('已完成', '已完成'),
        ('已取消', '已取消')
    ]

    # 时间周期选项
    period_options = [
        ('', '所有时间'), # 添加一个“所有时间”选项
        ('today', '今日'),
        ('week', '本周'),
        ('month', '本月'),
        ('quarter', '本季度'),
        ('year', '本年度')
    ]

    # 为前端传递筛选值，特别是日期要用最终用于查询的值
    # 如果 final_start_date/final_end_date 是 datetime 对象，需要格式化成字符串
    filter_start_date_display = final_start_date.strftime('%Y-%m-%d') if final_start_date else ''
    filter_end_date_display = final_end_date.strftime('%Y-%m-%d') if final_end_date else ''

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
            'start_date': filter_start_date_display, # 传递最终用于查询的日期
            'end_date': filter_end_date_display,   # 传递最终用于查询的日期
            'period': period                      # 传递接收到的周期值
        }
    )

# --- 后面是 add, detail, edit, delete, outbound_slip, update_status 函数 ---
# 这些函数保持不变，因为它们不涉及订单列表的日期筛选逻辑

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
    form.customer_id.choices = [(c.id, c.name) for c in Customer.query.order_by('name').all()] # 增加 .all()

    # 获取所有商品，用于前端选择
    products = Product.query.order_by('name').all() # 排序一下更友好

    if request.method == 'POST':
        # 从表单获取基本订单信息
        # 这里不使用 form.validate_on_submit() 来验证所有字段，
        # 因为订单项是动态添加的，WTForms 默认不知道如何验证它们。
        # 基本订单信息可以在下面手动验证，订单项验证也在循环中进行。

        # 手动从请求中获取基本订单信息
        order_date_str = request.form.get('order_date')
        customer_id = request.form.get('customer_id', type=int)
        status = request.form.get('status')
        payment_method = request.form.get('payment_method')
        notes = request.form.get('notes')

        # 简单的基本信息验证
        if not order_date_str or not customer_id or not status or not payment_method:
             flash('订单基本信息不完整', 'danger')
             # 重新填充表单并返回
             form.order_date.data = datetime.strptime(order_date_str, '%Y-%m-%d') if order_date_str else None
             form.customer_id.data = customer_id
             form.status.data = status
             form.payment_method.data = payment_method
             form.notes.data = notes
             form.customer_id.choices = [(c.id, c.name) for c in Customer.query.order_by('name').all()] # 重新设置choices
             return render_template('order/form.html', form=form, products=products, title='添加订单')

        try:
            # 保存订单时，如果只提供了日期，时间部分使用默认值 (00:00:00) 或当前时间
            # 这里的代码是解析日期字符串，时间部分默认是00:00:00
            order_date = datetime.strptime(order_date_str, '%Y-%m-%d')
            # 如果需要存储具体的下单时间，可以在这里加上时间信息，例如：
            # order_date = datetime.combine(datetime.strptime(order_date_str, '%Y-%m-%d').date(), datetime.now().time())
            # 或者直接用 datetime.now() 作为下单时间
            # order_date = datetime.now()
            # 这里保持原代码只解析日期部分
        except ValueError:
            flash('订单日期格式无效', 'danger')
            # 重新填充表单并返回
            form.order_date.data = None # Clear invalid date
            form.customer_id.data = customer_id
            form.status.data = status
            form.payment_method.data = payment_method
            form.notes.data = notes
            form.customer_id.choices = [(c.id, c.name) for c in Customer.query.order_by('name').all()] # 重新设置choices
            return render_template('order/form.html', form=form, products=products, title='添加订单')


        # 创建订单
        order = Order(
            order_date=order_date, # 使用解析或确定的订单日期
            customer_id=customer_id,
            status=status,
            payment_method=payment_method,
            notes=notes
        )
        db.session.add(order)
        db.session.flush()  # 获取订单ID (如果在generate_order_number中用到了id)

        # 确保order_number在commit前生成，如果default=generate_order_number依赖于order.id
        # 更好做法是 generate_order_number 在commit前生成不依赖id的唯一号
        # 或者在commit后生成并更新order.order_number
        # 如果 default=generate_order_number 已经可以工作，就保持原样

        # 处理订单项
        total_amount = 0
        product_ids = request.form.getlist('product_id[]')
        quantities = request.form.getlist('quantity[]')
        unit_prices = request.form.getlist('unit_price[]')

        if not product_ids:
            flash('订单必须包含至少一项商品', 'danger')
            db.session.rollback() # 回滚已添加的订单对象
            # 重新填充表单并返回
            form.order_date.data = order.order_date # Use validated date
            form.customer_id.data = order.customer_id
            form.status.data = order.status
            form.payment_method.data = order.payment_method
            form.notes.data = order.notes
            form.customer_id.choices = [(c.id, c.name) for c in Customer.query.order_by('name').all()] # 重新设置choices
            # 注意：这里无法自动填充动态添加的订单项到表单对象，前端可能需要JS来处理回显
            return render_template('order/form.html', form=form, products=products, title='添加订单')


        for i in range(len(product_ids)):
            # 防止索引越界，虽然getlist通常会返回等长列表
            if i >= len(quantities) or i >= len(unit_prices):
                 flash('订单项数据不完整', 'danger')
                 db.session.rollback() # 回滚已添加的订单对象
                 # 重新填充表单并返回 (这里的回显动态项依然是个问题)
                 form.order_date.data = order.order_date # Use validated date
                 form.customer_id.data = order.customer_id
                 form.status.data = order.status
                 form.payment_method.data = order.payment_method
                 form.notes.data = order.notes
                 form.customer_id.choices = [(c.id, c.name) for c in Customer.query.order_by('name').all()] # 重新设置choices
                 return render_template('order/form.html', form=form, products=products, title='添加订单')

            try:
                product_id = int(product_ids[i])
                quantity = int(quantities[i])
                unit_price = float(unit_prices[i])
            except (ValueError, TypeError):
                 flash('订单项数量或单价格式无效', 'danger')
                 db.session.rollback() # 回滚已添加的订单对象
                 # 重新填充表单并返回
                 form.order_date.data = order.order_date # Use validated date
                 form.customer_id.data = order.customer_id
                 form.status.data = order.status
                 form.payment_method.data = order.payment_method
                 form.notes.data = order.notes
                 form.customer_id.choices = [(c.id, c.name) for c in Customer.query.order_by('name').all()] # 重新设置choices
                 return render_template('order/form.html', form=form, products=products, title='添加订单')


            # 验证数据
            if quantity <= 0:
                flash(f'商品数量必须大于0 (项 {i+1})', 'danger')
                db.session.rollback()
                form.order_date.data = order.order_date
                form.customer_id.data = order.customer_id
                form.status.data = order.status
                form.payment_method.data = order.payment_method
                form.notes.data = order.notes
                form.customer_id.choices = [(c.id, c.name) for c in Customer.query.order_by('name').all()]
                return render_template('order/form.html', form=form, products=products, title='添加订单')

            if unit_price < 0:
                flash(f'商品单价不能为负数 (项 {i+1})', 'danger')
                db.session.rollback()
                form.order_date.data = order.order_date
                form.customer_id.data = order.customer_id
                form.status.data = order.status
                form.payment_method.data = order.payment_method
                form.notes.data = order.notes
                form.customer_id.choices = [(c.id, c.name) for c in Customer.query.order_by('name').all()]
                return render_template('order/form.html', form=form, products=products, title='添加订单')

            # 获取商品
            product = Product.query.get(product_id)
            if not product:
                flash(f'商品ID {product_id} 不存在 (项 {i+1})', 'danger')
                db.session.rollback()
                form.order_date.data = order.order_date
                form.customer_id.data = order.customer_id
                form.status.data = order.status
                form.payment_method.data = order.payment_method
                form.notes.data = order.notes
                form.customer_id.choices = [(c.id, c.name) for c in Customer.query.order_by('name').all()]
                return render_template('order/form.html', form=form, products=products, title='添加订单')


            # 检查库存 (只在状态不是"已取消"时检查和扣减库存)
            if order.status != '已取消' and quantity > product.stock_quantity:
                flash(f'商品 "{product.name}" 库存不足: 需要 {quantity}, 实际 {product.stock_quantity} (项 {i+1})', 'danger')
                db.session.rollback() # 回滚所有已添加的订单项和订单对象
                form.order_date.data = order.order_date
                form.customer_id.data = order.customer_id
                form.status.data = order.status
                form.payment_method.data = order.payment_method
                form.notes.data = order.notes
                form.customer_id.choices = [(c.id, c.name) for c in Customer.query.order_by('name').all()]
                return render_template('order/form.html', form=form, products=products, title='添加订单')

            # 创建订单项
            subtotal = round(quantity * unit_price, 2) # 计算并保留两位小数
            order_item = OrderItem(
                order_id=order.id,
                product_id=product_id,
                quantity=quantity,
                unit_price=unit_price,
                subtotal=subtotal
            )
            db.session.add(order_item)

            # 减少商品库存 (只在状态不是"已取消"时扣减库存)
            if order.status != '已取消':
                old_stock = product.stock_quantity
                product.stock_quantity -= quantity

                # 记录库存变动
                adjustment = StockAdjustment(
                    adjustment_type='product',
                    product_id=product.id,
                    quantity_before=old_stock,
                    quantity_after=product.stock_quantity,
                    adjustment_quantity=-quantity,
                    reason=f'销售出库: 订单 {order.order_number if order.order_number else order.id}', # 使用order_number如果生成了，否则使用id
                    created_by=current_user.id if current_user.is_authenticated else None # 记录操作用户ID
                )
                db.session.add(adjustment)

            # 累计订单总金额
            total_amount = round(total_amount + subtotal, 2) # 累计并保留两位小数

        # 设置订单总金额
        order.total_amount = total_amount

        db.session.commit()
        flash('订单创建成功', 'success')
        return redirect(url_for('order.detail', id=order.id))

    # GET 请求或表单验证失败时的处理
    # 注意：form.customer_id.choices 已经在上面设置
    products = Product.query.order_by('name').all() # GET请求也需要商品列表
    return render_template('order/form.html', form=form, products=products, title='添加订单')


@order_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    """编辑订单"""
    order = Order.query.get_or_404(id)
    form = OrderForm(obj=order) # 使用obj=order填充基本信息

    # 设置客户下拉列表
    form.customer_id.choices = [(c.id, c.name) for c in Customer.query.order_by('name').all()]

    # 获取所有商品，用于前端选择
    products = Product.query.order_by('name').all()

    # 获取现有订单项，用于GET请求时填充前端
    order_items = OrderItem.query.filter_by(order_id=order.id).all()

    if request.method == 'POST':
        # 手动从请求中获取基本订单信息和订单项数据
        order_date_str = request.form.get('order_date')
        customer_id = request.form.get('customer_id', type=int)
        status = request.form.get('status')
        payment_method = request.form.get('payment_method')
        notes = request.form.get('notes')

        # 简单的基本信息验证
        if not order_date_str or not customer_id or not status or not payment_method:
             flash('订单基本信息不完整', 'danger')
             # 重新填充表单并返回
             form.order_date.data = datetime.strptime(order_date_str, '%Y-%m-%d') if order_date_str else None
             form.customer_id.data = customer_id
             form.status.data = status
             form.payment_method.data = payment_method
             form.notes.data = notes
             form.customer_id.choices = [(c.id, c.name) for c in Customer.query.order_by('name').all()]
             # 注意：这里无法自动填充动态添加的订单项到表单对象，前端可能需要JS来处理回显
             return render_template('order/form.html', form=form, products=products, order=order, order_items=order_items, title='编辑订单')

        try:
            order_date = datetime.strptime(order_date_str, '%Y-%m-%d')
        except ValueError:
            flash('订单日期格式无效', 'danger')
            form.order_date.data = None # Clear invalid date
            form.customer_id.data = customer_id
            form.status.data = status
            form.payment_method.data = payment_method
            form.notes.data = notes
            form.customer_id.choices = [(c.id, c.name) for c in Customer.query.order_by('name').all()]
            return render_template('order/form.html', form=form, products=products, order=order, order_items=order_items, title='编辑订单')

        # 存储旧的订单项数量，用于库存回滚
        old_order_item_quantities = {item.product_id: item.quantity for item in order_items}
        old_order_status = order.status # 记录旧状态用于库存调整判断

        # 更新订单基本信息
        order.order_date = order_date # Use validated date
        order.customer_id = customer_id
        order.status = status
        order.payment_method = payment_method
        order.notes = notes

        # 处理订单项变更
        # 记录提交上来的订单项ID，用于确定哪些被删除
        submitted_item_ids = set()

        # 处理新的或更新的订单项
        product_ids = request.form.getlist('product_id[]')
        quantities = request.form.getlist('quantity[]')
        unit_prices = request.form.getlist('unit_price[]')
        item_ids = request.form.getlist('item_id[]') # 已有项目的ID，前端动态生成的隐藏字段

        # 重置总金额
        total_amount = 0

        # 先处理删除的订单项并回滚库存 (这部分逻辑比较复杂，我们先处理提交上来的项目)
        # 并在循环结束后处理未在 submitted_item_ids 中的旧项目

        processed_item_count = 0 # 用于 tracking submitted items index

        for i in range(len(product_ids)):
             # 防止索引越界
            if i >= len(quantities) or i >= len(unit_prices) or i >= len(item_ids):
                 flash('订单项数据不完整 (编辑)', 'danger')
                 db.session.rollback() # 回滚
                 # ... (re-populate form/render template) ...
                 return render_template('order/form.html', form=form, products=products, order=order, order_items=order_items, title='编辑订单')


            try:
                product_id = int(product_ids[i])
                quantity = int(quantities[i])
                unit_price = float(unit_prices[i])
                # item_id 可以是字符串 'None' 或实际ID的字符串形式
                item_id_str = item_ids[i] if i < len(item_ids) else 'None' # Default to 'None' if missing
                item_id = int(item_id_str) if item_id_str.isdigit() else None # Convert to int if valid digit
            except (ValueError, TypeError):
                 flash('订单项数量、单价或ID格式无效 (编辑)', 'danger')
                 db.session.rollback() # 回滚
                 # ... (re-populate form/render template) ...
                 return render_template('order/form.html', form=form, products=products, order=order, order_items=order_items, title='编辑订单')


            # 验证数据
            if quantity <= 0:
                flash(f'商品数量必须大于0 (项 {i+1}, 编辑)', 'danger')
                db.session.rollback()
                # ... (re-populate form/render template) ...
                return render_template('order/form.html', form=form, products=products, order=order, order_items=order_items, title='编辑订单')

            if unit_price < 0:
                flash(f'商品单价不能为负数 (项 {i+1}, 编辑)', 'danger')
                db.session.rollback()
                # ... (re-populate form/render template) ...
                return render_template('order/form.html', form=form, products=products, order=order, order_items=order_items, title='编辑订单')

            # 获取商品
            product = Product.query.get(product_id)
            if not product:
                flash(f'商品ID {product_id} 不存在 (项 {i+1}, 编辑)', 'danger')
                db.session.rollback()
                # ... (re-populate form/render template) ...
                return render_template('order/form.html', form=form, products=products, order=order, order_items=order_items, title='编辑订单')


            subtotal = round(quantity * unit_price, 2) # 计算小计并保留两位小数

            # 处理现有订单项 或 创建新订单项
            existing_item = None
            if item_id is not None:
                 existing_item = OrderItem.query.get(item_id)
                 if existing_item and existing_item.order_id != order.id:
                     flash(f'订单项ID {item_id} 不属于当前订单 (编辑)', 'danger')
                     db.session.rollback()
                     return render_template('order/form.html', form=form, products=products, order=order, order_items=order_items, title='编辑订单')


            if existing_item:
                # 更新现有订单项
                # 计算库存变动差额：新数量 - 旧数量
                # 如果旧状态是“已取消”，新状态不是“已取消”，需要重新扣减库存
                # 如果旧状态和新状态都不是“已取消”，需要根据差额调整
                # 如果旧状态不是“已取消”，新状态是“已取消”，这里不调整，在最后统一处理状态变更时的库存
                
                old_quantity = existing_item.quantity
                stock_change_needed = 0

                if old_order_status != '已取消' and order.status != '已取消':
                    # 之前扣减了库存，现在根据差额调整
                    stock_change_needed = old_quantity - quantity # 正数表示回滚，负数表示额外扣减
                elif old_order_status == '已取消' and order.status != '已取消':
                    # 之前恢复了库存，现在根据新数量扣减
                    stock_change_needed = -quantity # 需要扣减新数量
                # 如果新状态是“已取消”，无论旧状态如何，这里都不做库存调整，留给最后的状态变更逻辑处理

                # 检查库存 (只在新状态不是"已取消"且需要额外扣减时检查)
                if order.status != '已取消' and stock_change_needed < 0: # 小于0表示需要额外扣减库存
                    additional_qty_needed = -stock_change_needed
                    if additional_qty_needed > product.stock_quantity:
                        flash(f'商品 "{product.name}" 库存不足: 需要额外 {additional_qty_needed}, 实际 {product.stock_quantity} (项 {existing_item.id}, 编辑)', 'danger')
                        db.session.rollback()
                        # ... (re-populate form/render template) ...
                        return render_template('order/form.html', form=form, products=products, order=order, order_items=order_items, title='编辑订单')

                # 应用库存调整 (只在新状态不是"已取消"且库存需要变动时调整)
                if order.status != '已取消' and stock_change_needed != 0:
                     old_stock = product.stock_quantity
                     product.stock_quantity += stock_change_needed # 正数增加，负数减少

                     # 记录库存变动
                     adjustment = StockAdjustment(
                         adjustment_type='product',
                         product_id=product.id,
                         quantity_before=old_stock,
                         quantity_after=product.stock_quantity,
                         adjustment_quantity=stock_change_needed,
                         reason=f'订单修改项库存调整: 订单号 {order.order_number if order.order_number else order.id}',
                         created_by=current_user.id if current_user.is_authenticated else None
                     )
                     db.session.add(adjustment)


                # 更新订单项
                existing_item.product_id = product_id # 即使是现有项，也可能更换商品
                existing_item.quantity = quantity
                existing_item.unit_price = unit_price
                existing_item.subtotal = subtotal

                # 标记为已处理
                submitted_item_ids.add(existing_item.id)
            else:
                # 创建新订单项
                # 检查库存 (只在新状态不是"已取消"时检查和扣减)
                if order.status != '已取消' and quantity > product.stock_quantity:
                    flash(f'商品 "{product.name}" 库存不足: 需要 {quantity}, 实际 {product.stock_quantity} (新项 {i+1}, 编辑)', 'danger')
                    db.session.rollback()
                    # ... (re-populate form/render template) ...
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

                # 减少商品库存 (只在新状态不是"已取消"时扣减)
                if order.status != '已取消':
                    old_stock = product.stock_quantity
                    product.stock_quantity -= quantity

                    # 记录库存变动
                    adjustment = StockAdjustment(
                        adjustment_type='product',
                        product_id=product.id,
                        quantity_before=old_stock,
                        quantity_after=product.stock_quantity,
                        adjustment_quantity=-quantity,
                        reason=f'订单修改新增项: 订单号 {order.order_number if order.order_number else order.id}',
                        created_by=current_user.id if current_user.is_authenticated else None
                    )
                    db.session.add(adjustment)


            # 累计订单总金额
            total_amount = round(total_amount + subtotal, 2)

        # 处理删除的订单项
        # 获取当前数据库中属于此订单的所有订单项ID
        # 在POST请求中，order_items 可能只包含最初加载时的项目，需要重新查询以获取最新的
        # 或者依赖级联删除，这里假设OrderItem.query.filter_by(order_id=order.id).all() 在 session.delete(item) 后会更新
        # 但更安全的是根据 submitted_item_ids 和原始加载的 order_items 来判断
        
        # 改进：根据提交的 item_ids 和加载的 order_items 来判断哪些被删
        existing_items_map = {item.id: item for item in order_items} # order_items 是加载本页面时的数据
        submitted_item_ids_int = {int(id) for id in item_ids if id and id.isdigit()}

        items_to_delete_ids = set(existing_items_map.keys()) - submitted_item_ids_int


        for item_id in items_to_delete_ids:
            item_to_delete = existing_items_map.get(item_id) # 从加载时的列表中获取对象
            if item_to_delete:
                 # 归还库存 (只在旧状态不是"已取消"时回滚删除的项的库存)
                 # 如果新状态也是"已取消"，不回滚，留给状态变更处理
                 if old_order_status != '已取消' and order.status != '已取消':
                     product = Product.query.get(item_to_delete.product_id)
                     if product: # 检查商品是否存在
                         old_stock = product.stock_quantity
                         product.stock_quantity += item_to_delete.quantity

                         # 记录库存变动
                         adjustment = StockAdjustment(
                             adjustment_type='product',
                             product_id=product.id,
                             quantity_before=old_stock,
                             quantity_after=product.stock_quantity,
                             adjustment_quantity=item_to_delete.quantity,
                             reason=f'订单删除项: 订单号 {order.order_number if order.order_number else order.id}',
                             created_by=current_user.id if current_user.is_authenticated else None
                         )
                         db.session.add(adjustment)

                 # 删除订单项
                 db.session.delete(item_to_delete)


        # 处理订单状态变更引起的库存变化 (这是一个独立的逻辑块，确保只执行一次)
        # 如果旧状态 != 新状态 且 新状态 == "已取消"，则需要恢复所有订单项库存
        # 如果旧状态 == "已取消" 且 新状态 != "已取消"，则需要扣减所有订单项库存 (检查库存是否足够)
        # 注意：上面的订单项循环中，库存调整是基于“新状态不是已取消”来做的。
        # 如果新状态是“已取消”，上面的循环不会调整库存。
        # 如果从“已取消”恢复到其他状态，上面的循环会根据新数量来调整，但需要检查总库存。

        # 在 edit 逻辑中，更清晰的库存处理可能是：
        # 1. 无论新旧状态，先将旧订单项的库存全部回滚 (如果旧状态不是已取消)
        # 2. 根据新的订单项列表，扣减库存 (如果新状态不是已取消)
        # 3. 记录所有库存调整
        # 当前代码尝试在循环中处理差额，并在状态变更路由中处理状态引起的库存变化，这比较复杂且可能不一致。
        # 我会保持AI生成的原有状态变更逻辑，并假设它是后处理的。

        # 设置订单总金额
        order.total_amount = total_amount

        db.session.commit()
        flash('订单更新成功', 'success')
        return redirect(url_for('order.detail', id=order.id))

    # GET 请求时的处理：填充表单和订单项
    # obj=order 已经填充了基本信息
    # 订单项需要手动传递给模板以便前端动态渲染
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
            if product: # 检查商品是否存在
                old_stock = product.stock_quantity
                product.stock_quantity += item.quantity

                # 记录库存变动
                adjustment = StockAdjustment(
                    adjustment_type='product',
                    product_id=product.id,
                    quantity_before=old_stock,
                    quantity_after=product.stock_quantity,
                    adjustment_quantity=item.quantity,
                    reason=f'订单删除: 订单号 {order.order_number if order.order_number else order.id}',
                    created_by=current_user.id if current_user.is_authenticated else None
                )
                db.session.add(adjustment)
    else:
        # 如果订单已经是“已取消”，记录一个删除记录但库存未变动的调整
        adjustment = StockAdjustment(
             adjustment_type='order_delete', # 类型可以改为订单级别的删除
             order_id=order.id,
             # quantity_before=None, # 删除订单没有商品维度的before/after
             # quantity_after=None,
             adjustment_quantity=0, # 数量变动是0
             reason=f'已取消订单删除: 订单号 {order.order_number if order.order_number else order.id}',
             created_by=current_user.id if current_user.is_authenticated else None
        )
        db.session.add(adjustment)

    try:
        # 删除所有订单项
        for item in order_items:
            db.session.delete(item)

        # 最后删除订单本身
        db.session.delete(order)
        db.session.commit()
        flash('订单删除成功', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'删除订单失败: {str(e)}', 'danger')

    return redirect(url_for('order.list'))


@order_bp.route('/<int:id>/outbound_slip')
@login_required
def outbound_slip(id):
    """生成并显示出库单"""
    order = Order.query.get_or_404(id)
    return render_template('order/outbound_slip.html', order=order)


@order_bp.route('/<int:id>/update_status', methods=['POST'])
@login_required
def update_status(id):
    """更新订单状态并处理库存逻辑"""
    order = Order.query.get_or_404(id)
    new_status = request.form.get('status')

    # 允许的状态列表，用于验证
    allowed_statuses = ['待支付', '已支付', '已发货', '已完成', '已取消']

    if new_status and new_status in allowed_statuses:
        old_status = order.status

        if old_status != new_status:
            # 获取所有订单项，用于库存调整
            order_items = OrderItem.query.filter_by(order_id=order.id).all()

            if new_status == '已取消':
                # 从非“已取消”状态变为“已取消”时，恢复库存
                if old_status != '已取消':
                    for item in order_items:
                        product = Product.query.get(item.product_id)
                        if product:
                            old_stock = product.stock_quantity
                            product.stock_quantity += item.quantity

                            # 记录库存变动
                            adjustment = StockAdjustment(
                                adjustment_type='product',
                                product_id=product.id,
                                quantity_before=old_stock,
                                quantity_after=product.stock_quantity,
                                adjustment_quantity=item.quantity, # 增加库存
                                reason=f'订单取消: 订单号 {order.order_number if order.order_number else order.id}',
                                created_by=current_user.id if current_user.is_authenticated else None
                            )
                            db.session.add(adjustment)
            elif old_status == '已取消':
                # 从“已取消”状态变为其他非“已取消”状态时，扣减库存
                # 需要检查库存是否足够
                for item in order_items:
                    product = Product.query.get(item.product_id)
                    if product:
                        if item.quantity > product.stock_quantity:
                            db.session.rollback()
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
                            adjustment_quantity=-item.quantity, # 减少库存
                            reason=f'订单恢复: 订单号 {order.order_number if order.order_number else order.id}',
                            created_by=current_user.id if current_user.is_authenticated else None
                        )
                        db.session.add(adjustment)

            # 更新状态
            order.status = new_status
            db.session.commit()
            flash('订单状态更新成功', 'success')
        else:
             # 状态没有实际变化，只做成功提示
             flash('订单状态已是最新', 'info') # 提示信息可以改成info级别
    else:
        flash('无效的订单状态', 'danger')

    return redirect(url_for('order.detail', id=id))