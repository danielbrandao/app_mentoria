from . import admin

from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from mentoria import db
from mentoria.models import Registros, Turmas, Modulos, Conteudos, Avisos, Monitores, Encontros
from datetime import datetime

from . import admin # Importa o próprio blueprint
from .utils import admin_required # Vamos criar este decorador

# --- ROTAS DO PAINEL DE ADMINISTRAÇÃO ---


@admin.route('/admin/inscricoes')
@admin_required # Protegida para administradores
def admin_lista_inscricoes():
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

@admin.route('/admin/inscricao/<int:id>/detalhes')
@admin_required
def admin_detalhe_inscricao(id):
    """Exibe os detalhes completos de um único inscrito."""
    registro = Registros.query.get_or_404(id)
    return render_template('admin/detalhe.html', registro=registro)

@admin.route('/admin/registro/<int:id>/definir-senha', methods=['GET', 'POST'])
@admin_required
def definir_senha_mentorado(id):
    """Página de administração para definir a senha de um mentorado."""
    mentorado = Registros.query.get_or_404(id)
    if request.method == 'POST':
        senha = request.form.get('senha')
        confirmacao_senha = request.form.get('confirmacao_senha')

        if not senha or not confirmacao_senha or senha != confirmacao_senha:
            flash('As senhas não conferem ou estão em branco. Tente novamente.', 'danger')
            return redirect(url_for('admin.definir_senha_mentorado', id=id))

        mentorado.set_password(senha)
        db.session.commit()
        
        flash(f'Senha para {mentorado.nome} definida com sucesso!', 'success')
        return redirect(url_for('admin.admin_detalhe_inscricao', id=id))

    return render_template('admin/form_definir_senha.html', mentorado=mentorado)


@admin.route('/admin/detalhe/<int:id>')
@admin_required
def detalhe(id):
    registro = Registros.query.get_or_404(id)
    return render_template('detalhe.html', registro=registro)

@admin.route('/admin/resumo')
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

@admin.route('/admin/monitores')
@admin_required
def admin_lista_monitores():
    """Lista todos os monitores para gestão do administrador."""
    monitores = Monitores.query.order_by(Monitores.nome).all()
    return render_template('admin/lista_monitores.html', monitores=monitores)

@admin.route('/monitores/novo', methods=['GET', 'POST'])
@admin_required
def admin_novo_monitor():
    if request.method == 'POST':
        email = request.form.get('email')

        # --- LÓGICA DE VALIDAÇÃO ADICIONADA ---
        if Monitores.query.filter_by(email=email).first():
            flash('Este e-mail já está a ser utilizado por outro monitor.', 'danger')
            return redirect(url_for('admin.admin_novo_monitor'))
        # --- FIM DA VALIDAÇÃO ---

        novo = Monitores(nome=request.form['nome'], email=email, whatsapp=request.form['whatsapp'],
                         resumo=request.form['resumo'], perfil=request.form['perfil'])
        db.session.add(novo)
        db.session.commit()
        flash('Monitor registado com sucesso!', 'success')
        return redirect(url_for('admin.admin_lista_monitores'))
    return render_template('admin/form_monitor.html', titulo='Novo Monitor')


@admin.route('/admin/monitores/editar/<int:id>', methods=['GET', 'POST'])
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
        return redirect(url_for('admin.admin_lista_monitores'))
    return render_template('admin/form_monitor.html', titulo='Editar Monitor', monitor=monitor)


@admin.route('/admin/monitores/deletar/<int:id>', methods=['POST'])
@admin_required
def admin_deletar_monitor(id):
    """Deleta um monitor do sistema."""
    monitor = Monitores.query.get_or_404(id)
    db.session.delete(monitor)
    db.session.commit()
    flash('Monitor removido com sucesso!', 'danger')
    return redirect(url_for('admin.admin_lista_monitores'))


@admin.route('/admin')
@admin_required
def admin_dashboard():
    """Página principal do painel de administração (versão robusta)."""
    try:
        # Tenta calcular os totais
        total_registros = Registros.query.count()
        total_modulos = Modulos.query.count()
        total_turmas_ativas = Turmas.query.filter_by(status='Ativa').count()
    
    except Exception as e:
        # Se ocorrer um erro (ex: tabela não existe), envia uma mensagem de erro
        # e define os totais como 0 para a página não quebrar.
        flash(f"Ocorreu um erro ao carregar os dados do dashboard: {e}. Verifique se todas as tabelas da base de dados foram criadas.", "danger")
        total_registros = 0
        total_modulos = 0
        total_turmas_ativas = 0

    # Envia os totais (ou 0 em caso de erro) para o template
    return render_template('admin/admin_dashboard.html',
                           total_registros=total_registros,
                           total_modulos=total_modulos,
                           total_turmas_ativas=total_turmas_ativas)

