import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from config import Config
from flask_mail import Mail # Importe a nova extensão


# Inicializa as extensões
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'main.login'
login_manager.login_message = "Por favor, faça o login para aceder a esta página."
login_manager.login_message_category = 'info'
mail = Mail() # Inicialize a extensão mail



def create_app(config_class=Config):
    """
    Cria e configura a instância da aplicação Flask.
    """
    app = Flask(__name__)
 
    # Carrega as configurações do ficheiro config.py
    app.config.from_object(config_class)

    # Adiciona as configurações de upload diretamente na criação da app
    # para garantir que elas estejam sempre disponíveis.
    app.config['UPLOAD_FOLDER'] = os.path.join(
        os.path.abspath(os.path.join(os.path.dirname(__file__), '..')), 
        'mentoria', 'static', 'img', 'uploads'
    )
    app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

    # Associa as extensões à nossa aplicação
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    mail.init_app(app) # Associe o mail à sua aplicação

    from . import commands
    app.cli.add_command(commands.create_admin_command)
    app.cli.add_command(commands.init_data_command) # <-- ADICIONE ESTA LINHA



    # Regista os Blueprints
    from mentoria.main.routes import main as main_blueprint
    app.register_blueprint(main_blueprint)
    
    from mentoria.admin.routes import admin as admin_blueprint
    app.register_blueprint(admin_blueprint, url_prefix='/admin')

    # Retorna a aplicação pronta a ser executada
    return app
