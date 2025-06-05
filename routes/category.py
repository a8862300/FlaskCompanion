from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required

from models import db
from models import Category
from forms import CategoryForm

category_bp = Blueprint('category', __name__, url_prefix='/category')

@category_bp.route('/list')
@login_required
def list():
    """商品分类列表"""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # 搜索功能
    search = request.args.get('search', '')
    if search:
        categories = Category.query.filter(
            Category.name.like(f'%{search}%') | 
            Category.description.like(f'%{search}%')
        ).paginate(page=page, per_page=per_page)
    else:
        categories = Category.query.paginate(page=page, per_page=per_page)
    
    return render_template('category/list.html', categories=categories, search=search)

@category_bp.route('/<int:id>')
@login_required
def detail(id):
    """商品分类详情"""
    category = Category.query.get_or_404(id)
    return render_template('category/detail.html', category=category)

@category_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """添加商品分类"""
    form = CategoryForm()
    
    if form.validate_on_submit():
        category = Category(
            name=form.name.data,
            description=form.description.data
        )
        db.session.add(category)
        db.session.commit()
        
        flash('商品分类添加成功', 'success')
        return redirect(url_for('category.list'))
    
    return render_template('category/form.html', form=form, title='添加商品分类')

@category_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    """编辑商品分类"""
    category = Category.query.get_or_404(id)
    form = CategoryForm(obj=category)
    
    if form.validate_on_submit():
        category.name = form.name.data
        category.description = form.description.data
        
        db.session.commit()
        flash('商品分类更新成功', 'success')
        return redirect(url_for('category.list'))
    
    return render_template('category/form.html', form=form, category=category, title='编辑商品分类')

@category_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    """删除商品分类"""
    category = Category.query.get_or_404(id)
    
    # 检查分类是否有关联商品
    if category.products:
        flash('无法删除：该分类已有关联商品', 'danger')
        return redirect(url_for('category.list'))
    
    db.session.delete(category)
    db.session.commit()
    flash('商品分类删除成功', 'success')
    
    return redirect(url_for('category.list'))
