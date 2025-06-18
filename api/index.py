print("--- SERVIDOR RECARREGADO COM A VERSÃO MAIS RECENTE ---")
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from collections import Counter
from datetime import datetime
import secrets
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from config import DATABASE_PATH



# --- CONFIGURAÇÃO DA APLICAÇÃO E DO BANCO DE DADOS ---
app = Flask(__name__, template_folder='../templates', static_folder='../static')

# Chave secreta essencial para usar mensagens 'flash' e sessões.
app.config['SECRET_KEY'] = 'uma-chave-secreta-muito-segura'

# Configuração do caminho do banco de dados para garantir que ele seja criado na mesma pasta do projeto.
# basedir = os.path.abspath(os.path.dirname(__file__))
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + DATABASE_PATH
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- CONFIGURAÇÃO DO FLASK-LOGIN ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Redireciona usuários não logados para a rota /login
login_manager.login_message = "Por favor, faça o login para acessar esta página."
login_manager.login_message_category = "info"

# --- MODELS (REPRESENTAÇÃO DAS TABELAS DO BANCO DE DADOS) ---

# Tabela de Associação Muitos-para-Muitos: conecta Turmas e Monitores.
turma_monitores = db.Table('turma_monitores',
    db.Column('turma_id', db.Integer, db.ForeignKey('turmas.id'), primary_key=True),
    db.Column('monitor_id', db.Integer, db.ForeignKey('monitores.id'), primary_key=True)
)

turma_modulos = db.Table('turma_modulos',
    db.Column('turma_id', db.Integer, db.ForeignKey('turmas.id'), primary_key=True),
    db.Column('modulo_id', db.Integer, db.ForeignKey('modulos.id'), primary_key=True)
)

class Turmas(db.Model):
    # A linha __tablename__ é ESSENCIAL para conectar esta classe à sua tabela.
    __tablename__ = 'turmas'
    id = db.Column(db.Integer, primary_key=True)
    nome_turma = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text)
    data_inicio = db.Column(db.Date)
    data_fim = db.Column(db.Date)
    status = db.Column(db.String(50), default='Planejamento')

    # Relações que conectam este modelo a outros:
    mentorados = db.relationship('Registros', backref='turma', lazy='dynamic')
    encontros = db.relationship('Encontros', backref='turma', lazy=True, cascade="all, delete-orphan")
    monitores = db.relationship('Monitores', secondary=turma_monitores, lazy='subquery',
        back_populates='turmas')
    modulos = db.relationship('Modulos', secondary=turma_modulos, lazy='subquery',
        backref=db.backref('turmas', lazy=True))
    avisos = db.relationship('Avisos', backref='turma', lazy=True, cascade="all, delete-orphan")


class Monitores(db.Model):
    __tablename__ = 'monitores'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    whatsapp = db.Column(db.String(20))
    resumo = db.Column(db.Text)
    perfil = db.Column(db.String(100))

    turmas = db.relationship('Turmas', secondary=turma_monitores, lazy='subquery',
        back_populates='monitores')
    encontros_liderados = db.relationship('Encontros', backref='monitor', lazy=True)

class Registros(db.Model, UserMixin): # Adiciona UserMixin
    __tablename__ = 'registros'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(128)) # Campo para senha criptografada
    is_admin = db.Column(db.Boolean, default=False)
    fone = db.Column(db.String(20))
    perfil = db.Column(db.String(100))
    desafio = db.Column(db.String(100))
    disponibilidade = db.Column(db.String(100))
    mensagem = db.Column(db.Text)
    data_inscricao = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default='Inscrito')
    
    # NOVOS CAMPOS
    token_matricula = db.Column(db.String(32), unique=True, nullable=True)
    plano_escolhido = db.Column(db.String(50), nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    turma_id = db.Column(db.Integer, db.ForeignKey('turmas.id'))

class Encontros(db.Model):
    __tablename__ = 'encontros'
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(150), nullable=False)
    descricao = db.Column(db.Text)
    data_encontro = db.Column(db.DateTime)
    link_meet = db.Column(db.String(200))
    status = db.Column(db.String(50), default='Agendado')
    
    turma_id = db.Column(db.Integer, db.ForeignKey('turmas.id'), nullable=False)
    monitor_id = db.Column(db.Integer, db.ForeignKey('monitores.id'), nullable=False)

