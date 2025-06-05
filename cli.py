import click
from flask.cli import with_appcontext
from app import db, create_app
from models import User
from werkzeug.security import generate_password_hash

@click.command('init-db')
@with_appcontext
def init_db_command():
    """初始化数据库并创建默认管理员账户"""
    db.create_all()
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            password_hash=generate_password_hash('admin'),
            role='admin'
        )
        db.session.add(admin)
        db.session.commit()
        click.echo('创建了默认管理员账户: admin/admin')
    else:
        click.echo('管理员账户已存在')

def register_cli(app):
    app.cli.add_command(init_db_command)

if __name__ == '__main__':
    app = create_app()
    register_cli(app)
    app.run()
