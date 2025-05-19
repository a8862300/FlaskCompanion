from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash

from app import db
from models import User
from forms import LoginForm, UserForm

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            flash('登录成功！', 'success')
            return redirect(next_page or url_for('dashboard.index'))
        flash('用户名或密码错误', 'danger')
    
    return render_template('login.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    """用户登出"""
    logout_user()
    flash('您已成功登出', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/users')
@login_required
def user_list():
    """用户列表"""
    # 检查是否为管理员
    if current_user.role != 'admin':
        flash('您没有权限访问此页面', 'danger')
        return redirect(url_for('dashboard.index'))
    
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # 搜索功能
    search = request.args.get('search', '')
    if search:
        users = User.query.filter(User.username.like(f'%{search}%')).paginate(page=page, per_page=per_page)
    else:
        users = User.query.paginate(page=page, per_page=per_page)
    
    return render_template('user/list.html', users=users, search=search)

@auth_bp.route('/users/add', methods=['GET', 'POST'])
@login_required
def add_user():
    """添加用户"""
    # 检查是否为管理员
    if current_user.role != 'admin':
        flash('您没有权限访问此页面', 'danger')
        return redirect(url_for('dashboard.index'))
    
    form = UserForm()
    if form.validate_on_submit():
        # 检查用户名是否已存在
        existing_user = User.query.filter_by(username=form.username.data).first()
        if existing_user:
            flash('用户名已存在', 'danger')
            return render_template('user/form.html', form=form, title='添加用户')
        
        # 创建新用户
        user = User(
            username=form.username.data,
            password_hash=generate_password_hash(form.password.data),
            role=form.role.data
        )
        db.session.add(user)
        db.session.commit()
        
        flash('用户添加成功', 'success')
        return redirect(url_for('auth.user_list'))
    
    return render_template('user/form.html', form=form, title='添加用户')

@auth_bp.route('/users/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_user(id):
    """编辑用户"""
    # 检查是否为管理员
    if current_user.role != 'admin':
        flash('您没有权限访问此页面', 'danger')
        return redirect(url_for('dashboard.index'))
    
    user = User.query.get_or_404(id)
    form = UserForm(obj=user)
    
    # 不更新密码的特殊处理
    if request.method == 'GET':
        form.password.data = ''  # 清空密码字段
    
    if form.validate_on_submit():
        # 更新用户信息
        user.username = form.username.data
        user.role = form.role.data
        
        # 只有当密码字段有值时才更新密码
        if form.password.data:
            user.password_hash = generate_password_hash(form.password.data)
        
        db.session.commit()
        flash('用户更新成功', 'success')
        return redirect(url_for('auth.user_list'))
    
    return render_template('user/form.html', form=form, user=user, title='编辑用户')

@auth_bp.route('/users/delete/<int:id>', methods=['POST'])
@login_required
def delete_user(id):
    """删除用户"""
    # 检查是否为管理员
    if current_user.role != 'admin':
        flash('您没有权限访问此页面', 'danger')
        return redirect(url_for('dashboard.index'))
    
    user = User.query.get_or_404(id)
    
    # 避免删除当前登录的用户或最后一个管理员
    if user.id == current_user.id:
        flash('不能删除当前登录的用户', 'danger')
    elif user.role == 'admin' and User.query.filter_by(role='admin').count() <= 1:
        flash('不能删除唯一的管理员用户', 'danger')
    else:
        db.session.delete(user)
        db.session.commit()
        flash('用户删除成功', 'success')
    
    return redirect(url_for('auth.user_list'))
