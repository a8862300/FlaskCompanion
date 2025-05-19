from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required

from app import db
from models import Supplier
from forms import SupplierForm

supplier_bp = Blueprint('supplier', __name__, url_prefix='/suppliers')

@supplier_bp.route('/')
@login_required
def list():
    """供应商列表"""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # 搜索功能
    search = request.args.get('search', '')
    if search:
        suppliers = Supplier.query.filter(
            Supplier.name.like(f'%{search}%') | 
            Supplier.contact.like(f'%{search}%') | 
            Supplier.phone.like(f'%{search}%')
        ).paginate(page=page, per_page=per_page)
    else:
        suppliers = Supplier.query.paginate(page=page, per_page=per_page)
    
    return render_template('supplier/list.html', suppliers=suppliers, search=search)

@supplier_bp.route('/<int:id>')
@login_required
def detail(id):
    """供应商详情"""
    supplier = Supplier.query.get_or_404(id)
    return render_template('supplier/detail.html', supplier=supplier)

@supplier_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """添加供应商"""
    form = SupplierForm()
    
    if form.validate_on_submit():
        supplier = Supplier(
            name=form.name.data,
            contact=form.contact.data,
            phone=form.phone.data,
            address=form.address.data
        )
        db.session.add(supplier)
        db.session.commit()
        
        flash('供应商添加成功', 'success')
        return redirect(url_for('supplier.list'))
    
    return render_template('supplier/form.html', form=form, title='添加供应商')

@supplier_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    """编辑供应商"""
    supplier = Supplier.query.get_or_404(id)
    form = SupplierForm(obj=supplier)
    
    if form.validate_on_submit():
        supplier.name = form.name.data
        supplier.contact = form.contact.data
        supplier.phone = form.phone.data
        supplier.address = form.address.data
        
        db.session.commit()
        flash('供应商更新成功', 'success')
        return redirect(url_for('supplier.list'))
    
    return render_template('supplier/form.html', form=form, supplier=supplier, title='编辑供应商')

@supplier_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    """删除供应商"""
    supplier = Supplier.query.get_or_404(id)
    
    # 检查供应商是否有关联产品或采购记录
    if supplier.products or supplier.raw_material_purchases:
        flash('无法删除：该供应商已有关联产品或采购记录', 'danger')
        return redirect(url_for('supplier.list'))
    
    db.session.delete(supplier)
    db.session.commit()
    flash('供应商删除成功', 'success')
    
    return redirect(url_for('supplier.list'))
