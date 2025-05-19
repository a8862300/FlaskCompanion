from flask import Blueprint, render_template, request, Response, flash
from flask_login import login_required
from datetime import datetime
import csv
import io
from sqlalchemy import func, extract

from app import db
from models import Order, OrderItem, Product, Category, RawMaterialPurchase
from forms import ReportDateRangeForm

report_bp = Blueprint('report', __name__, url_prefix='/reports')

@report_bp.route('/sales')
@login_required
def sales():
    """销售统计报表"""
    form = ReportDateRangeForm()
    
    # 获取日期范围
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # 默认为本月
    if not start_date:
        start_date = datetime.now().replace(day=1).strftime('%Y-%m-%d')
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
    
    # 转换为日期对象
    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
    
    form.start_date.data = start_date_obj
    form.end_date.data = end_date_obj
    
    # 按分类的销售额统计
    category_sales = db.session.query(
        Category.name.label('category'),
        func.sum(OrderItem.subtotal).label('total_sales')
    ).join(
        Product, 
        Product.id == OrderItem.product_id
    ).join(
        Category, 
        Category.id == Product.category_id
    ).join(
        Order, 
        Order.id == OrderItem.order_id
    ).filter(
        Order.order_date.between(start_date_obj, end_date_obj),
        Order.status != '已取消'
    ).group_by(
        Category.name
    ).order_by(
        func.sum(OrderItem.subtotal).desc()
    ).all()
    
    # 月度销售额统计
    monthly_sales = db.session.query(
        extract('year', Order.order_date).label('year'),
        extract('month', Order.order_date).label('month'),
        func.sum(Order.total_amount).label('total_sales')
    ).filter(
        Order.status != '已取消'
    ).group_by(
        extract('year', Order.order_date),
        extract('month', Order.order_date)
    ).order_by(
        extract('year', Order.order_date),
        extract('month', Order.order_date)
    ).all()
    
    # 畅销商品排名
    top_products = db.session.query(
        Product.name.label('product'),
        Category.name.label('category'),
        func.sum(OrderItem.quantity).label('total_quantity'),
        func.sum(OrderItem.subtotal).label('total_sales')
    ).join(
        OrderItem, 
        OrderItem.product_id == Product.id
    ).join(
        Category, 
        Category.id == Product.category_id
    ).join(
        Order, 
        Order.id == OrderItem.order_id
    ).filter(
        Order.order_date.between(start_date_obj, end_date_obj),
        Order.status != '已取消'
    ).group_by(
        Product.name,
        Category.name
    ).order_by(
        func.sum(OrderItem.quantity).desc()
    ).limit(10).all()
    
    # 客户购买力排名
    top_customers = db.session.query(
        Customer.name.label('customer'),
        func.count(Order.id).label('order_count'),
        func.sum(Order.total_amount).label('total_amount')
    ).join(
        Order, 
        Order.customer_id == Customer.id
    ).filter(
        Order.order_date.between(start_date_obj, end_date_obj),
        Order.status != '已取消'
    ).group_by(
        Customer.name
    ).order_by(
        func.sum(Order.total_amount).desc()
    ).limit(10).all()
    
    # 导出数据
    export_format = request.args.get('export')
    if export_format == 'csv':
        return export_sales_to_csv(category_sales, top_products, top_customers, start_date, end_date)
    
    return render_template(
        'report/sales.html',
        form=form,
        category_sales=category_sales,
        monthly_sales=monthly_sales,
        top_products=top_products,
        top_customers=top_customers,
        start_date=start_date,
        end_date=end_date
    )

@report_bp.route('/material-cost')
@login_required
def material_cost():
    """月度原材料支出报告"""
    form = ReportDateRangeForm()
    
    # 获取日期范围
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # 默认为本月
    if not start_date:
        start_date = datetime.now().replace(day=1).strftime('%Y-%m-%d')
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
    
    # 转换为日期对象
    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
    
    form.start_date.data = start_date_obj
    form.end_date.data = end_date_obj
    
    # 月度原材料支出统计
    monthly_costs = db.session.query(
        extract('year', RawMaterialPurchase.purchase_date).label('year'),
        extract('month', RawMaterialPurchase.purchase_date).label('month'),
        func.sum(RawMaterialPurchase.total_price).label('total_cost')
    ).filter(
        RawMaterialPurchase.purchase_date.between(start_date_obj, end_date_obj)
    ).group_by(
        extract('year', RawMaterialPurchase.purchase_date),
        extract('month', RawMaterialPurchase.purchase_date)
    ).order_by(
        extract('year', RawMaterialPurchase.purchase_date),
        extract('month', RawMaterialPurchase.purchase_date)
    ).all()
    
    # 原材料采购排名
    top_materials = db.session.query(
        RawMaterial.name.label('material'),
        RawMaterial.unit.label('unit'),
        func.sum(RawMaterialPurchase.quantity).label('total_quantity'),
        func.sum(RawMaterialPurchase.total_price).label('total_cost')
    ).join(
        RawMaterialPurchase, 
        RawMaterialPurchase.raw_material_id == RawMaterial.id
    ).filter(
        RawMaterialPurchase.purchase_date.between(start_date_obj, end_date_obj)
    ).group_by(
        RawMaterial.name,
        RawMaterial.unit
    ).order_by(
        func.sum(RawMaterialPurchase.total_price).desc()
    ).all()
    
    # 供应商采购统计
    supplier_costs = db.session.query(
        Supplier.name.label('supplier'),
        func.sum(RawMaterialPurchase.total_price).label('total_cost'),
        func.count(RawMaterialPurchase.id).label('purchase_count')
    ).join(
        RawMaterialPurchase, 
        RawMaterialPurchase.supplier_id == Supplier.id
    ).filter(
        RawMaterialPurchase.purchase_date.between(start_date_obj, end_date_obj)
    ).group_by(
        Supplier.name
    ).order_by(
        func.sum(RawMaterialPurchase.total_price).desc()
    ).all()
    
    # 导出数据
    export_format = request.args.get('export')
    if export_format == 'csv':
        return export_material_cost_to_csv(monthly_costs, top_materials, supplier_costs, start_date, end_date)
    
    return render_template(
        'report/material_cost.html',
        form=form,
        monthly_costs=monthly_costs,
        top_materials=top_materials,
        supplier_costs=supplier_costs,
        start_date=start_date,
        end_date=end_date
    )

def export_sales_to_csv(category_sales, top_products, top_customers, start_date, end_date):
    """导出销售报表为CSV"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # 写入标题
    writer.writerow(['销售报表', f'日期范围: {start_date} - {end_date}'])
    writer.writerow([])
    
    # 写入分类销售数据
    writer.writerow(['按分类的销售额'])
    writer.writerow(['分类', '销售额'])
    for item in category_sales:
        writer.writerow([item.category, item.total_sales])
    writer.writerow([])
    
    # 写入畅销商品数据
    writer.writerow(['畅销商品排名'])
    writer.writerow(['商品', '分类', '销售数量', '销售额'])
    for item in top_products:
        writer.writerow([item.product, item.category, item.total_quantity, item.total_sales])
    writer.writerow([])
    
    # 写入客户购买力数据
    writer.writerow(['客户购买力排名'])
    writer.writerow(['客户', '订单数', '购买总额'])
    for item in top_customers:
        writer.writerow([item.customer, item.order_count, item.total_amount])
    
    # 创建响应
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=sales_report_{start_date}_to_{end_date}.csv"}
    )

def export_material_cost_to_csv(monthly_costs, top_materials, supplier_costs, start_date, end_date):
    """导出原材料支出报表为CSV"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # 写入标题
    writer.writerow(['原材料支出报表', f'日期范围: {start_date} - {end_date}'])
    writer.writerow([])
    
    # 写入月度支出数据
    writer.writerow(['月度原材料支出'])
    writer.writerow(['年', '月', '总支出'])
    for item in monthly_costs:
        writer.writerow([int(item.year), int(item.month), item.total_cost])
    writer.writerow([])
    
    # 写入原材料采购排名数据
    writer.writerow(['原材料采购排名'])
    writer.writerow(['原材料', '单位', '采购数量', '采购总额'])
    for item in top_materials:
        writer.writerow([item.material, item.unit, item.total_quantity, item.total_cost])
    writer.writerow([])
    
    # 写入供应商采购统计数据
    writer.writerow(['供应商采购统计'])
    writer.writerow(['供应商', '采购次数', '采购总额'])
    for item in supplier_costs:
        writer.writerow([item.supplier, item.purchase_count, item.total_cost])
    
    # 创建响应
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=material_cost_report_{start_date}_to_{end_date}.csv"}
    )
