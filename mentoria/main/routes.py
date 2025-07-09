from flask import render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from mentoria import db
from mentoria.models import Registros, Turmas, Modulos, Conteudos, Avisos, Produtos
from . import main
from mentoria.email import send_email
import secrets
import re
from datetime import datetime
from sqlalchemy.exc import IntegrityError, OperationalError


# --- ROTAS PÚBLICAS E DE AUTENTICAÇÃO ---

@main.route('/')
@login_required
def index():
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
        if user and user.check_password(request.form.get('password')):
            remember_me = request.form.get('remember') == 'on'
            login_user(user, remember=remember_me)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.index'))
        else:
            flash('Login inválido. Verifique o seu e-mail e senha.', 'danger')
    return render_template('login.html')

@main.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Você saiu da sua conta com sucesso.", "info")
    return redirect(url_for('main.login'))

@main.route('/escolha')
def escolha():
    return render_template('escolha.html')

@main.route('/agradecimento-dev')
def agradecimento1():
    return render_template('agradecimento.html')

@main.route('/agradecimento-edu')
def agradecimento2():
    return render_template('agradecimento2.html')


@main.route('/inscricao-dev', methods=['GET', 'POST'])
def inscricao_dev():
    if request.method == 'POST':
        try:
            email = request.form.get('email')
            if Registros.query.filter_by(email=email).first():
                return jsonify({'status': 'error', 'message': 'Este e-mail já foi utilizado. Por favor, tente outro.'})
            produto = Produtos.query.filter_by(nome="Mentoria DEV+").first()
            if not produto: return jsonify({'status': 'error', 'message': 'Erro de configuração do produto.'}), 500
            novo_registro = Registros(
                nome=request.form.get('nome'), email=email, whatsapp=request.form.get('whatsapp'),
                produto_interesse_id=produto.id, perfil_detalhado=request.form.get('perfil_detalhado'),
                desafio_detalhado=request.form.get('desafio_detalhado'), resumo_jornada=request.form.get('resumo_jornada'),
                status='Inscrito', token_matricula=secrets.token_hex(16)
            )
            db.session.add(novo_registro)
            db.session.commit()
            return jsonify({'status': 'success', 'message': 'Pré-inscrição na Mentoria DEV+ realizada com sucesso! <br> Entraremos em contato em breve.'})
        except Exception as e:
            db.session.rollback(); current_app.logger.error(f"Erro na inscrição DEV+: {e}")
            return jsonify({'status': 'error', 'message': 'Ocorreu um erro inesperado ao processar a sua inscrição.'}), 500
    return render_template('form_dev_plus.html', titulo="Inscrição | Mentoria DEV+")

@main.route('/interesse/educadores', methods=['GET', 'POST'])
def formulario_interesse_educadores():
    produtos = Produtos.query.filter_by(publico_alvo='Educadores').order_by(Produtos.valor.desc()).all()
    if not produtos: abort(404)
    if request.method == 'POST':
        try:
            email = request.form.get('email')
            if Registros.query.filter_by(email=email).first():
                return jsonify({'status': 'error', 'message': 'Este e-mail já foi utilizado.'})
            produto_id = request.form.get('produto_interesse_id')
            if not produto_id: return jsonify({'status': 'error', 'message': 'Por favor, selecione uma opção de interesse.'})
            novo_registro = Registros(
                nome=request.form.get('nome'), email=email, whatsapp=request.form.get('whatsapp'),
                produto_interesse_id=produto_id, perfil_detalhado=request.form.get('perfil_detalhado'),
                desafio_detalhado=request.form.get('desafio_detalhado'), escolaridade=request.form.get('escolaridade'),
                resumo_jornada=request.form.get('resumo_jornada'), status='Interessado',
                token_matricula=secrets.token_hex(16)
            )
            db.session.add(novo_registro)
            db.session.commit()
            produto_escolhido = Produtos.query.get(novo_registro.produto_interesse_id)
            send_email(current_app.config['ADMIN_EMAIL'], f'Novo Lead (Educador): {novo_registro.nome}',
                       'email/novo_lead_admin', lead=novo_registro, produto=produto_escolhido)
            return jsonify({'status': 'success', 'message': 'Recebemos o seu interesse com sucesso! Entraremos em contato em breve.'})
        except Exception as e:
            db.session.rollback(); current_app.logger.error(f"Erro no formulário de interesse: {e}")
            return jsonify({'status': 'error', 'message': 'Ocorreu um erro inesperado.'}), 500
    return render_template('form_ia_edu.html', titulo="Interesse | IA para Educadores", produtos=produtos)



