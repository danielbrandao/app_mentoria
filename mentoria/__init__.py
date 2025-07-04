import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from config import Config

# Inicializa as extensões
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'main.login'
login_manager.login_message = "Por favor, faça o login para aceder a esta página."
login_manager.login_message_category = 'info'


def create_app(config_class=Config):
    """
    Cria e configura a instância da aplicação Flask.
    """
    app = Flask(__name__)
 
    # Carrega as configurações do ficheiro config.py
    app.config.from_object(config_class)

    # Associa as extensões à nossa aplicação
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # Regista os Blueprints
    from mentoria.main.routes import main as main_blueprint
    app.register_blueprint(main_blueprint)
    
    from mentoria.admin.routes import admin as admin_blueprint
    app.register_blueprint(admin_blueprint, url_prefix='/admin')

    # Retorna a aplicação pronta a ser executada
    return app
