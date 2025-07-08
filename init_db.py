import sqlite3
import csv
from datetime import datetime
# Importa as ferramentas da sua aplicação
from mentoria import create_app, db
from mentoria.models import Produtos

# O caminho da base de dados é agora gerido pela aplicação
app = create_app()
DATABASE_PATH = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')


def criar_tabelas():
    """Verifica e cria as tabelas da base de dados se não existirem."""
    with app.app_context():
        db.create_all()
    print("Tabelas verificadas/criadas com sucesso!")


def importar_csv_para_registros():
    """Lê o ficheiro dados.csv e insere na tabela de registos."""
    # ... (a sua função importar_csv_para_registros continua igual) ...


def popular_produtos():
    """Garante que os produtos padrão existam na base de dados."""
    with app.app_context():
        produtos_a_criar = [
            {"nome": "Mentoria DEV+", "publico_alvo": "DEV", "descricao": "Mentoria para carreira DEV", "valor": 997},
            {"nome": "Mentoria IA.edu", "publico_alvo": "Educadores", "descricao": "Mentoria de IA para educadores", "valor": 997},
            {"nome": "Formação IA para Educadores", "publico_alvo": "Educadores", "descricao": "Curso de IA para educadores", "valor": 497}
        ]
        
        for p_info in produtos_a_criar:
            if not Produtos.query.filter_by(nome=p_info["nome"]).first():
                novo_produto = Produtos(**p_info)
                db.session.add(novo_produto)
        
        db.session.commit()
        print("Produtos padrão verificados/criados com sucesso.")


if __name__ == '__main__':
    print("Iniciando a configuração da base de dados...")
    criar_tabelas()
    print("\nVerificando produtos padrão...")
    popular_produtos()
    print("\nTentando importar dados do CSV para a tabela 'registros'...")
    importar_csv_para_registros()
    print("\nConfiguração finalizada.")
