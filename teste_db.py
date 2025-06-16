from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os

# Configuração básica idêntica à do seu app.py
app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'aplicacao.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Definição do Model idêntica à do seu app.py
# Isso é crucial para que o SQLAlchemy saiba o que procurar.
class Registros(db.Model):
    __tablename__ = 'registros'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    fone = db.Column(db.String(20))
    perfil = db.Column(db.String(100))
    desafio = db.Column(db.String(100))
    disponibilidade = db.Column(db.String(100))
    mensagem = db.Column(db.Text)
    data_inscricao = db.Column(db.DateTime)
    status = db.Column(db.String(50), default='Inscrito')
    turma_id = db.Column(db.Integer, db.ForeignKey('turmas.id'))

# O teste real
def testar_leitura():
    print("--- Iniciando teste de leitura do banco de dados ---")
    try:
        with app.app_context():
            # Tenta buscar todos os registros da tabela
            todos_os_registros = Registros.query.all()

            if not todos_os_registros:
                print("RESULTADO: A consulta não retornou nenhum registro. A lista está vazia.")
            else:
                print(f"RESULTADO: SUCESSO! Foram encontrados {len(todos_os_registros)} registros no banco.")
                print("Amostra dos 5 primeiros registros encontrados:")
                for registro in todos_os_registros[:5]:
                    print(f"  - ID: {registro.id}, Nome: {registro.nome}, Email: {registro.email}")

    except Exception as e:
        print(f"Ocorreu um erro ao tentar ler o banco de dados: {e}")

    print("--- Teste de leitura finalizado ---")

if __name__ == '__main__':
    testar_leitura()