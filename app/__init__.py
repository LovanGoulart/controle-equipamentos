from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Por favor, faça login para acessar esta página.'
    login_manager.login_message_category = 'warning'

    with app.app_context():
        from app.routes import auth, main, api, admin
        app.register_blueprint(auth.bp)
        app.register_blueprint(main.bp)
        app.register_blueprint(api.bp, url_prefix='/api')
        app.register_blueprint(admin.bp, url_prefix='/admin')

        db.create_all()
        criar_admin_padrao()
        criar_config_padrao()

    
    # Context processor: disponibiliza 'date' em todos os templates
    @app.context_processor
    def inject_date():
        from datetime import date
        return dict(date=date)

    return app

def criar_admin_padrao():
    from app.models.models import Usuario
    from werkzeug.security import generate_password_hash

    admin = Usuario.query.filter_by(username='admin').first()
    if not admin:
        admin = Usuario(
            nome='Administrador',
            username='admin',
            email='admin@patrimonio.local',
            password_hash=generate_password_hash('admin'),
            is_admin=True,
            ativo=True
        )
        db.session.add(admin)
        db.session.commit()

def criar_config_padrao():
    from app.models.models import Configuracao

    config = Configuracao.query.first()
    if not config:
        config = Configuracao(
            nome_empresa='Controle de Patrimônio',
            dias_lembrete_manutencao='30,15,7,1',
            tema='claro'
        )
        db.session.add(config)
        db.session.commit()
