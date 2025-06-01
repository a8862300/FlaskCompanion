// 初始化
document.addEventListener('DOMContentLoaded', function() {
    // 初始设置
    updateOrderTotal();
    
    // 设置添加商品按钮事件
    document.getElementById('addItemBtn').addEventListener('click', addNewItem);
    
    // 获取URL参数
    const urlParams = new URLSearchParams(window.location.search);
    const customerId = urlParams.get('customer_id');
    
    // 如果URL中有客户ID，自动选中
    if (customerId) {
        const customerSelect = document.getElementById('customer_id');
        if (customerSelect) {
            customerSelect.value = customerId;
        }
    }
});

// 添加新的订单项
function addNewItem() {
    // 获取表格和消息元素
    const table = document.getElementById('orderItemsTable');
    const tbody = document.getElementById('orderItemsBody');
    const noItemsMessage = document.getElementById('noItemsMessage');
    
    // 显示表格，隐藏无项目消息
    table.style.display = 'table';
    noItemsMessage.style.display = 'none';
    
    // 创建新行
    const newRow = document.createElement('tr');
    newRow.className = 'item-row';
    
    // 获取所有商品选项
    const productSelectOptions = getAllProductOptions();
    
    // 设置行内容
    newRow.innerHTML = `
        <td>
            <select name="product_id[]" class="product-select" required onchange="updateProductPrice(this)">
                <option value="">-- 选择商品 --</option>
                ${productSelectOptions}
            </select>
            <input type="hidden" name="item_id[]" value="">
        </td>
        <td>
            <input type="number" name="quantity[]" class="quantity-input" value="1" min="1" required onchange="updateSubtotal(this.parentNode.parentNode)">
        </td>
        <td>
            <input type="number" name="unit_price[]" class="price-input" value="0.00" min="0" step="0.01" required onchange="updateSubtotal(this.parentNode.parentNode)">
        </td>
        <td class="item-subtotal">0.00</td>
        <td>
            <span class="remove-item" onclick="removeItem(this)">✕</span>
        </td>
    `;
    
    // 添加到表格
    tbody.appendChild(newRow);
    
    // 更新总金额
    updateOrderTotal();
}

// 获取所有商品选项
function getAllProductOptions() {
    // 从表格中获取商品选项
    const productSelects = document.querySelectorAll('.product-select');
    if (productSelects.length > 0) {
        return productSelects[0].innerHTML;
    } else {
        // 如果还没有商品选择器，获取预加载的产品数据
        let options = '<option value="">-- 选择商品 --</option>';
        
        // 从全局变量或API获取产品数据
        if (typeof productData !== 'undefined' && productData.length > 0) {
            productData.forEach(product => {
                options += `<option value="${product.id}" data-price="${product.selling_price}" data-stock="${product.stock_quantity}">
                    ${product.name} (${product.sku}) - 库存: ${product.stock_quantity}
                </option>`;
            });
        }
        
        return options;
    }
}

// 更新商品价格
function updateProductPrice(select) {
    // 获取选择的选项
    const selectedOption = select.options[select.selectedIndex];
    // 获取所在行
    const row = select.closest('tr');
    
    if (selectedOption.value) {
        // 从选项的data属性获取价格
        const price = selectedOption.dataset.price || 0;
        // 设置价格输入框的值
        row.querySelector('.price-input').value = parseFloat(price).toFixed(2);
        // 更新小计
        updateSubtotal(row);
    } else {
        // 清空价格
        row.querySelector('.price-input').value = '0.00';
        // 更新小计
        updateSubtotal(row);
    }
}

// 更新行小计
function updateSubtotal(row) {
    // 获取数量和单价
    const quantity = parseFloat(row.querySelector('.quantity-input').value) || 0;
    const unitPrice = parseFloat(row.querySelector('.price-input').value) || 0;
    
    // 计算小计
    const subtotal = quantity * unitPrice;
    
    // 更新小计显示
    row.querySelector('.item-subtotal').textContent = subtotal.toFixed(2);
    
    // 更新总金额
    updateOrderTotal();
}

// 更新订单总金额
function updateOrderTotal() {
    // 获取所有小计
    const subtotals = document.querySelectorAll('.item-subtotal');
    let total = 0;
    
    // 累加所有小计
    subtotals.forEach(function(element) {
        total += parseFloat(element.textContent) || 0;
    });
    
    // 更新总金额显示
    document.getElementById('orderTotal').textContent = total.toFixed(2);
    // 更新隐藏表单字段
    document.getElementById('totalAmountInput').value = total.toFixed(2);
}

// 移除订单项
function removeItem(element) {
    // 获取所在行和表格体
    const row = element.closest('tr');
    const tbody = row.parentNode;
    
    // 移除行
    tbody.removeChild(row);
    
    // 检查是否还有行
    if (tbody.querySelectorAll('tr').length === 0) {
        // 如果没有行，隐藏表格，显示无项目消息
        document.getElementById('orderItemsTable').style.display = 'none';
        document.getElementById('noItemsMessage').style.display = 'block';
    }
    
    // 更新总金额
    updateOrderTotal();
}
