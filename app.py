import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from collections import Counter
from datetime import datetime
import secrets
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash


# --- CONFIGURAÇÃO DA APLICAÇÃO E DO BANCO DE DADOS ---
app = Flask(__name__)
# Chave secreta essencial para usar mensagens 'flash' e sessões.
app.config['SECRET_KEY'] = 'uma-chave-secreta-muito-segura'

# Configuração do caminho do banco de dados para garantir que ele seja criado na mesma pasta do projeto.
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'aplicacao.db')
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


@app.route('/detalhe/<int:id>')
def detalhe(id):
    registro = Registros.query.get_or_404(id)
    return render_template('detalhe.html', registro=registro)

@app.route('/resumo')
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

@app.route('/monitores')
def lista_monitores():
    monitores = Monitores.query.order_by(Monitores.nome).all()
    return render_template('lista_monitores.html', monitores=monitores)

@app.route('/monitores/novo', methods=['GET', 'POST'])
def novo_monitor():
    if request.method == 'POST':
        novo = Monitores(nome=request.form['nome'], email=request.form['email'],
                         whatsapp=request.form['whatsapp'], resumo=request.form['resumo'],
                         perfil=request.form['perfil'])
        db.session.add(novo)
        db.session.commit()
        flash('Monitor cadastrado com sucesso!', 'success')
        return redirect(url_for('lista_monitores'))
    return render_template('form_monitor.html', titulo='Novo Monitor')

@app.route('/monitores/editar/<int:id>', methods=['GET', 'POST'])
def editar_monitor(id):
    monitor = Monitores.query.get_or_404(id)
    if request.method == 'POST':
        monitor.nome = request.form['nome']
        monitor.email = request.form['email']
        monitor.whatsapp = request.form['whatsapp']
        monitor.resumo = request.form['resumo']
        monitor.perfil = request.form['perfil']
        db.session.commit()
        flash('Monitor atualizado com sucesso!', 'success')
        return redirect(url_for('lista_monitores'))
    return render_template('form_monitor.html', titulo='Editar Monitor', monitor=monitor)

@app.route('/monitores/deletar/<int:id>', methods=['POST'])
def deletar_monitor(id):
    monitor = Monitores.query.get_or_404(id)
    db.session.delete(monitor)
    db.session.commit()
    flash('Monitor removido com sucesso!', 'danger')
    return redirect(url_for('lista_monitores'))


# --- ROTAS PARA GERENCIAR TURMAS ---

@app.route('/turmas')
def lista_turmas():
    turmas = Turmas.query.order_by(Turmas.data_inicio.desc()).all()
    return render_template('lista_turmas.html', turmas=turmas)

@app.route('/turmas/nova', methods=['GET', 'POST'])
def nova_turma():
    monitores_disponiveis = Monitores.query.all()
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
        return redirect(url_for('lista_turmas'))
    
    return render_template('form_turma.html', titulo='Nova Turma', monitores_disponiveis=monitores_disponiveis)

@app.route('/turmas/editar/<int:id>', methods=['GET', 'POST'])
def editar_turma(id):
    turma = Turmas.query.get_or_404(id)
    monitores_disponiveis = Monitores.query.all()
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
        return redirect(url_for('lista_turmas'))
        
    return render_template('form_turma.html', titulo='Editar Turma', turma=turma, monitores_disponiveis=monitores_disponiveis)

# --- ROTAS PARA GERENCIAR ENCONTROS DE UMA TURMA ---

@app.route('/turma/<int:id>/detalhes')
def detalhes_turma(id):
    """Mostra os detalhes de uma turma, incluindo encontros, mentorados, e mentorados disponíveis."""
    turma = Turmas.query.get_or_404(id)
    
    # Busca os mentorados que ainda não foram alocados em NENHUMA turma
    mentorados_disponiveis = Registros.query.filter(Registros.turma_id.is_(None)).order_by(Registros.nome).all()

    # Ordena os encontros da turma pela data
    encontros = sorted(turma.encontros, key=lambda x: x.data_encontro if x.data_encontro else datetime.min, reverse=True)
    
    return render_template('detalhes_turma.html', 
                           turma=turma, 
                           encontros=encontros, 
                           mentorados_disponiveis=mentorados_disponiveis)

@app.route('/turma/<int:turma_id>/encontros/novo', methods=['GET', 'POST'])
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
        return redirect(url_for('detalhes_turma', id=turma_id))
    
    return render_template('form_encontro.html', titulo='Agendar Novo Encontro', turma=turma, monitores_da_turma=monitores_da_turma)

@app.route('/encontro/editar/<int:id>', methods=['GET', 'POST'])
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
        return redirect(url_for('detalhes_turma', id=turma.id))

    return render_template('form_encontro.html', titulo='Editar Encontro', encontro=encontro, turma=turma, monitores_da_turma=monitores_da_turma)

@app.route('/encontro/deletar/<int:id>', methods=['POST'])
def deletar_encontro(id):
    """Rota para deletar um encontro."""
    encontro = Encontros.query.get_or_404(id)
    turma_id = encontro.turma_id
    db.session.delete(encontro)
    db.session.commit()
    flash('Encontro removido com sucesso!', 'danger')
    return redirect(url_for('detalhes_turma', id=turma_id))

# --- ROTAS PARA GERENCIAR A ALOCAÇÃO DE MENTORADOS ---

# 1. ATUALIZADA ROTA 'detalhes_turma' EXISTENTE COM ESTA VERSÃO:

# 2. ADICIONE ESTA NOVA ROTA PARA ALOCAR UM MENTORADO:
@app.route('/registro/<int:registro_id>/alocar/<int:turma_id>', methods=['POST'])
def alocar_mentorado(registro_id, turma_id):
    """Define o turma_id de um registro para alocá-lo a uma turma."""
    registro = Registros.query.get_or_404(registro_id)
    registro.turma_id = turma_id
    db.session.commit()
    flash(f"'{registro.nome}' foi adicionado(a) à turma com sucesso!", 'success')
    return redirect(url_for('detalhes_turma', id=turma_id))


# 3. ADICIONE ESTA NOVA ROTA PARA DESALOCAR UM MENTORADO:
@app.route('/registro/<int:registro_id>/desalocar/<int:turma_id>', methods=['POST'])
def desalocar_mentorado(registro_id, turma_id):
    """Limpa o turma_id de um registro para removê-lo de uma turma."""
    registro = Registros.query.get_or_404(registro_id)
    # Apenas verifica se o registro realmente pertence a esta turma
    if registro.turma_id == turma_id:
        registro.turma_id = None
        db.session.commit()
        flash(f"'{registro.nome}' foi removido(a) da turma.", 'info')
    return redirect(url_for('detalhes_turma', id=turma_id))

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
    Dashboard principal do mentorado. Exibe o progresso
    e os módulos de conteúdo aos quais ele tem acesso.
    """
    # Pega a turma do usuário logado (current_user é disponibilizado pelo Flask-Login)
    turma_do_aluno = current_user.turma
    modulos_da_turma = []
    progresso_percent = 0

    if turma_do_aluno:
        # Pega os módulos associados à turma, ordenados pela coluna 'ordem'
        modulos_da_turma = sorted(turma_do_aluno.modulos, key=lambda m: m.ordem)
        
        # Lógica para calcular o progresso da mentoria
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
                           progresso=progresso_percent)

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


@app.route('/admin')
@admin_required
def admin_dashboard():
    """Página principal do painel de administração."""
    return render_template('admin/admin_dashboard.html')


@app.route('/admin/modulos')
@admin_required
def lista_modulos():
    """Lista todos os módulos para gerenciamento."""
    modulos = Modulos.query.order_by(Modulos.ordem).all()
    return render_template('admin/lista_modulos.html', modulos=modulos)


@app.route('/admin/modulos/novo', methods=['GET', 'POST'])
@admin_required
def novo_modulo():
    """Formulário para criar um novo módulo."""
    if request.method == 'POST':
        novo = Modulos(
            titulo=request.form['titulo'],
            descricao=request.form['descricao'],
            ordem=int(request.form['ordem']),
            thumbnail_url=request.form['thumbnail_url']
        )
        db.session.add(novo)
        db.session.commit()
        flash('Módulo criado com sucesso!', 'success')
        return redirect(url_for('lista_modulos'))
    return render_template('admin/form_modulo.html', titulo="Criar Novo Módulo")


@app.route('/admin/modulos/editar/<int:id>', methods=['GET', 'POST'])
@admin_required
def editar_modulo(id):
    """Formulário para editar um módulo existente."""
    modulo = Modulos.query.get_or_404(id)
    if request.method == 'POST':
        modulo.titulo = request.form['titulo']
        modulo.descricao = request.form['descricao']
        modulo.ordem = int(request.form['ordem'])
        modulo.thumbnail_url = request.form['thumbnail_url']
        db.session.commit()
        flash('Módulo atualizado com sucesso!', 'success')
        return redirect(url_for('lista_modulos'))
    return render_template('admin/form_modulo.html', titulo="Editar Módulo", modulo=modulo)


@app.route('/admin/modulos/deletar/<int:id>', methods=['POST'])
@admin_required
def deletar_modulo(id):
    """Deleta um módulo."""
    modulo = Modulos.query.get_or_404(id)
    db.session.delete(modulo)
    db.session.commit()
    flash('Módulo removido com sucesso!', 'danger')
    return redirect(url_for('lista_modulos'))

@app.route('/admin/registro/<int:id>/definir-senha', methods=['GET', 'POST'])
@admin_required # Protege a rota para que apenas admins possam acessá-la
def definir_senha_mentorado(id):
    """
    Página de administração para definir a senha de um mentorado.
    """
    mentorado = Registros.query.get_or_404(id)
    if request.method == 'POST':
        senha = request.form.get('senha')
        confirmacao_senha = request.form.get('confirmacao_senha')

        if not senha or not confirmacao_senha or senha != confirmacao_senha:
            flash('As senhas não conferem ou estão em branco. Tente novamente.', 'danger')
            return redirect(url_for('definir_senha_mentorado', id=id))

        # Usa o método que criamos no Model para criptografar e salvar a senha
        mentorado.set_password(senha)
        db.session.commit()
        
        flash(f'Senha para {mentorado.nome} definida com sucesso!', 'success')
        return redirect(url_for('detalhe', id=id))

    return render_template('admin/form_definir_senha.html', mentorado=mentorado)

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

@app.route('/turma/<int:turma_id>/avisos/novo', methods=['POST'])
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
    return redirect(url_for('detalhes_turma', id=turma_id))

@app.route('/avisos/deletar/<int:id>', methods=['POST'])
@admin_required
def deletar_aviso(id):
    """Deleta um aviso."""
    aviso = Avisos.query.get_or_404(id)
    turma_id = aviso.turma_id
    db.session.delete(aviso)
    db.session.commit()
    flash('Aviso removido com sucesso!', 'info')
    return redirect(url_for('detalhes_turma', id=turma_id))

# --- INICIALIZAÇÃO DA APLICAÇÃO ---
if __name__ == '__main__':
    # O contexto da aplicação é necessário para que o SQLAlchemy saiba a qual app ele pertence.
    with app.app_context():
        # A linha abaixo pode ser usada para criar as tabelas se elas não existirem,
        # mas o ideal é usar o script 'init_db.py' para isso.
        # db.create_all()
        pass
    app.run(debug=True)