@admin.route('/admin/modulos')
@admin_required
def admin_lista_modulos():
    """Lista todos os módulos para gestão do administrador."""
    modulos = Modulos.query.order_by(Modulos.ordem).all()
    return render_template('admin/lista_modulos.html', modulos=modulos)


@admin.route('/modulos/novo', methods=['GET', 'POST'])
@admin_required
def admin_novo_modulo():
    if request.method == 'POST':
        titulo = request.form.get('titulo')

        # --- LÓGICA DE VALIDAÇÃO ADICIONADA ---
        if Modulos.query.filter_by(titulo=titulo).first():
            flash(f"Já existe um módulo com o título '{titulo}'. Por favor, escolha outro.", 'danger')
            return redirect(url_for('admin.admin_novo_modulo'))
        # --- FIM DA VALIDAÇÃO ---

        novo = Modulos(titulo=titulo, descricao=request.form['descricao'],
                       ordem=int(request.form.get('ordem', 0)),
                       thumbnail_url=request.form.get('thumbnail_url'))
        db.session.add(novo)
        db.session.commit()
        flash('Módulo criado com sucesso!', 'success')
        return redirect(url_for('admin.admin_lista_modulos'))
    return render_template('admin/form_modulo.html', titulo="Criar Novo Módulo")


@admin.route('/admin/modulos/editar/<int:id>', methods=['GET', 'POST'])
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
        return redirect(url_for('admin.admin_lista_modulos'))
    return render_template('admin/form_modulo.html', titulo="Editar Módulo", modulo=modulo)



@admin.route('/admin/modulos/deletar/<int:id>', methods=['POST'])
@admin_required
def admin_deletar_modulo(id):
    """Deleta um módulo e todos os seus conteúdos associados (devido ao cascade)."""
    modulo = Modulos.query.get_or_404(id)
    db.session.delete(modulo)
    db.session.commit()
    flash('Módulo removido com sucesso!', 'danger')
    return redirect(url_for('admin.admin_lista_modulos'))

@admin.route('/admin/modulos/<int:id>/detalhes')
@admin_required
def admin_detalhes_modulo(id):
    """Página para ver e gerir os conteúdos de um módulo específico."""
    modulo = Modulos.query.get_or_404(id)
    conteudos = sorted(modulo.conteudos, key=lambda c: c.ordem)
    return render_template('admin/detalhes_modulo.html', modulo=modulo, conteudos=conteudos)


@admin.route('/admin/turma/<int:turma_id>/avisos/novo', methods=['POST'])
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
    return redirect(url_for('admin.admin_detalhes_turma', id=turma_id))


@admin.route('/admin/avisos/deletar/<int:id>', methods=['POST'])
@admin_required
def deletar_aviso(id):
    """Deleta um aviso."""
    aviso = Avisos.query.get_or_404(id)
    turma_id = aviso.turma_id
    db.session.delete(aviso)
    db.session.commit()
    flash('Aviso removido com sucesso!', 'info')
    return redirect(url_for('admin.admin_detalhes_turma', id=turma_id))

# Player de video
@admin.route('/conteudo/<int:id>')
@login_required
def ver_conteudo(id):
    """
    Exibe uma página dedicada para um conteúdo específico,
    com um leitor de vídeo incorporado para o Google Drive.
    """
    conteudo = Conteudos.query.get_or_404(id)
    
    # Verificação de segurança: o aluno tem acesso a este módulo?
    turma_do_aluno = current_user.turma
    if not turma_do_aluno or conteudo.modulo not in turma_do_aluno.modulos:
        flash("Não tem permissão para aceder a este conteúdo.", "danger")
        return redirect(url_for('main.area_membros'))

    embed_url = None
    # Verifica se é um vídeo do Google Drive
    if conteudo.tipo == 'Vídeo':
        # Caso seja Bunny Stream
        if 'video.bunnycdn.com' in conteudo.url_conteudo:
            embed_url = conteudo.url_conteudo

        # Caso seja Google Drive
        elif 'drive.google.com' in conteudo.url_conteudo:
            match = re.search(r'/d/([a-zA-Z0-9_-]+)', conteudo.url_conteudo)
            if match:
                file_id = match.group(1)
                embed_url = f"https://drive.google.com/file/d/{file_id}/preview?rm=minimal"
            else:
                embed_url = conteudo.url_conteudo

        else:
            # Caso seja outro link de vídeo direto
            embed_url = conteudo.url_conteudo

    else:
        # Para outros tipos de conteúdo, usa o link diretamente
        embed_url = conteudo.url_conteudo

    return render_template('conteudo.html', conteudo=conteudo, embed_url=embed_url)


