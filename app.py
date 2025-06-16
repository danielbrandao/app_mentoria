import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from collections import Counter
from datetime import datetime
import secrets


# --- CONFIGURAÇÃO DA APLICAÇÃO E DO BANCO DE DADOS ---
app = Flask(__name__)
# Chave secreta essencial para usar mensagens 'flash' e sessões.
app.config['SECRET_KEY'] = 'uma-chave-secreta-muito-segura'

# Configuração do caminho do banco de dados para garantir que ele seja criado na mesma pasta do projeto.
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'aplicacao.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- MODELS (REPRESENTAÇÃO DAS TABELAS DO BANCO DE DADOS) ---

# Tabela de Associação Muitos-para-Muitos: conecta Turmas e Monitores.
turma_monitores = db.Table('turma_monitores',
    db.Column('turma_id', db.Integer, db.ForeignKey('turmas.id'), primary_key=True),
    db.Column('monitor_id', db.Integer, db.ForeignKey('monitores.id'), primary_key=True)
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

class Registros(db.Model):
    __tablename__ = 'registros'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
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
    # Adicione outros campos que você queira no formulário completo aqui
    
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


# --- ROTAS DA APLICAÇÃO ---

@app.route('/')
def index():
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

    return render_template('index.html', dados=dados_filtrados, total=len(dados_filtrados),
                           perfis=perfis_opcoes, desafios=desafios_opcoes,
                           disponibilidades=disponibilidades_opcoes, filtros_ativos=filtros_ativos)

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



# --- INICIALIZAÇÃO DA APLICAÇÃO ---
if __name__ == '__main__':
    # O contexto da aplicação é necessário para que o SQLAlchemy saiba a qual app ele pertence.
    with app.app_context():
        # A linha abaixo pode ser usada para criar as tabelas se elas não existirem,
        # mas o ideal é usar o script 'init_db.py' para isso.
        # db.create_all()
        pass
    app.run(debug=True)
