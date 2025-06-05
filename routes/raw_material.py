# raw_material.py (完整替换)

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from models import db
from models import RawMaterial, StockAdjustment, Product, RawMaterialPurchase, Supplier
from forms import RawMaterialForm, StockAdjustmentForm
from datetime import datetime # 确保 datetime 在这里被导入

raw_material_bp = Blueprint('raw_material', __name__, url_prefix='/raw_material')

@raw_material_bp.route('/list')
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
    ).order_by(StockAdjustment.adjustment_date.desc()).all()

    # 获取采购历史 (使用 RawMaterialPurchase 模型直接查询)
    purchases = RawMaterialPurchase.query.filter_by(raw_material_id=id).order_by(RawMaterialPurchase.purchase_date.desc()).all()

    return render_template('raw_material/detail.html', 
                           raw_material=raw_material, 
                           adjustments=adjustments,
                           purchases=purchases)


@raw_material_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """添加原材料"""
    form = RawMaterialForm()
    # 填充供应商下拉列表
    form.supplier_id.choices = [(s.id, s.name) for s in Supplier.query.order_by(Supplier.name).all()]
    form.supplier_id.choices.insert(0, (0, '')) # 允许为空选择

    if form.validate_on_submit():
        raw_material = RawMaterial(
            name=form.name.data,
            unit=form.unit.data,
            stock_quantity=form.stock_quantity.data,
            unit_cost=form.unit_cost.data,
            safety_stock=form.safety_stock.data or 0,
            supplier_id=form.supplier_id.data if form.supplier_id.data != 0 else None
        )
        db.session.add(raw_material)
        db.session.commit()
        flash('原材料添加成功！', 'success')
        return redirect(url_for('raw_material.list'))
    return render_template('raw_material/form.html', form=form, title='添加原材料')

@raw_material_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    """编辑原材料"""
    raw_material = RawMaterial.query.get_or_404(id)
    form = RawMaterialForm(obj=raw_material) # 预填充表单
    # 填充供应商下拉列表
    form.supplier_id.choices = [(s.id, s.name) for s in Supplier.query.order_by(Supplier.name).all()]
    form.supplier_id.choices.insert(0, (0, '')) # 允许为空选择

    if form.validate_on_submit():
        form.populate_obj(raw_material)
        # 确保安全库存为空时设为0
        raw_material.safety_stock = form.safety_stock.data or 0
        raw_material.supplier_id = form.supplier_id.data if form.supplier_id.data != 0 else None
        db.session.commit()
        flash('原材料更新成功！', 'success')
        return redirect(url_for('raw_material.list'))
    return render_template('raw_material/form.html', form=form, title='编辑原材料')


@raw_material_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    """删除原材料"""
    raw_material = RawMaterial.query.get_or_404(id)
    try:
        db.session.delete(raw_material)
        db.session.commit()
        flash(f'原材料 "{raw_material.name}" 已删除！', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'删除原材料 "{raw_material.name}" 失败：{str(e)}', 'danger')
    return redirect(url_for('raw_material.list'))


@raw_material_bp.route('/adjust_stock/<int:id>', methods=['GET', 'POST'])
@login_required
def adjust_stock(id):
    """调整原材料库存数量"""
    raw_material = RawMaterial.query.get_or_404(id)
    form = StockAdjustmentForm()

    # 预设表单字段
    form.adjustment_type.data = 'raw_material' # 强制设置为 'raw_material'
    
    # 隐藏 product_id 字段
    form.product_id.render_kw = {'style': 'display: none;'}
    # 填充 product_id 的 choices，以满足 DataRequired，但由于是隐藏的，不会显示
    form.product_id.choices = [(0, 'N/A')] # 确保有选项，即使是隐藏的

    # 设置原材料ID的choices并预设，并禁用
    form.raw_material_id.choices = [(raw_material.id, raw_material.name)]
    form.raw_material_id.data = raw_material.id
    form.raw_material_id.render_kw = {'disabled': 'disabled'} # 禁用以便用户不能修改
    
    # 在POST请求中处理表单提交
    if form.validate_on_submit():
        # 验证 adjustment_type 是否为 'raw_material'
        if form.adjustment_type.data != 'raw_material':
            flash('调整类型错误，请刷新页面。', 'danger')
            return redirect(url_for('raw_material.detail', id=raw_material.id))

        # 从表单获取数据
        adjustment_quantity = form.adjustment_quantity.data
        reason_text = form.reason.data
        reason_detail = form.reason_detail.data

        old_quantity = raw_material.stock_quantity
        
        # 更新原材料库存
        raw_material.stock_quantity += adjustment_quantity
        
        # 创建库存调整记录
        adjustment = StockAdjustment(
            adjustment_date=datetime.now(),
            adjustment_type='raw_material',
            raw_material_id=raw_material.id,
            quantity_before=old_quantity,
            quantity_after=raw_material.stock_quantity,
            adjustment_quantity=adjustment_quantity,
            reason=reason_text + (f": {reason_detail}" if reason_detail else ""),
            created_by=current_user.username if current_user.is_authenticated else 'System' # 记录操作者
        )
        
        db.session.add(adjustment)
        db.session.commit()
        
        flash(f'库存调整成功：{raw_material.name} 当前库存 {raw_material.stock_quantity} {raw_material.unit}', 'success')
        return redirect(url_for('raw_material.detail', id=raw_material.id))
    
    # GET 请求或表单验证失败时渲染模板
    return render_template(
        'raw_material/adjust.html',
        form=form,
        raw_material=raw_material, # 传递原材料对象给模板
        title=f'调整原材料库存：{raw_material.name}'
    )