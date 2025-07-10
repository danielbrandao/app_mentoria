import csv
from datetime import datetime
# Importa as ferramentas da sua aplicação para interagir com a base de dados
from mentoria import create_app, db
from mentoria.models import Produtos, Registros

# Cria uma instância da aplicação para obter o contexto e as configurações
app = create_app()


def popular_produtos():
    """
    Garante que os produtos padrão (mentorias e cursos) existam na base de dados.
    Esta função pode ser executada várias vezes sem criar duplicados.
    """
    # Usa o contexto da aplicação para interagir com a base de dados
    with app.app_context():
        # Lista dos produtos que a sua plataforma oferece
        produtos_a_criar = [
            {"nome": "Mentoria DEV+", "publico_alvo": "DEV", "descricao": "Mentoria para carreira DEV", "valor": 1997.00},
            {"nome": "Mentoria IA.edu", "publico_alvo": "Educadores", "descricao": "Mentoria de IA para educadores", "valor": 997.00},
            {"nome": "Formação IA para Educadores", "publico_alvo": "Educadores", "descricao": "Curso de IA para educadores", "valor": 497.00}
        ]
        
        novos_produtos_criados = 0
        for p_info in produtos_a_criar:
            # Verifica se um produto com este nome já existe usando uma query SQLAlchemy
            if not Produtos.query.filter_by(nome=p_info["nome"]).first():
                novo_produto = Produtos(**p_info)
                db.session.add(novo_produto)
                novos_produtos_criados += 1
        
        if novos_produtos_criados > 0:
            db.session.commit()
            print(f"{novos_produtos_criados} novos produtos foram criados.")
        else:
            print("Todos os produtos padrão já existem na base de dados.")


def importar_csv_para_registros():
    """Lê o ficheiro dados.csv e insere na tabela de registos usando SQLAlchemy."""
    with app.app_context():
        try:
            with open('dados_mentoria_pre2.csv', mode='r', encoding='utf-8') as csv_file:
                csv_reader = csv.DictReader(csv_file)
                registos_inseridos = 0
                for row in csv_reader:
                    email_limpo = row.get('email', '').strip()
                    if not email_limpo:
                        continue

                    # Verifica se o utilizador já existe para não criar duplicados
                    if not Registros.query.filter_by(email=email_limpo).first():
                        data_obj = datetime.strptime(row['_date'], '%d/%m/%Y %H:%M:%S')
                        
                        # Cria um objeto 'Registros' em vez de usar SQL puro
                        novo_registro = Registros(
                            nome=row.get('nome'),
                            email=email_limpo,
                            whatsapp=row.get('fone'), # Mapeia 'fone' para 'whatsapp'
                            # Os campos antigos ficam aqui para os dados do CSV
                            perfil=row.get('perfil'),
                            desafio=row.get('desafio'),
                            disponibilidade=row.get('disponibilidade'),
                            mensagem=row.get('mensagem'),
                            data_inscricao=data_obj
                        )
                        db.session.add(novo_registro)
                        registos_inseridos += 1
                
                if registos_inseridos > 0:
                    db.session.commit()
                    print(f"{registos_inseridos} novos registos foram inseridos do CSV.")
                else:
                    print("Nenhum registo novo do CSV para inserir.")

        except FileNotFoundError:
            print("AVISO: Ficheiro 'dados_mentoria_pre2.csv' não encontrado. A importação do CSV foi ignorada.")
        except Exception as e:
            print(f"Ocorreu um erro ao importar o CSV: {e}")
            db.session.rollback()


if __name__ == '__main__':
    print("Iniciando a configuração da base de dados...")
    print("\nVerificando produtos padrão...")
    popular_produtos()
    print("\nTentando importar dados do CSV para a tabela 'registros'...")
    importar_csv_para_registros()
    print("\nConfiguração finalizada.")