# FlaskCompanion 库存管理系统

## 项目简介
FlaskCompanion 是基于 Flask 框架开发的现代化库存管理系统，支持商品、客户、供应商、订单、采购、原材料、报表等全流程管理，适合中小企业或团队协作使用。

## 主要功能
- 用户认证与权限管理（支持管理员/普通用户）
- 仪表盘总览（库存、销售、采购等关键数据）
- 商品管理（增删改查、库存调整）
- 分类管理（商品分类维护）
- 客户管理（客户信息维护）
- 供应商管理（供应商信息维护）
- 订单管理（下单、出库、订单明细、出库单打印）
- 采购管理（采购单、入库、采购明细）
- 原材料管理（原材料库存、调整）
- 报表中心（销售报表、原材料成本报表等）
- RESTful API 支持（部分接口）
- 全局 CSRF 防护，安全性高
- 支持多用户协作与权限分级

## 技术栈
- Python 3.12+
- Flask 2.x
- Flask-WTF（表单与 CSRF 防护）
- SQLAlchemy（ORM）
- Jinja2（模板渲染）
- Poetry（依赖管理与虚拟环境）
- pre-commit（代码规范与安全自动化）
- bandit（安全扫描）
- pytest（自动化测试）

## 快速开始
1. 克隆仓库
   ```bash
   git clone https://github.com/a8862300/FlaskCompanion.git
   cd FlaskCompanion
   ```
2. 安装依赖（推荐使用 Poetry）
   ```bash
   poetry install
   ```
3. 激活虚拟环境
   ```bash
   poetry shell
   ```
4. 初始化数据库（自动创建默认管理员 admin/admin）
   ```bash
   flask init-db
   ```
5. 启动开发服务器
   ```bash
   flask run
   ```
6. 访问系统
   浏览器打开 http://127.0.0.1:5000

## 代码规范与安全
- 已集成 pre-commit 钩子，提交前自动执行 black、isort、flake8、bandit、mypy、pytest 等检查。
- 依赖管理采用 poetry，所有依赖锁定在 poetry.lock，保证团队环境一致。
- 可手动运行 bandit 进行安全扫描：
  ```bash
  bandit -r . -f txt -o bandit_report.txt
  ```
- 所有表单均已启用 CSRF 防护。

## 目录结构
- app.py           —— Flask 工厂模式主入口
- cli.py           —— 命令行工具（如初始化数据库）
- models.py        —— 数据模型定义
- routes/          —— 各业务模块蓝图（商品、订单等）
- templates/       —— 前端模板
- static/          —— 静态资源（CSS/JS）
- test_app.py      —— 自动化测试脚本
- pyproject.toml   —— 依赖与项目配置
- .pre-commit-config.yaml —— 代码规范与安全钩子配置

## 分支与协作
- 推荐每个功能/修复新建 feature/xxx 或 fix/xxx 分支，提交后推送到 GitHub 并发起 PR。
- 代码合并需经团队成员评审，确保主分支稳定。

## 其它说明
- 默认数据库为 SQLite（instance/inventory.db），可按需切换。
- 默认管理员账号：admin  密码：admin
- 如需扩展 API、权限、报表等功能，欢迎提交 PR 或 issue。

---

如有问题请联系项目维护者，或在 GitHub 提交 issue。