@admin.route('/admin/modulos/<int:modulo_id>/conteudo/novo', methods=['POST'])
@admin_required
def admin_novo_conteudo(modulo_id):
    """Processa o formulário para adicionar um novo conteúdo, agora com upload de imagem."""
    titulo = request.form.get('titulo')
    url_conteudo = request.form.get('url_conteudo')
    thumbnail_url = request.form.get('thumbnail_url')
    
    # --- INÍCIO DA LÓGICA DE UPLOAD ---
    file = request.files.get('thumbnail_file')
    
    # Se um ficheiro foi enviado, ele tem prioridade sobre a URL
    if file and allowed_file(file.filename):
        # Garante um nome de ficheiro seguro e único
        filename = str(int(time.time())) + '_' + secure_filename(file.filename)
        # Salva o ficheiro na nossa pasta de uploads
        file.path = os.path.join(admin.config['UPLOAD_FOLDER'], filename)
        file.save(file.path)
        # Guarda o caminho relativo para ser usado no HTML
        thumbnail_url = f"/static/img/uploads/{filename}"
    # --- FIM DA LÓGICA DE UPLOAD ---

    if titulo and url_conteudo:
        novo = Conteudos(
            modulo_id=modulo_id, titulo=titulo, tipo=request.form.get('tipo'),
            url_conteudo=url_conteudo, descricao=request.form.get('descricao'),
            ordem=int(request.form.get('ordem', 0)),
            thumbnail_url=thumbnail_url # Salva o caminho do upload ou a URL fornecida
        )
        db.session.add(novo)
        db.session.commit()
        flash('Conteúdo adicionado com sucesso!', 'success')
    else:
        flash('Título e URL do conteúdo são obrigatórios.', 'danger')
        
    return redirect(url_for('admin.admin_detalhes_modulo', id=modulo_id))

@admin.route('/admin/conteudo/editar/<int:id>', methods=['GET', 'POST'])
@admin_required
def admin_editar_conteudo(id):
    """Exibe e processa o formulário para editar um conteúdo, agora com upload de imagem."""
    conteudo = Conteudos.query.get_or_404(id)
    if request.method == 'POST':
        conteudo.titulo = request.form['titulo']
        conteudo.tipo = request.form['tipo']
        conteudo.url_conteudo = request.form['url_conteudo']
        conteudo.descricao = request.form['descricao']
        conteudo.ordem = int(request.form['ordem'])
        
        # --- INÍCIO DA LÓGICA DE UPLOAD ---
        file = request.files.get('thumbnail_file')
        thumbnail_url = request.form.get('thumbnail_url')
        
        if file and allowed_file(file.filename):
            filename = str(int(time.time())) + '_' + secure_filename(file.filename)
            file.path = os.path.join(admin.config['UPLOAD_FOLDER'], filename)
            file.save(file.path)
            conteudo.thumbnail_url = f"/static/img/uploads/{filename}"
        else:
            # Se nenhum ficheiro novo for enviado, usa a URL do formulário
            conteudo.thumbnail_url = thumbnail_url
        # --- FIM DA LÓGICA DE UPLOAD ---
            
        db.session.commit()
        flash('Conteúdo atualizado com sucesso!', 'success')
        return redirect(url_for('admin.admin_detalhes_modulo', id=conteudo.modulo_id))
        
    return render_template('admin/form_conteudo.html', titulo="Editar Conteúdo", conteudo=conteudo)


@admin.route('/admin/conteudo/deletar/<int:id>', methods=['POST'])
@admin_required
def admin_deletar_conteudo(id):
    """Deleta um conteúdo."""
    conteudo = Conteudos.query.get_or_404(id)
    modulo_id = conteudo.modulo_id
    db.session.delete(conteudo)
    db.session.commit()
    flash('Conteúdo removido com sucesso!', 'info')
    return redirect(url_for('admin.admin_detalhes_modulo', id=modulo_id))

# --- ROTAS PARA GERENCIAR ENCONTROS DE UMA TURMA ---

@admin.route('/admin/turma/<int:turma_id>/encontros/novo', methods=['GET', 'POST'])
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
        return redirect(url_for('admin.admin_detalhes_turma', id=turma_id))
    
    return render_template('admin/form_encontro.html', titulo='Agendar Novo Encontro', turma=turma, monitores_da_turma=monitores_da_turma)

