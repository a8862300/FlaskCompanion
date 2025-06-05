from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required

from models import db
from models import Customer
from forms import CustomerForm

customer_bp = Blueprint('customer', __name__, url_prefix='/customer')

@customer_bp.route('/list')
@login_required
def list():
    """客户列表"""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # 搜索功能
    search = request.args.get('search', '')
    if search:
        customers = Customer.query.filter(
            Customer.name.like(f'%{search}%') | 
            Customer.contact.like(f'%{search}%') | 
            Customer.phone.like(f'%{search}%')
        ).paginate(page=page, per_page=per_page)
    else:
        customers = Customer.query.paginate(page=page, per_page=per_page)
    
    return render_template('customer/list.html', customers=customers, search=search)

@customer_bp.route('/<int:id>')
@login_required
def detail(id):
    """客户详情"""
    customer = Customer.query.get_or_404(id)
    return render_template('customer/detail.html', customer=customer)

@customer_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """添加客户"""
    form = CustomerForm()
    
    if form.validate_on_submit():
        customer = Customer(
            name=form.name.data,
            contact=form.contact.data,
            phone=form.phone.data,
            address=form.address.data
        )
        db.session.add(customer)
        db.session.commit()
        
        flash('客户添加成功', 'success')
        return redirect(url_for('customer.list'))
    
    return render_template('customer/form.html', form=form, title='添加客户')

@customer_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    """编辑客户"""
    customer = Customer.query.get_or_404(id)
    form = CustomerForm(obj=customer)
    
    if form.validate_on_submit():
        customer.name = form.name.data
        customer.contact = form.contact.data
        customer.phone = form.phone.data
        customer.address = form.address.data
        
        db.session.commit()
        flash('客户更新成功', 'success')
        return redirect(url_for('customer.list'))
    
    return render_template('customer/form.html', form=form, customer=customer, title='编辑客户')

@customer_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    """删除客户"""
    customer = Customer.query.get_or_404(id)
    
    # 检查客户是否有关联订单
    if customer.orders:
        flash('无法删除：该客户已有关联订单', 'danger')
        return redirect(url_for('customer.list'))
    
    db.session.delete(customer)
    db.session.commit()
    flash('客户删除成功', 'success')
    
    return redirect(url_for('customer.list'))
