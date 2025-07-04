from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from mentoria import db
from mentoria.models import Registros, Turmas, Modulos, Conteudos, Avisos
from . import main # Importa o próprio blueprint
from datetime import datetime


import secrets
import re


# Rota alternativa para escolher qual mentoria/curso escolher
@main.route('/escolha')
def escolha():
    return render_template('escolha.html')

@main.route('/inscricao-dev', methods=['GET', 'POST'])
def inscricao_dev():
    """Exibe e processa o formulário para a Mentoria DEV+."""
    if request.method == 'POST':
        email = request.form.get('email')
        # Validação para evitar e-mails duplicados
        if Registros.query.filter_by(email=email).first():
            flash('Este e-mail já foi utilizado. Por favor, tente outro.', 'warning')
            return redirect(url_for('main.inscricao_dev'))

        # Cria um novo registo com os campos detalhados
        novo_registro = Registros(
            nome=request.form.get('nome'),
            email=email,
            whatsapp=request.form.get('whatsapp'),
            programa_interesse="Mentoria DEV+",
            perfil_detalhado=request.form.get('perfil_detalhado'),
            desafio_detalhado=request.form.get('desafio_detalhado'),
            resumo_jornada=request.form.get('resumo_jornada'),
            status='Inscrito',
            token_matricula=secrets.token_hex(16)
        )
        db.session.add(novo_registro)
        db.session.commit()
        flash('Pré-inscrição na Mentoria DEV+ realizada com sucesso! Fique de olho no seu e-mail.', 'success')
        return redirect(url_for('main.escolha'))

    return render_template('form_dev_plus.html', titulo="Inscrição | Mentoria DEV+")


@main.route('/inscricao-ia-edu', methods=['GET', 'POST'])
def inscricao_ia_edu():
    """Exibe e processa o formulário para a Mentoria/Curso IA.edu."""
    if request.method == 'POST':
        email = request.form.get('email')
        # Validação para evitar e-mails duplicados
        if Registros.query.filter_by(email=email).first():
            flash('Este e-mail já foi utilizado. Por favor, tente outro.', 'warning')
            return redirect(url_for('main.inscricao_ia_edu'))

        # Cria um novo registo com os campos detalhados
        novo_registro = Registros(
            nome=request.form.get('nome'),
            email=email,
            whatsapp=request.form.get('whatsapp'),
            programa_interesse="IA para Educadores",
            perfil_detalhado=request.form.get('perfil_detalhado'),
            desafio_detalhado=request.form.get('desafio_detalhado'),
            escolaridade=request.form.get('escolaridade'),
            resumo_jornada=request.form.get('resumo_jornada'),
            status='Inscrito',
            token_matricula=secrets.token_hex(16)
        )
        db.session.add(novo_registro)
        db.session.commit()
        flash('Pré-inscrição na Formação IA para Educadores realizada com sucesso! Fique de olho no seu e-mail.', 'success')
        return redirect(url_for('main.escolha'))

    return render_template('form_ia_edu.html', titulo="Inscrição | IA para Educadores")


@main.route('/pre-inscricao', methods=['GET', 'POST'])
def pre_inscricao():
    """Página pública para o formulário de pré-inscrição."""
    if request.method == 'POST':
        # Verifica se o e-mail já está cadastrado
        email_existente = Registros.query.filter_by(email=request.form['email']).first()
        if email_existente:
            flash('Este e-mail já foi utilizado em uma inscrição. Por favor, utilize outro.', 'warning')
            return redirect(url_for('main.pre_inscricao'))

        disponibilidades_lista = request.form.getlist('disponibilidade')
        disponibilidades_str = ", ".join(disponibilidades_lista)


        novo_registro = Registros(
            nome=request.form['nome'],
            email=request.form['email'],
            fone=request.form['fone'],
            desafio=request.form['desafio'],
            disponibilidade=disponibilidades_str, # 3. Usa a string convertida aqui
            mensagem=request.form['mensagem'],
            status='Inscrito',
            token_matricula=secrets.token_hex(16) # Gera um token seguro e único
        )
        db.session.add(novo_registro)
        db.session.commit()
        
        # Aqui você pode adicionar lógica para enviar um e-mail de confirmação de inscrição

         # LINHA TEMPORÁRIA PARA TESTE:
        flash(f"LINK DE TESTE PARA MATRÍCULA: /matricula/{novo_registro.token_matricula}", 'info')

        flash('Sua pré-inscrição foi realizada com sucesso!', 'success')
        return redirect(url_for('main.pre_inscricao'))
        
        #flash('Sua pré-inscrição foi realizada com sucesso! Em breve, você receberá mais informações por e-mail.', 'success')
        #return redirect(url_for('pre_inscricao')) # ou para uma página de "obrigado"

    return render_template('form_pre_inscricao.html', titulo="Pré-inscrição para Mentoria")