class Modulos(db.Model):
    __tablename__ = 'modulos'
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(150), nullable=False)
    descricao = db.Column(db.Text)
    ordem = db.Column(db.Integer, default=0)
    thumbnail_url = db.Column(db.String(255))
    conteudos = db.relationship('Conteudos', backref='modulo', lazy=True, cascade="all, delete-orphan")

# NOVO MODEL: Conteudos
class Conteudos(db.Model):
    __tablename__ = 'conteudos'
    id = db.Column(db.Integer, primary_key=True)
    modulo_id = db.Column(db.Integer, db.ForeignKey('modulos.id'), nullable=False)
    titulo = db.Column(db.String(150), nullable=False)
    tipo = db.Column(db.String(50)) # 'Vídeo', 'PDF', 'Link'
    url_conteudo = db.Column(db.String(255), nullable=False)
    descricao = db.Column(db.Text)
    ordem = db.Column(db.Integer, default=0)

class Avisos(db.Model):
    __tablename__ = 'avisos'
    id = db.Column(db.Integer, primary_key=True)
    turma_id = db.Column(db.Integer, db.ForeignKey('turmas.id'), nullable=False)
    titulo = db.Column(db.String(150), nullable=False)
    conteudo = db.Column(db.Text, nullable=False)
    data_publicacao = db.Column(db.DateTime, default=datetime.utcnow)


# --- ROTAS DA APLICAÇÃO ---

@login_manager.user_loader
def load_user(user_id):
    return Registros.query.get(int(user_id))

# --- ROTAS PÚBLICAS PARA INSCRIÇÃO E MATRÍCULA ---

@app.route('/pre-inscricao', methods=['GET', 'POST'])
def pre_inscricao():
    """Página pública para o formulário de pré-inscrição."""
    if request.method == 'POST':
        # Verifica se o e-mail já está cadastrado
        email_existente = Registros.query.filter_by(email=request.form['email']).first()
        if email_existente:
            flash('Este e-mail já foi utilizado em uma inscrição. Por favor, utilize outro.', 'warning')
            return redirect(url_for('pre_inscricao'))

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
        return redirect(url_for('pre_inscricao'))
        
        #flash('Sua pré-inscrição foi realizada com sucesso! Em breve, você receberá mais informações por e-mail.', 'success')
        #return redirect(url_for('pre_inscricao')) # ou para uma página de "obrigado"

    return render_template('form_pre_inscricao.html', titulo="Pré-inscrição para Mentoria")


@app.route('/matricula/<token>', methods=['GET', 'POST'])
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

