import click
from flask.cli import with_appcontext
from . import db
from .models import Registros, Produtos
import csv
from datetime import datetime

# --- COMANDO PARA CRIAR UM ADMINISTRADOR ---

@click.command(name='create-admin')
@with_appcontext
@click.option('--nome', prompt=True, help='O nome completo do administrador.')
@click.option('--email', prompt=True, help='O email de login do administrador.')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='A senha do administrador.')
def create_admin_command(nome, email, password):
    """Cria um novo utilizador administrador."""
    if Registros.query.filter_by(email=email).first():
        click.echo(f"Erro: O e-mail '{email}' já existe.")
        return

    admin_user = Registros(
        nome=nome,
        email=email,
        is_admin=True,
        status='Matriculado'
    )
    admin_user.set_password(password)
    db.session.add(admin_user)
    db.session.commit()
    click.echo(f"Administrador '{nome}' criado com sucesso!")


# --- COMANDO PARA INICIALIZAR OS DADOS (PRODUTOS E CSV) ---

@click.command(name='init-data')
@with_appcontext
def init_data_command():
    """Cria os produtos padrão e importa os registos do CSV."""
    
    # 1. Popula a tabela de produtos
    produtos_a_criar = [
        {"nome": "Mentoria DEV+", "publico_alvo": "DEV", "descricao": "Mentoria para carreira DEV", "valor": 997.00},
        {"nome": "Mentoria IA.edu", "publico_alvo": "Educadores", "descricao": "Mentoria de IA para educadores", "valor": 997.00},
        {"nome": "Formação IA para Educadores", "publico_alvo": "Educadores", "descricao": "Curso de IA para educadores", "valor": 297.00}
    ]
    
    novos_produtos_criados = 0
    for p_info in produtos_a_criar:
        if not Produtos.query.filter_by(nome=p_info["nome"]).first():
            novo_produto = Produtos(**p_info)
            db.session.add(novo_produto)
            novos_produtos_criados += 1

    if novos_produtos_criados > 0:
        db.session.commit()
        click.echo(f"{novos_produtos_criados} novos produtos foram criados.")
    else:
        click.echo("Todos os produtos padrão já existem na base de dados.")

    # 2. Importa os registos do CSV
    try:
        # Tenta encontrar o ficheiro CSV na raiz do projeto
        with open('dados_mentoria_pre2.csv', mode='r', encoding='utf-8') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            registos_inseridos = 0
            for row in csv_reader:
                email_limpo = row.get('email', '').strip()
                if not email_limpo or Registros.query.filter_by(email=email_limpo).first():
                    continue

                data_obj = datetime.strptime(row['_date'], '%d/%m/%Y %H:%M:%S')
                novo_registro = Registros(
                    nome=row.get('nome'), email=email_limpo, whatsapp=row.get('fone'),
                    perfil=row.get('perfil'), desafio=row.get('desafio'),
                    disponibilidade=row.get('disponibilidade'), mensagem=row.get('mensagem'),
                    data_inscricao=data_obj
                )
                db.session.add(novo_registro)
                registos_inseridos += 1
            
            if registos_inseridos > 0:
                db.session.commit()
            click.echo(f"{registos_inseridos} novos registos foram inseridos do CSV.")
    except FileNotFoundError:
        click.echo("AVISO: Ficheiro CSV não encontrado. A importação foi ignorada.")
    except Exception as e:
        click.echo(f"Erro ao importar CSV: {e}")
        db.session.rollback()