@main.route('/matricula/<token>', methods=['GET', 'POST'])
def confirmar_matricula(token):
    """Página onde o aluno confirma os dados e escolhe o plano."""
    # Busca o registro pelo token único
    registro = Registros.query.filter_by(token_matricula=token).first_or_404()

    # LINKS DE PAGAMENTO (Exemplo - você deve substituir pelos seus links reais)
    links_pagamento = {
        'plano_basico': 'https://link-do-seu-mercado-pago-plano-1.com',
        'plano_pro': 'https://link-do-seu-mercado-pago-plano-2.com',
        'plano_premium': 'https://link-do-seu-mercado-pago-plano-3.com'
    }

    if request.method == 'POST':
        # Atualiza os dados do registro com as informações do formulário completo
        registro.nome = request.form['nome']
        registro.fone = request.form['fone']
        # Adicione aqui a atualização de outros campos do formulário completo
        
        plano = request.form.get('plano_escolhido')
        if not plano:
            flash('Por favor, selecione um plano para continuar.', 'warning')
            return render_template('form_matricula.html', titulo="Confirmar Matrícula", registro=registro)

        registro.plano_escolhido = plano
        registro.status = 'Aguardando Pagamento'
        db.session.commit()

        # Redireciona para o link de pagamento correspondente
        link_pagamento = links_pagamento.get(plano)
        if link_pagamento:
            return redirect(link_pagamento)
        else:
            flash('Ocorreu um erro ao processar o plano selecionado.', 'danger')

    return render_template('form_matricula.html', titulo="Confirmar Matrícula", registro=registro)

## Auth e Member area

@main.route('/')
@login_required # Garante que só usuários logados acessem a raiz do site
def index():
    """
    Rota principal que atua como um portão de entrada, redirecionando
    o usuário para o dashboard correto com base em seu perfil.
    """
    if current_user.is_admin:
        return redirect(url_for('admin.admin_dashboard'))
    else:
        return redirect(url_for('main.area_membros'))

@main.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.area_membros'))
    if request.method == 'POST':
        user = Registros.query.filter_by(email=request.form['email']).first()
        if user and user.check_password(request.form['password']):
            login_user(user, remember=request.form.get('remember'))
            return redirect(url_for('main.area_membros'))
        else:
            flash('Login inválido. Verifique seu e-mail e senha.', 'danger')
    return render_template('login.html')

@main.route('/logout')
@login_required # Garante que apenas usuários logados possam acessar esta rota
def logout():
    logout_user() # Função do Flask-Login que limpa a sessão do usuário
    flash("Você saiu da sua conta com sucesso.", "info")
    return redirect(url_for('main.login')) # Redireciona para a página de login

@main.route('/area-membros')
@login_required # Esta linha protege a rota!
def area_membros():
    """
    Dashboard principal do mentorado. Exibe o progresso, avisos
    e os módulos de conteúdo aos quais ele tem acesso.
    """
    # Pega a turma do utilizador logado (current_user é disponibilizado pelo Flask-Login)
    turma_do_aluno = current_user.turma
    modulos_da_turma = []
    progresso_percent = 0
    avisos_da_turma = []

    if turma_do_aluno:
        # Pega os módulos associados à turma, ordenados pela coluna 'ordem'
        modulos_da_turma = sorted(turma_do_aluno.modulos, key=lambda m: m.ordem)
        
        # Pega os avisos associados à turma, ordenados pela data de publicação
        avisos_da_turma = sorted(turma_do_aluno.avisos, key=lambda a: a.data_publicacao, reverse=True)

        # Lógica para calcular o progresso da mentoria com base nas datas
        hoje = datetime.utcnow().date()
        inicio = turma_do_aluno.data_inicio
        fim = turma_do_aluno.data_fim

        if inicio and fim and hoje >= inicio:
            if hoje >= fim:
                progresso_percent = 100
            else:
                duracao_total = (fim - inicio).days
                dias_passados = (hoje - inicio).days
                if duracao_total > 0:
                    progresso_percent = round((dias_passados / duracao_total) * 100)
    
    return render_template('area_membros.html', 
                           modulos=modulos_da_turma, 
                           progresso=progresso_percent,
                           avisos=avisos_da_turma)
