from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from app import db
from models import RawMaterial, StockAdjustment
from forms import RawMaterialForm, StockAdjustmentForm

raw_material_bp = Blueprint('raw_material', __name__, url_prefix='/raw-materials')

@raw_material_bp.route('/')
@login_required
def list():
    """原材料列表"""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # 搜索功能
    search = request.args.get('search', '')
    if search:
        raw_materials = RawMaterial.query.filter(
            RawMaterial.name.like(f'%{search}%') | 
            RawMaterial.unit.like(f'%{search}%')
        ).paginate(page=page, per_page=per_page)
    else:
        raw_materials = RawMaterial.query.paginate(page=page, per_page=per_page)
    
    return render_template('raw_material/list.html', raw_materials=raw_materials, search=search)

@raw_material_bp.route('/<int:id>')
@login_required
def detail(id):
    """原材料详情"""
    raw_material = RawMaterial.query.get_or_404(id)
    
    # 获取库存调整历史
    adjustments = StockAdjustment.query.filter(
        StockAdjustment.adjustment_type == 'raw_material',
        StockAdjustment.raw_material_id == id
    ).order_by(StockAdjustment.adjustment_date.desc()).limit(5).all()
    
    # 获取采购历史
    purchases = raw_material.purchases
    
    return render_template(
        'raw_material/detail.html', 
        raw_material=raw_material, 
        adjustments=adjustments,
        purchases=purchases
    )

@raw_material_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """添加原材料"""
    form = RawMaterialForm()
    
    if form.validate_on_submit():
        raw_material = RawMaterial(
            name=form.name.data,
            unit=form.unit.data,
            stock_quantity=form.stock_quantity.data,
            unit_cost=form.unit_cost.data,
            safety_stock=form.safety_stock.data
        )
        db.session.add(raw_material)
        db.session.commit()
        
        flash('原材料添加成功', 'success')
        return redirect(url_for('raw_material.list'))
    
    return render_template('raw_material/form.html', form=form, title='添加原材料')

@raw_material_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    """编辑原材料"""
    raw_material = RawMaterial.query.get_or_404(id)
    form = RawMaterialForm(obj=raw_material)
    
    if form.validate_on_submit():
        # 记录库存变化
        if raw_material.stock_quantity != form.stock_quantity.data:
            adjustment = StockAdjustment(
                adjustment_type='raw_material',
                raw_material_id=raw_material.id,
                quantity_before=raw_material.stock_quantity,
                quantity_after=form.stock_quantity.data,
                adjustment_quantity=form.stock_quantity.data - raw_material.stock_quantity,
                reason='通过原材料编辑页面手动调整',
                created_by=current_user.id
            )
            db.session.add(adjustment)
        
        raw_material.name = form.name.data
        raw_material.unit = form.unit.data
        raw_material.stock_quantity = form.stock_quantity.data
        raw_material.unit_cost = form.unit_cost.data
        raw_material.safety_stock = form.safety_stock.data
        
        db.session.commit()
        flash('原材料更新成功', 'success')
        return redirect(url_for('raw_material.list'))
    
    return render_template('raw_material/form.html', form=form, raw_material=raw_material, title='编辑原材料')

@raw_material_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    """删除原材料"""
    raw_material = RawMaterial.query.get_or_404(id)
    
    # 检查原材料是否有关联采购记录
    if raw_material.purchases:
        flash('无法删除：该原材料已有关联采购记录', 'danger')
        return redirect(url_for('raw_material.list'))
    
    db.session.delete(raw_material)
    db.session.commit()
    flash('原材料删除成功', 'success')
    
    return redirect(url_for('raw_material.list'))

@raw_material_bp.route('/adjust/<int:id>', methods=['GET', 'POST'])
@login_required
def adjust_stock(id):
    """调整原材料库存"""
    raw_material = RawMaterial.query.get_or_404(id)
    form = StockAdjustmentForm()
    
    # 预设调整类型为原材料
    form.adjustment_type.data = 'raw_material'
    form.adjustment_type.render_kw = {'disabled': 'disabled'}
    
    # 隐藏商品选择
    form.product_id.render_kw = {'style': 'display: none;'}
    form.product_id.choices = [(-1, '无')]  # 提供一个空选项避免验证错误
    
    # 预设原材料
    form.raw_material_id.choices = [(raw_material.id, raw_material.name)]
    form.raw_material_id.default = raw_material.id
    form.process()  # 重新处理表单以应用默认值
    form.raw_material_id.render_kw = {'disabled': 'disabled'}
    
    if form.validate_on_submit():
        adjustment = StockAdjustment()
        adjustment.adjustment_type = 'raw_material'
        adjustment.raw_material_id = raw_material.id
        adjustment.quantity_before = raw_material.stock_quantity
        adjustment.quantity_after = raw_material.stock_quantity + form.adjustment_quantity.data
        adjustment.adjustment_quantity = form.adjustment_quantity.data
        # 合并下拉选择的原因和详细说明
        reason_text = form.reason.data
        if form.reason_detail.data:
            reason_text += f": {form.reason_detail.data}"
        adjustment.reason = reason_text
        adjustment.created_by = current_user.id
        
        # 更新原材料库存
        raw_material.stock_quantity += form.adjustment_quantity.data
        
        db.session.add(adjustment)
        db.session.commit()
        
        flash(f'库存调整成功：{raw_material.name} 当前库存 {raw_material.stock_quantity} {raw_material.unit}', 'success')
        return redirect(url_for('raw_material.detail', id=raw_material.id))
    
    return render_template(
        'raw_material/adjust.html', 
        form=form, 
        raw_material=raw_material, 
        title='调整原材料库存'
    )