@main.route('/inscricao-ia-edu', methods=['GET', 'POST'])
def inscricao_ia_edu():
    if request.method == 'POST':
        try:
            email = request.form.get('email')
            if Registros.query.filter_by(email=email).first():
                return jsonify({'status': 'error', 'message': 'Este e-mail já foi utilizado.'})

            produto = Produtos.query.filter_by(nome="Mentoria IA.edu").first()
            if not produto:
                return jsonify({'status': 'error', 'message': 'Erro de configuração do produto.'})

            novo_registro = Registros(
                nome=request.form.get('nome'), email=email, whatsapp=request.form.get('whatsapp'),
                produto_interesse_id=produto.id, perfil_detalhado=request.form.get('perfil_detalhado'),
                desafio_detalhado=request.form.get('desafio_detalhado'), escolaridade=request.form.get('escolaridade'),
                resumo_jornada=request.form.get('resumo_jornada'), status='Inscrito',
                token_matricula=secrets.token_hex(16)
            )
            db.session.add(novo_registro)
            db.session.commit()

            return jsonify({'status': 'success', 'message': 'Pré-inscrição na Formação IA para Educadores realizada com sucesso! Entraremos em contacto em breve.'})
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro na inscrição IA.edu: {e}")
            return jsonify({'status': 'error', 'message': 'Ocorreu um erro inesperado ao processar a sua inscrição.'}), 500
            
    return render_template('form_ia_edu.html', titulo="Inscrição | IA para Educadores")


# --- ROTAS DE RECUPERAÇÃO DE SENHA ---

@main.route("/reset_password_request", methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    if request.method == 'POST':
        user = Registros.query.filter_by(email=request.form['email']).first()
        if user:
            token = user.get_reset_token()
            send_email(user.email, 
                       'Instruções para Recuperar a sua Senha',
                       'email/reset_password',
                       user=user, token=token)
        flash('Se existir uma conta com este e-mail, receberá as instruções para recuperar a sua senha.', 'info')
        return redirect(url_for('main.login'))
    return render_template('reset_password_request.html', title='Recuperar Senha')

@main.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_password(token):
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


# --- ROTAS DA ÁREA DE MEMBROS ---

@main.route('/area-membros')
@login_required
def area_membros():
    turma_do_aluno = current_user.turma
    modulos_da_turma = []
    progresso_percent = 0
    avisos_da_turma = []

    if turma_do_aluno:
        modulos_da_turma = sorted(turma_do_aluno.modulos, key=lambda m: m.ordem)
        avisos_da_turma = sorted(turma_do_aluno.avisos, key=lambda a: a.data_publicacao, reverse=True)
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

@main.route('/conteudo/<int:id>')
@login_required
def ver_conteudo(id):
    conteudo = Conteudos.query.get_or_404(id)
    turma_do_aluno = current_user.turma
    if not turma_do_aluno or conteudo.modulo not in turma_do_aluno.modulos:
        flash("Não tem permissão para aceder a este conteúdo.", "danger")
        return redirect(url_for('main.area_membros'))

    embed_url = None
    if 'vimeo.com' in conteudo.url_conteudo:
        match = re.search(r'vimeo.com/(\d+)', conteudo.url_conteudo)
        if match:
            video_id = match.group(1)
            embed_url = f"https://player.vimeo.com/video/{video_id}?title=0&byline=0&portrait=0"
    elif 'drive.google.com' in conteudo.url_conteudo:
        match = re.search(r'/d/([a-zA-Z0-9_-]+)', conteudo.url_conteudo)
        if match:
            file_id = match.group(1)
            embed_url = f"https://drive.google.com/file/d/{file_id}/preview"
    else:
        embed_url = conteudo.url_conteudo

    return render_template('conteudo.html', conteudo=conteudo, embed_url=embed_url)