@app.route('/')
@login_required # Garante que só usuários logados acessem a raiz do site
def index():
    """
    Rota principal que atua como um portão de entrada, redirecionando
    o usuário para o dashboard correto com base em seu perfil.
    """
    if current_user.is_admin:
        return redirect(url_for('admin_dashboard'))
    else:
        return redirect(url_for('area_membros'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('area_membros'))
    if request.method == 'POST':
        user = Registros.query.filter_by(email=request.form['email']).first()
        if user and user.check_password(request.form['password']):
            login_user(user, remember=request.form.get('remember'))
            return redirect(url_for('area_membros'))
        else:
            flash('Login inválido. Verifique seu e-mail e senha.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required # Garante que apenas usuários logados possam acessar esta rota
def logout():
    logout_user() # Função do Flask-Login que limpa a sessão do usuário
    flash("Você saiu da sua conta com sucesso.", "info")
    return redirect(url_for('login')) # Redireciona para a página de login

@app.route('/area-membros')
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


# --- ROTAS DO PAINEL DE ADMINISTRAÇÃO ---

# Função decoradora para proteger rotas de admin
from functools import wraps

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("Acesso não autorizado. Esta área é restrita para administradores.", "danger")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin/inscricoes')
@admin_required # Protegida para administradores
def lista_inscricoes():
    """
    Página principal que lista os inscritos com filtros.
    """
    query = Registros.query
    
    filtro_perfil = request.args.get('perfil', '')
    filtro_desafio = request.args.get('desafio', '')
    filtro_disponibilidade = request.args.get('disponibilidade', '')

    if filtro_perfil:
        query = query.filter(Registros.perfil == filtro_perfil)
    if filtro_desafio:
        query = query.filter(Registros.desafio == filtro_desafio)
    if filtro_disponibilidade:
        query = query.filter(Registros.disponibilidade.like(f'%{filtro_disponibilidade}%'))

    dados_filtrados = query.order_by(Registros.data_inscricao.desc()).all()
    
    perfis_opcoes = sorted([p[0] for p in db.session.query(Registros.perfil).distinct().all() if p[0]])
    desafios_opcoes = sorted([d[0] for d in db.session.query(Registros.desafio).distinct().all() if d[0]])
    disponibilidades_opcoes = ['Manhã', 'Tarde', 'Noite', 'Fim de semana']
    
    filtros_ativos = {
        'perfil': filtro_perfil,
        'desafio': filtro_desafio,
        'disponibilidade': filtro_disponibilidade
    }

    return render_template('admin/lista_inscricoes.html', dados=dados_filtrados, total=len(dados_filtrados),
                           perfis=perfis_opcoes, desafios=desafios_opcoes,
                           disponibilidades=disponibilidades_opcoes, filtros_ativos=filtros_ativos)

@app.route('/admin/inscricao/<int:id>/detalhes')
@admin_required
def admin_detalhe_inscricao(id):
    """Exibe os detalhes completos de um único inscrito."""
    registro = Registros.query.get_or_404(id)
    return render_template('admin/detalhe.html', registro=registro)

@app.route('/admin/registro/<int:id>/definir-senha', methods=['GET', 'POST'])
@admin_required
def definir_senha_mentorado(id):
    """Página de administração para definir a senha de um mentorado."""
    mentorado = Registros.query.get_or_404(id)
    if request.method == 'POST':
        senha = request.form.get('senha')
        confirmacao_senha = request.form.get('confirmacao_senha')

        if not senha or not confirmacao_senha or senha != confirmacao_senha:
            flash('As senhas não conferem ou estão em branco. Tente novamente.', 'danger')
            return redirect(url_for('definir_senha_mentorado', id=id))

        mentorado.set_password(senha)
        db.session.commit()
        
        flash(f'Senha para {mentorado.nome} definida com sucesso!', 'success')
        return redirect(url_for('admin_detalhe_inscricao', id=id))

    return render_template('admin/form_definir_senha.html', mentorado=mentorado)


@app.route('/admin/detalhe/<int:id>')
@admin_required
def detalhe(id):
    registro = Registros.query.get_or_404(id)
    return render_template('detalhe.html', registro=registro)

@app.route('/admin/resumo')
@admin_required
def resumo():
    dados = Registros.query.all()
    total_registros = len(dados) if dados else 1
    
    total_disponibilidade = Counter()
    for item in dados:
        if item.disponibilidade:
            opcoes = [opt.strip() for opt in item.disponibilidade.split(',')]
            total_disponibilidade.update(opcoes)

    total_desafio = Counter(item.desafio for item in dados if item.desafio)
    total_perfil = Counter(item.perfil for item in dados if item.perfil)

    resumo_desafio = {k: {'total': v, 'pct': (v / total_registros) * 100} for k, v in total_desafio.items()}
    resumo_disponibilidade = {k: {'total': v, 'pct': (v / total_registros) * 100} for k, v in total_disponibilidade.items()}
    resumo_perfil = {k: {'total': v, 'pct': (v / total_registros) * 100} for k, v in total_perfil.items()}
    
    return render_template('resumo.html', 
                           resumo_desafio=resumo_desafio,
                           resumo_disponibilidade=resumo_disponibilidade,
                           resumo_perfil=resumo_perfil)
# --- ROTAS PARA GERENCIAR MONITORES ---

@app.route('/admin/monitores')
@admin_required
def admin_lista_monitores():
    """Lista todos os monitores para gestão do administrador."""
    monitores = Monitores.query.order_by(Monitores.nome).all()
    return render_template('admin/lista_monitores.html', monitores=monitores)

@app.route('/admin/monitores/novo', methods=['GET', 'POST'])
@admin_required
def admin_novo_monitor():
    """Exibe e processa o formulário para criar um novo monitor."""
    if request.method == 'POST':
        novo = Monitores(
            nome=request.form['nome'],
            email=request.form['email'],
            whatsapp=request.form['whatsapp'],
            resumo=request.form['resumo'],
            perfil=request.form['perfil']
        )
        db.session.add(novo)
        db.session.commit()
        flash('Monitor registado com sucesso!', 'success')
        return redirect(url_for('admin_lista_monitores'))
    return render_template('admin/form_monitor.html', titulo='Novo Monitor')

@app.route('/admin/monitores/editar/<int:id>', methods=['GET', 'POST'])
@admin_required
def admin_editar_monitor(id):
    """Exibe e processa o formulário para editar um monitor existente."""
    monitor = Monitores.query.get_or_404(id)
    if request.method == 'POST':
        monitor.nome = request.form['nome']
        monitor.email = request.form['email']
        monitor.whatsapp = request.form['whatsapp']
        monitor.resumo = request.form['resumo']
        monitor.perfil = request.form['perfil']
        db.session.commit()
        flash('Monitor atualizado com sucesso!', 'success')
        return redirect(url_for('admin_lista_monitores'))
    return render_template('admin/form_monitor.html', titulo='Editar Monitor', monitor=monitor)


@app.route('/admin/monitores/deletar/<int:id>', methods=['POST'])
@admin_required
def admin_deletar_monitor(id):
    """Deleta um monitor do sistema."""
    monitor = Monitores.query.get_or_404(id)
    db.session.delete(monitor)
    db.session.commit()
    flash('Monitor removido com sucesso!', 'danger')
    return redirect(url_for('admin_lista_monitores'))


@app.route('/admin')
@admin_required
def admin_dashboard():
    """Página principal do painel de administração."""
    return render_template('admin/admin_dashboard.html')


@app.route('/admin/modulos')
@admin_required
def admin_lista_modulos():
    """Lista todos os módulos para gestão do administrador."""
    modulos = Modulos.query.order_by(Modulos.ordem).all()
    return render_template('admin/lista_modulos.html', modulos=modulos)


@app.route('/admin/modulos/novo', methods=['GET', 'POST'])
@admin_required
def admin_novo_modulo():
    """Exibe e processa o formulário para criar um novo módulo."""
    if request.method == 'POST':
        novo = Modulos(
            titulo=request.form['titulo'],
            descricao=request.form['descricao'],
            ordem=int(request.form.get('ordem', 0)),
            thumbnail_url=request.form.get('thumbnail_url')
        )
        db.session.add(novo)
        db.session.commit()
        flash('Módulo criado com sucesso!', 'success')
        return redirect(url_for('admin_lista_modulos'))
    return render_template('admin/form_modulo.html', titulo="Criar Novo Módulo")



@app.route('/admin/modulos/editar/<int:id>', methods=['GET', 'POST'])
@admin_required
def admin_editar_modulo(id):
    """Exibe e processa o formulário para editar um módulo existente."""
    modulo = Modulos.query.get_or_404(id)
    if request.method == 'POST':
        modulo.titulo = request.form['titulo']
        modulo.descricao = request.form['descricao']
        modulo.ordem = int(request.form.get('ordem', 0))
        modulo.thumbnail_url = request.form.get('thumbnail_url')
        db.session.commit()
        flash('Módulo atualizado com sucesso!', 'success')
        return redirect(url_for('admin_lista_modulos'))
    return render_template('admin/form_modulo.html', titulo="Editar Módulo", modulo=modulo)



@app.route('/admin/modulos/deletar/<int:id>', methods=['POST'])
@admin_required
def admin_deletar_modulo(id):
    """Deleta um módulo e todos os seus conteúdos associados (devido ao cascade)."""
    modulo = Modulos.query.get_or_404(id)
    db.session.delete(modulo)
    db.session.commit()
    flash('Módulo removido com sucesso!', 'danger')
    return redirect(url_for('admin_lista_modulos'))

@app.route('/admin/modulos/<int:id>/detalhes')
@admin_required
def admin_detalhes_modulo(id):
    """Página para ver e gerir os conteúdos de um módulo específico."""
    modulo = Modulos.query.get_or_404(id)
    conteudos = sorted(modulo.conteudos, key=lambda c: c.ordem)
    return render_template('admin/detalhes_modulo.html', modulo=modulo, conteudos=conteudos)


@app.route('/admin/turma/<int:turma_id>/avisos/novo', methods=['POST'])
@admin_required
def novo_aviso(turma_id):
    """Processa o formulário para adicionar um novo aviso a uma turma."""
    titulo = request.form.get('titulo')
    conteudo = request.form.get('conteudo')
    if titulo and conteudo:
        novo = Avisos(turma_id=turma_id, titulo=titulo, conteudo=conteudo)
        db.session.add(novo)
        db.session.commit()
        flash('Aviso publicado com sucesso!', 'success')
    else:
        flash('O título e o conteúdo do aviso não podem estar em branco.', 'danger')
    return redirect(url_for('admin_detalhes_turma', id=turma_id))


@app.route('/admin/avisos/deletar/<int:id>', methods=['POST'])
@admin_required
def deletar_aviso(id):
    """Deleta um aviso."""
    aviso = Avisos.query.get_or_404(id)
    turma_id = aviso.turma_id
    db.session.delete(aviso)
    db.session.commit()
    flash('Aviso removido com sucesso!', 'info')
    return redirect(url_for('admin_detalhes_turma', id=turma_id))



@app.route('/admin/modulos/<int:modulo_id>/conteudo/novo', methods=['POST'])
@admin_required
def admin_novo_conteudo(modulo_id):
    """Processa o formulário para adicionar um novo conteúdo a um módulo."""
    novo = Conteudos(
        modulo_id=modulo_id, titulo=request.form.get('titulo'), tipo=request.form.get('tipo'),
        url_conteudo=request.form.get('url_conteudo'), descricao=request.form.get('descricao'),
        ordem=int(request.form.get('ordem', 0))
    )
    db.session.add(novo)
    db.session.commit()
    flash('Conteúdo adicionado com sucesso!', 'success')
    return redirect(url_for('admin_detalhes_modulo', id=modulo_id))

@app.route('/admin/conteudo/editar/<int:id>', methods=['GET', 'POST'])
@admin_required
def admin_editar_conteudo(id):
    """Formulário para editar um conteúdo existente."""
    conteudo = Conteudos.query.get_or_404(id)
    if request.method == 'POST':
        conteudo.titulo = request.form['titulo']
        conteudo.tipo = request.form['tipo']
        conteudo.url_conteudo = request.form['url_conteudo']
        conteudo.descricao = request.form['descricao']
        conteudo.ordem = int(request.form['ordem'])
        db.session.commit()
        flash('Conteúdo atualizado com sucesso!', 'success')
        return redirect(url_for('admin_detalhes_modulo', id=conteudo.modulo_id))
    return render_template('admin/form_conteudo.html', titulo="Editar Conteúdo", conteudo=conteudo)

@app.route('/admin/conteudo/deletar/<int:id>', methods=['POST'])
@admin_required
def admin_deletar_conteudo(id):
    """Deleta um conteúdo."""
    conteudo = Conteudos.query.get_or_404(id)
    modulo_id = conteudo.modulo_id
    db.session.delete(conteudo)
    db.session.commit()
    flash('Conteúdo removido com sucesso!', 'info')
    return redirect(url_for('admin_detalhes_modulo', id=modulo_id))

# --- ROTAS PARA GERENCIAR ENCONTROS DE UMA TURMA ---

@app.route('/admin/turma/<int:turma_id>/encontros/novo', methods=['GET', 'POST'])
@admin_required
def novo_encontro(turma_id):
    """Página para criar um novo encontro para uma turma específica."""
    turma = Turmas.query.get_or_404(turma_id)
    # Passa apenas os monitores associados a esta turma para o formulário
    monitores_da_turma = turma.monitores

    if request.method == 'POST':
        data_encontro_str = request.form['data_encontro']
        data_encontro = datetime.strptime(data_encontro_str, '%Y-%m-%dT%H:%M') if data_encontro_str else None

        novo = Encontros(
            titulo=request.form['titulo'],
            descricao=request.form['descricao'],
            data_encontro=data_encontro,
            link_meet=request.form['link_meet'],
            status=request.form['status'],
            turma_id=turma_id,
            monitor_id=request.form['monitor_id']
        )
        db.session.add(novo)
        db.session.commit()
        flash('Encontro agendado com sucesso!', 'success')
        return redirect(url_for('admin_detalhes_turma', id=turma_id))
    
    return render_template('admin/form_encontro.html', titulo='Agendar Novo Encontro', turma=turma, monitores_da_turma=monitores_da_turma)

@app.route('/admin/encontro/editar/<int:id>', methods=['GET', 'POST'])
@admin_required
def editar_encontro(id):
    """Página para editar um encontro existente."""
    encontro = Encontros.query.get_or_404(id)
    turma = encontro.turma
    monitores_da_turma = turma.monitores
    
    if request.method == 'POST':
        encontro.titulo = request.form['titulo']
        encontro.descricao = request.form['descricao']
        encontro.link_meet = request.form['link_meet']
        encontro.status = request.form['status']
        encontro.monitor_id = request.form['monitor_id']
        
        data_encontro_str = request.form['data_encontro']
        encontro.data_encontro = datetime.strptime(data_encontro_str, '%Y-%m-%dT%H:%M') if data_encontro_str else None
        
        db.session.commit()
        flash('Encontro atualizado com sucesso!', 'success')
        return redirect(url_for('admin_detalhes_turma', id=turma.id))

    return render_template('admin/form_encontro.html', titulo='Editar Encontro', encontro=encontro, turma=turma, monitores_da_turma=monitores_da_turma)

@app.route('/admin/encontro/deletar/<int:id>', methods=['POST'])
@admin_required
def deletar_encontro(id):
    """Rota para deletar um encontro."""
    encontro = Encontros.query.get_or_404(id)
    turma_id = encontro.turma_id
    db.session.delete(encontro)
    db.session.commit()
    flash('Encontro removido com sucesso!', 'danger')
    return redirect(url_for('admin_detalhes_turma', id=turma_id))

# --- ROTAS PARA GERENCIAR A ALOCAÇÃO DE MENTORADOS ---


# 2. ROTA PARA ALOCAR UM MENTORADO:
@app.route('/admin/registro/<int:registro_id>/alocar/<int:turma_id>', methods=['POST'])
@admin_required
def alocar_mentorado(registro_id, turma_id):
    """Define o turma_id de um registo para alocá-lo a uma turma."""
    registro = Registros.query.get_or_404(registro_id)
    registro.turma_id = turma_id
    db.session.commit()
    flash(f"'{registro.nome}' foi adicionado(a) à turma com sucesso!", 'success')
    return redirect(url_for('admin_detalhes_turma', id=turma_id))

# --- ROTA Desalocar mentorado de uma turma ---
@app.route('/admin/registro/<int:registro_id>/desalocar/<int:turma_id>', methods=['POST'])
@admin_required
def desalocar_mentorado(registro_id, turma_id):
    """Limpa o turma_id de um registo para removê-lo de uma turma."""
    registro = Registros.query.get_or_404(registro_id)
    if registro.turma_id == turma_id:
        registro.turma_id = None
        db.session.commit()
        flash(f"'{registro.nome}' foi removido(a) da turma.", 'info')
    return redirect(url_for('admin_detalhes_turma', id=turma_id))

# --- ROTAS PARA GERENCIAR TURMAS ---

@app.route('/admin/turmas')
@admin_required
def admin_lista_turmas():
    turmas = Turmas.query.order_by(Turmas.data_inicio.desc()).all()
    return render_template('admin/lista_turmas.html', turmas=turmas)

@app.route('/admin/turmas/nova', methods=['GET', 'POST'])
@admin_required
def admin_nova_turma():
    """Exibe e processa o formulário para criar uma nova turma."""
    monitores_disponiveis = Monitores.query.order_by(Monitores.nome).all()
    if request.method == 'POST':
        data_inicio = datetime.strptime(request.form['data_inicio'], '%Y-%m-%d').date() if request.form['data_inicio'] else None
        data_fim = datetime.strptime(request.form['data_fim'], '%Y-%m-%d').date() if request.form['data_fim'] else None

        nova = Turmas(nome_turma=request.form['nome_turma'], descricao=request.form['descricao'],
                      data_inicio=data_inicio, data_fim=data_fim, status=request.form['status'])
        
        for id_monitor in request.form.getlist('monitores'):
            monitor = Monitores.query.get(id_monitor)
            if monitor:
                nova.monitores.append(monitor)
        
        db.session.add(nova)
        db.session.commit()
        flash('Turma criada com sucesso!', 'success')
        return redirect(url_for('admin_lista_turmas'))
    
    return render_template('admin/form_turma.html', titulo='Nova Turma', monitores_disponiveis=monitores_disponiveis)


@app.route('/admin/turmas/editar/<int:id>', methods=['GET', 'POST'])
@admin_required
def admin_editar_turma(id):
    """Exibe e processa o formulário para editar uma turma existente."""
    turma = Turmas.query.get_or_404(id)
    monitores_disponiveis = Monitores.query.order_by(Monitores.nome).all()
    if request.method == 'POST':
        turma.nome_turma = request.form['nome_turma']
        turma.descricao = request.form['descricao']
        turma.status = request.form['status']
        turma.data_inicio = datetime.strptime(request.form['data_inicio'], '%Y-%m-%d').date() if request.form['data_inicio'] else None
        turma.data_fim = datetime.strptime(request.form['data_fim'], '%Y-%m-%d').date() if request.form['data_fim'] else None

        turma.monitores.clear()
        for id_monitor in request.form.getlist('monitores'):
            monitor = Monitores.query.get(id_monitor)
            if monitor:
                turma.monitores.append(monitor)
        
        db.session.commit()
        flash('Turma atualizada com sucesso!', 'success')
        return redirect(url_for('admin_lista_turmas'))
        
    return render_template('admin/form_turma.html', titulo='Editar Turma', turma=turma, monitores_disponiveis=monitores_disponiveis)

@app.route('/admin/turma/<int:id>/detalhes')
@admin_required
def admin_detalhes_turma(id):
    """Página de administração para ver detalhes de uma turma e gerir os seus membros, avisos e módulos."""
    turma = Turmas.query.get_or_404(id)
    mentorados_disponiveis = Registros.query.filter(Registros.turma_id.is_(None)).order_by(Registros.nome).all()
    modulos_disponiveis = Modulos.query.order_by(Modulos.ordem).all()
    encontros = sorted(turma.encontros, key=lambda x: x.data_encontro if x.data_encontro else datetime.min, reverse=True)
    
    return render_template('admin/detalhes_turma.html', 
                           turma=turma, encontros=encontros, 
                           mentorados_disponiveis=mentorados_disponiveis,
                           modulos_disponiveis=modulos_disponiveis)

@app.route('/admin/turma/<int:turma_id>/vincular-modulos', methods=['POST'])
@admin_required
def vincular_modulos_turma(turma_id):
    """Processa o formulário da página de detalhes da turma, sincronizando os módulos selecionados com a turma."""
    turma = Turmas.query.get_or_404(turma_id)
    ids_dos_modulos_selecionados = request.form.getlist('modulos')
    turma.modulos.clear()
    for modulo_id in ids_dos_modulos_selecionados:
        modulo = Modulos.query.get(modulo_id)
        if modulo:
            turma.modulos.append(modulo)
    db.session.commit()
    flash('Módulos da turma atualizados com sucesso!', 'success')
    return redirect(url_for('admin_detalhes_turma', id=turma_id))

# DEBUG ROUTES
'''
@app.route('/admin/debug-routes')
def debug_routes():
    """
    Uma página de depuração que lista todas as rotas registadas na aplicação.
    Isto ajuda a confirmar se o Flask reconhece uma rota específica.
    """
    output = []
    for rule in app.url_map.iter_rules():
        # Obtém os métodos (GET, POST, etc.) para a rota
        methods = ','.join(rule.methods)
        # Formata a linha para exibição
        line = f"Endpoint: {rule.endpoint:<40} Métodos: {methods:<20} URL: {rule.rule}"
        output.append(line)
    
    # Imprime a lista no terminal para fácil visualização
    print("\n--- ROTAS REGISTADAS NA APLICAÇÃO ---")
    for line in sorted(output):
        print(line)
    print("-------------------------------------\n")
    
    # Também exibe a lista no navegador
    return "<pre>" + "\n".join(sorted(output)) + "</pre>"
'''

# --- INICIALIZAÇÃO DA APLICAÇÃO ---
if __name__ == '__main__':
    # O contexto da aplicação é necessário para que o SQLAlchemy saiba a qual app ele pertence.
    with app.app_context():
        # A linha abaixo pode ser usada para criar as tabelas se elas não existirem,
        # mas o ideal é usar o script 'init_db.py' para isso.
        # db.create_all()
        pass
    app.run(debug=True)
