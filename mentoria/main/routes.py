from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from mentoria import db
from mentoria.models import Registros, Turmas, Modulos, Conteudos, Avisos
from . import main # Importa o próprio blueprint
from datetime import datetime
from mentoria.email import send_email


import secrets
import re


# Rota alternativa para escolher qual mentoria/curso escolher
@main.route('/escolha')
def escolha():
    return render_template('escolha.html')

@main.route('/inscricao-dev', methods=['GET', 'POST'])
def inscricao_dev():
    if request.method == 'POST':
        try:
            email = request.form.get('email')
            if Registros.query.filter_by(email=email).first():
                return jsonify({'status': 'error', 'message': 'Este e-mail já foi utilizado. Por favor, tente outro.'})

            produto = Produtos.query.filter_by(nome="Mentoria DEV+").first()
            if not produto:
                return jsonify({'status': 'error', 'message': 'Erro de configuração: Produto "Mentoria DEV+" não encontrado.'})

            novo_registro = Registros(
                nome=request.form.get('nome'),
                email=email,
                whatsapp=request.form.get('whatsapp'),
                produto_interesse_id=produto.id,
                perfil_detalhado=request.form.get('perfil_detalhado'),
                desafio_detalhado=request.form.get('desafio_detalhado'),
                resumo_jornada=request.form.get('resumo_jornada'),
                status='Inscrito',
                token_matricula=secrets.token_hex(16)
            )
            db.session.add(novo_registro)
            db.session.commit()
            
            return jsonify({'status': 'success', 'message': 'Pré-inscrição na Mentoria DEV+ realizada com sucesso!'})

        except (IntegrityError, OperationalError) as e:
            db.session.rollback()
            # Este erro é capturado se a base de dados estiver dessincronizada
            current_app.logger.error(f"Erro de base de dados na inscrição DEV+: {e}")
            return jsonify({'status': 'error', 'message': 'Ocorreu um erro ao processar a sua inscrição. Verifique se a base de dados está atualizada.'}), 500
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro inesperado na inscrição DEV+: {e}")
            return jsonify({'status': 'error', 'message': 'Ocorreu um erro inesperado. Tente novamente mais tarde.'}), 500

    return render_template('form_dev_plus.html', titulo="Inscrição | Mentoria DEV+")


@main.route('/inscricao-ia-edu', methods=['GET', 'POST'])
def inscricao_ia_edu():
    if request.method == 'POST':
        try:
            email = request.form.get('email')
            if Registros.query.filter_by(email=email).first():
                return jsonify({'status': 'error', 'message': 'Este e-mail já foi utilizado.'})

            produto = Produtos.query.filter_by(nome="Mentoria IA.edu").first()
            if not produto:
                return jsonify({'status': 'error', 'message': 'Erro de configuração: Produto "Mentoria IA.edu" não encontrado.'})

            novo_registro = Registros(
                nome=request.form.get('nome'),
                email=email,
                whatsapp=request.form.get('whatsapp'),
                produto_interesse_id=produto.id,
                perfil_detalhado=request.form.get('perfil_detalhado'),
                desafio_detalhado=request.form.get('desafio_detalhado'),
                escolaridade=request.form.get('escolaridade'),
                resumo_jornada=request.form.get('resumo_jornada'),
                status='Inscrito',
                token_matricula=secrets.token_hex(16)
            )
            db.session.add(novo_registro)
            db.session.commit()

            return jsonify({'status': 'success', 'message': 'Pré-inscrição na Formação IA para Educadores realizada com sucesso!'})

        except (IntegrityError, OperationalError) as e:
            db.session.rollback()
            current_app.logger.error(f"Erro de base de dados na inscrição IA.edu: {e}")
            return jsonify({'status': 'error', 'message': 'Ocorreu um erro ao processar a sua inscrição. Verifique se a base de dados está atualizada.'}), 500
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro inesperado na inscrição IA.edu: {e}")
            return jsonify({'status': 'error', 'message': 'Ocorreu um erro inesperado. Tente novamente mais tarde.'}), 500

    return render_template('form_ia_edu.html', titulo="Inscrição | IA.edu - IA para Educadores")



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