@admin.route('/admin/encontro/editar/<int:id>', methods=['GET', 'POST'])
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
        return redirect(url_for('admin.admin_detalhes_turma', id=turma.id))

    return render_template('admin/form_encontro.html', titulo='Editar Encontro', encontro=encontro, turma=turma, monitores_da_turma=monitores_da_turma)

@admin.route('/admin/encontro/deletar/<int:id>', methods=['POST'])
@admin_required
def deletar_encontro(id):
    """Rota para deletar um encontro."""
    encontro = Encontros.query.get_or_404(id)
    turma_id = encontro.turma_id
    db.session.delete(encontro)
    db.session.commit()
    flash('Encontro removido com sucesso!', 'danger')
    return redirect(url_for('admin.admin_detalhes_turma', id=turma_id))

# --- ROTAS PARA GERENCIAR A ALOCAÇÃO DE MENTORADOS ---


# 2. ROTA PARA ALOCAR UM MENTORADO:
@admin.route('/admin/registro/<int:registro_id>/alocar/<int:turma_id>', methods=['POST'])
@admin_required
def alocar_mentorado(registro_id, turma_id):
    """Define o turma_id de um registo para alocá-lo a uma turma."""
    registro = Registros.query.get_or_404(registro_id)
    registro.turma_id = turma_id
    db.session.commit()
    flash(f"'{registro.nome}' foi adicionado(a) à turma com sucesso!", 'success')
    return redirect(url_for('admin.admin_detalhes_turma', id=turma_id))

# --- ROTA Desalocar mentorado de uma turma ---
@admin.route('/admin/registro/<int:registro_id>/desalocar/<int:turma_id>', methods=['POST'])
@admin_required
def desalocar_mentorado(registro_id, turma_id):
    """Limpa o turma_id de um registo para removê-lo de uma turma."""
    registro = Registros.query.get_or_404(registro_id)
    if registro.turma_id == turma_id:
        registro.turma_id = None
        db.session.commit()
        flash(f"'{registro.nome}' foi removido(a) da turma.", 'info')
    return redirect(url_for('admin.admin_detalhes_turma', id=turma_id))

# --- ROTAS PARA GERENCIAR TURMAS ---

@admin.route('/admin/turmas')
@admin_required
def admin_lista_turmas():
    turmas = Turmas.query.order_by(Turmas.data_inicio.desc()).all()
    return render_template('admin/lista_turmas.html', turmas=turmas)

@admin.route('/turmas/nova', methods=['GET', 'POST'])
@admin_required
def admin_nova_turma():
    monitores_disponiveis = Monitores.query.order_by(Monitores.nome).all()
    if request.method == 'POST':
        nome_turma = request.form.get('nome_turma')
        
        # --- LÓGICA DE VALIDAÇÃO ADICIONADA ---
        if Turmas.query.filter_by(nome_turma=nome_turma).first():
            flash(f"Já existe uma turma com o nome '{nome_turma}'. Por favor, escolha outro nome.", 'danger')
            return redirect(url_for('admin.admin_nova_turma'))
        # --- FIM DA VALIDAÇÃO ---
        
        data_inicio = datetime.strptime(request.form['data_inicio'], '%Y-%m-%d').date() if request.form['data_inicio'] else None
        data_fim = datetime.strptime(request.form['data_fim'], '%Y-%m-%d').date() if request.form['data_fim'] else None
        nova = Turmas(nome_turma=nome_turma, descricao=request.form['descricao'],
                      data_inicio=data_inicio, data_fim=data_fim, status=request.form['status'])
        for id_monitor in request.form.getlist('monitores'):
            monitor = Monitores.query.get(id_monitor)
            if monitor:
                nova.monitores.append(monitor)
        db.session.add(nova)
        db.session.commit()
        flash('Turma criada com sucesso!', 'success')
        return redirect(url_for('admin.admin_lista_turmas'))
    return render_template('admin/form_turma.html', titulo='Nova Turma', monitores_disponiveis=monitores_disponiveis)


@admin.route('/admin/turmas/editar/<int:id>', methods=['GET', 'POST'])
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
        return redirect(url_for('admin.admin_lista_turmas'))
        
    return render_template('admin/form_turma.html', titulo='Editar Turma', turma=turma, monitores_disponiveis=monitores_disponiveis)

@admin.route('/admin/turma/<int:id>/detalhes')
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

@admin.route('/admin/turma/<int:turma_id>/vincular-modulos', methods=['POST'])
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
    return redirect(url_for('admin.admin_detalhes_turma', id=turma_id))