import os
from dotenv import load_dotenv

# Esta linha carrega as variáveis do seu ficheiro .env para o ambiente
load_dotenv()

# O resto do ficheiro continua a ler do ambiente
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Lê a SECRET_KEY do ambiente, com um valor padrão por segurança
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'fallback-secret-key'

    a versão:

import os
from dotenv import load_dotenv

load_dotenv()
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'fallback-secret-key'

    # LÓGICA ATUALIZADA: Usa o DATABASE_URL se ele existir (na Render), senão, usa o ficheiro sqlite3 local.
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'aplicacao.db')

    # Versão anterior do BD local
    #SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
    #    'sqlite:///' + os.path.join(basedir, 'aplicacao.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- CONFIGURAÇÕES DE E-MAIL LIDAS DO AMBIENTE ---
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.googlemail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']

    # Lê as suas credenciais diretamente do ficheiro .env
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL')