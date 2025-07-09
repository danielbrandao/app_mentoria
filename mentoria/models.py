from mentoria import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from flask import current_app
from itsdangerous import URLSafeTimedSerializer as Serializer

# --- Tabelas de Associação (para relações Muitos-para-Muitos) ---

turma_monitores = db.Table('turma_monitores',
    db.Column('turma_id', db.Integer, db.ForeignKey('turmas.id'), primary_key=True),
    db.Column('monitor_id', db.Integer, db.ForeignKey('monitores.id'), primary_key=True)
)

turma_modulos = db.Table('turma_modulos',
    db.Column('turma_id', db.Integer, db.ForeignKey('turmas.id'), primary_key=True),
    db.Column('modulo_id', db.Integer, db.ForeignKey('modulos.id'), primary_key=True)
)


# --- Modelos Principais ---

class Registros(db.Model, UserMixin):
    """Representa os utilizadores, sejam eles inscritos, mentorados ou administradores."""
    __tablename__ = 'registros'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False, index=True)
    whatsapp = db.Column(db.String(20))
    
    # Campos detalhados do novo formulário de inscrição
    programa_interesse = db.Column(db.String(100))
    perfil_detalhado = db.Column(db.String(100))
    desafio_detalhado = db.Column(db.String(100))
    escolaridade = db.Column(db.String(100), nullable=True)
    resumo_jornada = db.Column(db.Text)
    produto_interesse_id = db.Column(db.Integer, db.ForeignKey('produtos.id'))
    
    # Campos de controlo e autenticação
    data_inscricao = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default='Inscrito')
    token_matricula = db.Column(db.String(32), unique=True, nullable=True)
    plano_escolhido = db.Column(db.String(50), nullable=True)
    password_hash = db.Column(db.String(128))
    is_admin = db.Column(db.Boolean, default=False)
    
    # Chave estrangeira para a turma
    turma_id = db.Column(db.Integer, db.ForeignKey('turmas.id'))
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if self.password_hash is None:
            return False
        return check_password_hash(self.password_hash, password)

    def get_reset_token(self, expires_sec=1800):
        s = Serializer(current_app.config['SECRET_KEY'])
        return s.dumps({'user_id': self.id})

    @staticmethod
    def verify_reset_token(token, expires_sec=1800):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token, max_age=expires_sec)['user_id']
        except:
            return None
        return Registros.query.get(user_id)

class Turmas(db.Model):
    """Representa as turmas da mentoria."""
    __tablename__ = 'turmas'
    id = db.Column(db.Integer, primary_key=True)
    nome_turma = db.Column(db.String(100), unique=True, nullable=False)
    descricao = db.Column(db.Text)
    data_inicio = db.Column(db.Date)
    data_fim = db.Column(db.Date)
    status = db.Column(db.String(50), default='Planejamento')
    
    # Relações
    mentorados = db.relationship('Registros', backref='turma', lazy='dynamic')
    encontros = db.relationship('Encontros', backref='turma', lazy=True, cascade="all, delete-orphan")
    avisos = db.relationship('Avisos', backref='turma', lazy=True, cascade="all, delete-orphan")
    monitores = db.relationship('Monitores', secondary=turma_monitores, lazy='subquery',
        backref=db.backref('turmas', lazy=True))
    modulos = db.relationship('Modulos', secondary=turma_modulos, lazy='subquery',
        backref=db.backref('turmas', lazy=True))

class Monitores(db.Model):
    """Representa os monitores da plataforma."""
    __tablename__ = 'monitores'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    whatsapp = db.Column(db.String(20))
    resumo = db.Column(db.Text)
    perfil = db.Column(db.String(100))
    
    # Relações
    encontros_liderados = db.relationship('Encontros', backref='monitor', lazy=True)

class Modulos(db.Model):
    """Representa os módulos de conteúdo."""
    __tablename__ = 'modulos'
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(150), unique=True, nullable=False)
    descricao = db.Column(db.Text)
    ordem = db.Column(db.Integer, default=0)
    thumbnail_url = db.Column(db.String(255))
    
    # Relações
    conteudos = db.relationship('Conteudos', backref='modulo', lazy=True, cascade="all, delete-orphan")

class Conteudos(db.Model):
    """Representa um conteúdo individual (aula, PDF, link) dentro de um módulo."""
    __tablename__ = 'conteudos'
    id = db.Column(db.Integer, primary_key=True)
    modulo_id = db.Column(db.Integer, db.ForeignKey('modulos.id'), nullable=False)
    titulo = db.Column(db.String(150), nullable=False)
    tipo = db.Column(db.String(50))
    url_conteudo = db.Column(db.String(255), nullable=False)
    descricao = db.Column(db.Text)
    ordem = db.Column(db.Integer, default=0)
    thumbnail_url = db.Column(db.String(255), nullable=True)

class Avisos(db.Model):
    """Representa os avisos publicados para uma turma."""
    __tablename__ = 'avisos'
    id = db.Column(db.Integer, primary_key=True)
    turma_id = db.Column(db.Integer, db.ForeignKey('turmas.id'), nullable=False)
    titulo = db.Column(db.String(150), nullable=False)
    conteudo = db.Column(db.Text, nullable=False)
    data_publicacao = db.Column(db.DateTime, default=datetime.utcnow)

class Encontros(db.Model):
    """Representa os encontros (aulas ao vivo) de uma turma."""
    __tablename__ = 'encontros'
    id = db.Column(db.Integer, primary_key=True)
    turma_id = db.Column(db.Integer, db.ForeignKey('turmas.id'), nullable=False)
    monitor_id = db.Column(db.Integer, db.ForeignKey('monitores.id'), nullable=False)
    titulo = db.Column(db.String(150), nullable=False)
    descricao = db.Column(db.Text)
    data_encontro = db.Column(db.DateTime)
    link_meet = db.Column(db.String(200))
    status = db.Column(db.String(50), default='Agendado')

class Produtos(db.Model):
    """Representa os produtos/serviços oferecidos (mentorias, cursos)."""
    __tablename__ = 'produtos'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), unique=True, nullable=False)
    publico_alvo = db.Column(db.String(50), index=True)
    descricao = db.Column(db.Text)
    valor = db.Column(db.Float)
    
    # Relações
    interessados = db.relationship('Registros', backref='produto_interesse', lazy='dynamic')


# --- Configuração do Flask-Login ---
@login_manager.user_loader
def load_user(user_id):
    """Função necessária para o Flask-Login saber como carregar um utilizador a partir da sessão."""
    return Registros.query.get(int(user_id))