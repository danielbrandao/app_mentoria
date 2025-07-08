from mentoria import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from flask import current_app
from itsdangerous import URLSafeTimedSerializer as Serializer

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

class Produtos(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), unique=True, nullable=False)
    publico_alvo = db.Column(db.String(50), index=True) # Ex: 'DEV', 'Educadores'
    descricao = db.Column(db.Text)
    valor = db.Column(db.Float)

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

class Registros(db.Model, UserMixin):
    __tablename__ = 'registros'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    whatsapp = db.Column(db.String(20)) # Renomeado de 'fone' para 'whatsapp'
    
    # --- CAMPOS ANTIGOS (serão menos usados para novas inscrições) ---
    perfil = db.Column(db.String(100))
    desafio = db.Column(db.String(100))
    disponibilidade = db.Column(db.String(100))
    mensagem = db.Column(db.Text)

    # --- NOVOS CAMPOS DETALHADOS ---
    #programa_interesse = db.Column(db.String(100)) # Ex: "DEV+", "IA.edu"
    produto_interesse_id = db.Column(db.Integer, db.ForeignKey('produtos.id'))
    produto_interesse = db.relationship('Produtos', backref='interessados')
    perfil_detalhado = db.Column(db.String(100)) # Ex: "Backend", "Professor Universitário"
    desafio_detalhado = db.Column(db.String(100)) # Ex: "Migrar de área", "Aprender IA do zero"
    escolaridade = db.Column(db.String(100), nullable=True) # Apenas para IA.edu
    resumo_jornada = db.Column(db.Text) # Resumo sobre a jornada
    
    # --- Campos de Controlo e Autenticação (sem alterações) ---
    data_inscricao = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default='Inscrito')
    token_matricula = db.Column(db.String(32), unique=True, nullable=True)
    plano_escolhido = db.Column(db.String(50), nullable=True)
    password_hash = db.Column(db.String(128))
    is_admin = db.Column(db.Boolean, default=False)
    turma_id = db.Column(db.Integer, db.ForeignKey('turmas.id'))

    def get_reset_token(self, expires_sec=1800):
        """Gera um token seguro com tempo de expiração (30 minutos por defeito)."""
        s = Serializer(current_app.config['SECRET_KEY'])
        return s.dumps({'user_id': self.id})

    @staticmethod
    def verify_reset_token(token, expires_sec=1800):
        """Verifica o token. Se for válido, retorna o utilizador correspondente."""
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token, max_age=expires_sec)['user_id']
        except:
            return None
        return Registros.query.get(user_id)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

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
    # NOVO CAMPO ADICIONADO:
    thumbnail_url = db.Column(db.String(255), nullable=True)

class Avisos(db.Model):
    __tablename__ = 'avisos'
    id = db.Column(db.Integer, primary_key=True)
    turma_id = db.Column(db.Integer, db.ForeignKey('turmas.id'), nullable=False)
    titulo = db.Column(db.String(150), nullable=False)
    conteudo = db.Column(db.Text, nullable=False)
    data_publicacao = db.Column(db.DateTime, default=datetime.utcnow)



# Função auxiliar para verificar se a extensão do ficheiro é permitida
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Função user_loader necessária para o Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return Registros.query.get(int(user_id))