@main.route('/interesse/<publico_alvo>', methods=['GET', 'POST'])
def formulario_interesse(publico_alvo):
    """
    Exibe um formulário de interesse unificado baseado no público-alvo
    e envia uma notificação por e-mail para o admin.
    """
    # Busca no banco os produtos para este público (ex: 'Educadores')
    produtos = Produtos.query.filter_by(publico_alvo=publico_alvo).all()
    if not produtos:
        abort(404) # Se não houver produtos para este público, dá erro 404

    if request.method == 'POST':
        email = request.form.get('email')
        if Registros.query.filter_by(email=email).first():
            flash('Este e-mail já foi utilizado. Em breve entraremos em contacto.', 'info')
            return redirect(url_for('main.formulario_interesse', publico_alvo=publico_alvo))

        novo_registro = Registros(
            nome=request.form.get('nome'),
            email=email,
            whatsapp=request.form.get('whatsapp'),
            produto_interesse_id=request.form.get('produto_interesse_id'),
            # ... (salve outros campos do formulário aqui)
        )
        db.session.add(novo_registro)
        db.session.commit()

        # Envia o e-mail de notificação para o admin
        produto_escolhido = Produtos.query.get(novo_registro.produto_interesse_id)
        send_email(current_app.config['ADMIN_EMAIL'], 
                   f'Novo Lead: {novo_registro.nome} para {produto_escolhido.nome}',
                   'email/novo_lead_admin', 
                   lead=novo_registro,
                   produto=produto_escolhido)

        return render_template('agradecimento.html')

    return render_template('form_interesse.html', produtos=produtos, publico_alvo=publico_alvo)


## Auth e Member area

@main.route('/')
@login_required # Garante que só utilizadores logados acedam à raiz do site
def index():
    """
    Rota principal que atua como um portão de entrada, redirecionando
    o utilizador para o dashboard correto com base no seu perfil.
    """
    if current_user.is_admin:
        return redirect(url_for('admin.admin_dashboard'))
    else:
        return redirect(url_for('main.area_membros'))
    
@main.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        user = Registros.query.filter_by(email=request.form.get('email')).first()
        
        # Verifica se o utilizador existe E se a senha está correta
        if user and user.check_password(request.form.get('password')):
            
            # --- LÓGICA "LEMBRAR DE MIM" ADICIONADA AQUI ---
            # Verifica se a checkbox "remember" foi marcada no formulário
            remember_me = request.form.get('remember') == 'on'
            # Passa o resultado para a função login_user
            login_user(user, remember=remember_me)
            
            # Redireciona para a página que o utilizador tentava aceder ou para a home
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.index'))
        else:
            # --- MENSAGEM DE ERRO GARANTIDA ---
            # Se o login falhar, envia esta mensagem para ser exibida no template
            flash('Login inválido. Verifique o seu e-mail e senha.', 'danger')
    
    return render_template('login.html')

@main.route('/logout')
@login_required # Garante que apenas usuários logados possam acessar esta rota
def logout():
    logout_user() # Função do Flask-Login que limpa a sessão do usuário
    flash("Você saiu da sua conta com sucesso.", "info")
    return redirect(url_for('main.login')) # Redireciona para a página de login

@main.route("/reset_password_request", methods=['GET', 'POST'])
def reset_password_request():
    """Exibe o formulário para pedir a recuperação de senha."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    if request.method == 'POST':
        user = Registros.query.filter_by(email=request.form['email']).first()
        if user:
            # Se o utilizador existir, envia o e-mail com o link de reset
            token = user.get_reset_token()
            send_email(user.email, 
                       'Instruções para Recuperar a sua Senha',
                       'email/reset_password',
                       user=user, token=token)
        # Mostra a mesma mensagem quer o e-mail exista ou não, por segurança
        flash('Se existir uma conta com este e-mail, receberá as instruções para recuperar a sua senha.', 'info')
        return redirect(url_for('main.login'))
    return render_template('reset_password_request.html', title='Recuperar Senha')


@main.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_password(token):
    """Página para o utilizador inserir a nova senha, acedida via token."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    user = Registros.verify_reset_token(token)
    if not user:
        flash('O link de recuperação é inválido ou expirou.', 'warning')
        return redirect(url_for('main.reset_password_request'))
    
    if request.method == 'POST':
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        if password != confirm_password:
            flash('As senhas não coincidem.', 'danger')
            return redirect(url_for('main.reset_password', token=token))

        user.set_password(password)
        db.session.commit()
        flash('A sua senha foi atualizada com sucesso! Pode agora fazer o login.', 'success')
        return redirect(url_for('main.login'))
        
    return render_template('reset_password.html', title='Definir Nova Senha', token=token)


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
