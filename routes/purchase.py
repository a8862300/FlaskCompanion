from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from datetime import datetime

from app import db
from models import RawMaterialPurchase, RawMaterial, Supplier, StockAdjustment
from forms import RawMaterialPurchaseForm

purchase_bp = Blueprint('purchase', __name__, url_prefix='/purchases')

@purchase_bp.route('/')
@login_required
def list():
    """原材料采购列表"""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # 筛选条件
    supplier_id = request.args.get('supplier_id', type=int)
    raw_material_id = request.args.get('raw_material_id', type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # 转换日期字符串为日期对象（如果提供）
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
        # 设置为当天结束时间
        end_date = end_date.replace(hour=23, minute=59, second=59)
    
    # 构建查询
    query = RawMaterialPurchase.query
    
    # 应用筛选条件
    if supplier_id:
        query = query.filter(RawMaterialPurchase.supplier_id == supplier_id)
    
    if raw_material_id:
        query = query.filter(RawMaterialPurchase.raw_material_id == raw_material_id)
    
    if start_date:
        query = query.filter(RawMaterialPurchase.purchase_date >= start_date)
    
    if end_date:
        query = query.filter(RawMaterialPurchase.purchase_date <= end_date)
    
    # 按日期降序排序
    query = query.order_by(RawMaterialPurchase.purchase_date.desc())
    
    # 执行分页查询
    purchases = query.paginate(page=page, per_page=per_page)
    
    # 获取筛选选项数据
    suppliers = Supplier.query.all()
    raw_materials = RawMaterial.query.all()
    
    return render_template(
        'purchase/list.html', 
        purchases=purchases, 
        suppliers=suppliers,
        raw_materials=raw_materials,
        filter={
            'supplier_id': supplier_id,
            'raw_material_id': raw_material_id,
            'start_date': start_date.strftime('%Y-%m-%d') if start_date else '',
            'end_date': end_date.strftime('%Y-%m-%d') if end_date else ''
        }
    )

@purchase_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """添加原材料采购记录"""
    form = RawMaterialPurchaseForm()
    
    # 设置下拉列表选项
    form.raw_material_id.choices = [(m.id, m.name) for m in RawMaterial.query.order_by('name')]
    form.supplier_id.choices = [(s.id, s.name) for s in Supplier.query.order_by('name')]
    
    if form.validate_on_submit():
        # 获取原材料对象以便更新库存
        raw_material = RawMaterial.query.get(form.raw_material_id.data)
        
        # 计算采购总价
        total_price = form.quantity.data * form.unit_price.data
        
        # 创建采购记录
        purchase = RawMaterialPurchase(
            purchase_date=form.purchase_date.data,
            raw_material_id=form.raw_material_id.data,
            supplier_id=form.supplier_id.data,
            quantity=form.quantity.data,
            unit_price=form.unit_price.data,
            total_price=total_price
        )
        
        # 更新原材料库存和单位成本
        old_stock = raw_material.stock_quantity
        raw_material.stock_quantity += form.quantity.data
        
        # 创建库存调整记录
        adjustment = StockAdjustment(
            adjustment_type='raw_material',
            raw_material_id=raw_material.id,
            quantity_before=old_stock,
            quantity_after=raw_material.stock_quantity,
            adjustment_quantity=form.quantity.data,
            reason=f'采购入库：{form.quantity.data} {raw_material.unit}',
            created_by=current_user.id
        )
        
        # 如果单位成本不同，计算新的平均单位成本
        if raw_material.unit_cost != form.unit_price.data:
            # 计算加权平均成本
            total_value = (old_stock * raw_material.unit_cost) + (form.quantity.data * form.unit_price.data)
            raw_material.unit_cost = total_value / raw_material.stock_quantity
        
        db.session.add(purchase)
        db.session.add(adjustment)
        db.session.commit()
        
        flash('原材料采购记录添加成功', 'success')
        return redirect(url_for('purchase.list'))
    
    return render_template('purchase/form.html', form=form, title='添加原材料采购记录')
