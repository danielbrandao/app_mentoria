import os

# Define o caminho raiz do projeto
basedir = os.path.abspath(os.path.dirname(__file__))

# Define o caminho completo para o arquivo do banco de dados
DATABASE_PATH = os.path.join(basedir, 'aplicacao.db')
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + DATABASE_PATH