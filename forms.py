from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, FloatField, IntegerField, SelectField, DateField, HiddenField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Email, Length, Optional, NumberRange
from datetime import datetime

class LoginForm(FlaskForm):
    """登录表单"""
    username = StringField('用户名', validators=[DataRequired(message='用户名不能为空')])
    password = PasswordField('密码', validators=[DataRequired(message='密码不能为空')])
    submit = SubmitField('登录')

class UserForm(FlaskForm):
    """用户表单"""
    username = StringField('用户名', validators=[DataRequired(message='用户名不能为空'), Length(min=2, max=20)])
    password = PasswordField('密码', validators=[Length(min=6, max=20, message='密码长度必须在6到20个字符之间')])
    role = SelectField('角色', choices=[('user', '普通用户'), ('admin', '管理员')])
    submit = SubmitField('保存')

class CustomerForm(FlaskForm):
    """客户表单"""
    name = StringField('客户名称', validators=[DataRequired(message='客户名称不能为空')])
    contact = StringField('联系人')
    phone = StringField('电话')
    address = StringField('地址')
    submit = SubmitField('保存')

class SupplierForm(FlaskForm):
    """供应商表单"""
    name = StringField('供应商名称', validators=[DataRequired(message='供应商名称不能为空')])
    contact = StringField('联系人')
    phone = StringField('电话')
    address = StringField('地址')
    submit = SubmitField('保存')

class CategoryForm(FlaskForm):
    """商品分类表单"""
    name = StringField('分类名称', validators=[DataRequired(message='分类名称不能为空')])
    description = TextAreaField('描述')
    submit = SubmitField('保存')

class ProductForm(FlaskForm):
    """商品表单"""
    name = StringField('商品名称', validators=[DataRequired(message='商品名称不能为空')])
    sku = StringField('SKU', validators=[DataRequired(message='SKU不能为空')])
    description = TextAreaField('描述')
    selling_price = FloatField('销售价格', validators=[DataRequired(message='销售价格不能为空'), NumberRange(min=0, message='价格必须大于等于0')])
    cost_price = FloatField('成本价格', validators=[DataRequired(message='成本价格不能为空'), NumberRange(min=0, message='价格必须大于等于0')])
    stock_quantity = IntegerField('库存数量', validators=[NumberRange(min=0, message='库存不能为负数')])
    category_id = SelectField('所属分类', coerce=int, validators=[DataRequired(message='必须选择分类')])
    supplier_id = SelectField('默认供应商', coerce=int)
    submit = SubmitField('保存')

class RawMaterialForm(FlaskForm):
    """原材料表单"""
    name = StringField('原材料名称', validators=[DataRequired(message='原材料名称不能为空')])
    unit = StringField('单位', validators=[DataRequired(message='单位不能为空')])
    stock_quantity = FloatField('库存数量', validators=[NumberRange(min=0, message='库存不能为负数')])
    unit_cost = FloatField('单位成本', validators=[DataRequired(message='单位成本不能为空'), NumberRange(min=0, message='成本必须大于等于0')])
    safety_stock = FloatField('安全库存量', validators=[Optional(), NumberRange(min=0, message='安全库存不能为负数')])
    submit = SubmitField('保存')

class RawMaterialPurchaseForm(FlaskForm):
    """原材料采购表单"""
    purchase_date = DateField('采购日期', default=datetime.now)
    raw_material_id = SelectField('原材料', coerce=int, validators=[DataRequired(message='必须选择原材料')])
    supplier_id = SelectField('供应商', coerce=int, validators=[DataRequired(message='必须选择供应商')])
    quantity = FloatField('采购数量', validators=[DataRequired(message='采购数量不能为空'), NumberRange(min=0.1, message='采购数量必须大于0')])
    unit_price = FloatField('单位价格', validators=[DataRequired(message='单位价格不能为空'), NumberRange(min=0, message='价格必须大于等于0')])
    total_price = FloatField('采购总价', validators=[DataRequired(message='采购总价不能为空')])
    submit = SubmitField('保存')

class OrderForm(FlaskForm):
    """订单表单"""
    order_date = DateField('订单日期', default=datetime.now)
    customer_id = SelectField('客户', coerce=int, validators=[DataRequired(message='必须选择客户')])
    status = SelectField('订单状态', choices=[
        ('待支付', '待支付'),
        ('已支付', '已支付'),
        ('已发货', '已发货'),
        ('已完成', '已完成'),
        ('已取消', '已取消')
    ])
    payment_method = SelectField('支付方式', choices=[
        ('支付宝', '支付宝'),
        ('微信支付', '微信支付'),
        ('货到付款', '货到付款'),
        ('银行转账', '银行转账'),
        ('其他', '其他')
    ])
    notes = TextAreaField('备注')
    total_amount = FloatField('订单总金额', render_kw={'readonly': True})
    submit = SubmitField('保存订单')

class OrderItemForm(FlaskForm):
    """订单项表单 - 仅用于表单验证，不直接渲染"""
    product_id = IntegerField('商品ID', validators=[DataRequired()])
    quantity = IntegerField('数量', validators=[DataRequired(), NumberRange(min=1, message='数量必须大于0')])
    unit_price = FloatField('单价', validators=[DataRequired(), NumberRange(min=0, message='单价必须大于等于0')])
    subtotal = FloatField('小计')

class StockAdjustmentForm(FlaskForm):
    """库存调整表单"""
    # 保持为 SelectField，以便在路由中设置 choices
    adjustment_type = SelectField('调整类型', choices=[('product', '成品商品'), ('raw_material', '原材料')], validators=[DataRequired(message='调整类型不能为空')])
    # product_id 保持 SelectField，并设置为 DataRequired
    product_id = SelectField('商品', coerce=int, validators=[DataRequired(message='商品ID不能为空')])
    raw_material_id = SelectField('原材料', coerce=int, validators=[Optional()]) # 保持 SelectField，但允许可选
    
    adjustment_quantity = FloatField('调整数量', validators=[DataRequired(message='调整数量不能为空')])
    reason = SelectField('调整原因', choices=[
        ('盘点调整', '盘点调整'),
        ('退货入库', '退货入库'),
        ('质量问题出库', '质量问题出库'),
        ('生产领用', '生产领用'),
        ('损耗报废', '损耗报废'),
        ('其他原因', '其他原因')
    ], validators=[DataRequired(message='调整原因不能为空')])
    reason_detail = TextAreaField('详细说明', validators=[Optional()])
    submit = SubmitField('保存')

class ReportDateRangeForm(FlaskForm):
    """报表日期范围表单"""
    start_date = DateField('开始日期', default=lambda: datetime.now().replace(day=1))
    end_date = DateField('结束日期', default=datetime.now)
    submit = SubmitField('生成报表')
