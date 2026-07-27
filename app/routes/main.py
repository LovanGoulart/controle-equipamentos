from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, Response
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from app import db
from app.models.models import Usuario, Equipamento, Observacao, Historico, Configuracao
from app.routes.auth import registrar_historico
import csv
import io

bp = Blueprint('main', __name__)

@bp.route('/')
@login_required
def index():
    return redirect(url_for('main.dashboard'))

@bp.route('/dashboard')
@login_required
def dashboard():
    config = Configuracao.query.first()

    total = Equipamento.query.count()
    baixados = Equipamento.query.filter_by(baixado=True).count()
    ativos = total - baixados

    hoje = date.today()
    proximos = []
    vencidos = []
    sem_manutencao = []

    dias_alertas = [int(d) for d in config.dias_lembrete_manutencao.split(',') if d.strip().isdigit()]

    equipamentos = Equipamento.query.filter_by(baixado=False).all()
    for eq in equipamentos:
        if not eq.proxima_manutencao:
            sem_manutencao.append(eq)
        else:
            delta = (eq.proxima_manutencao - hoje).days
            if delta < 0:
                vencidos.append(eq)
            elif any(delta <= d for d in dias_alertas):
                proximos.append(eq)

    setores = db.session.query(Equipamento.setor, db.func.count(Equipamento.id)).filter(Equipamento.baixado==False).group_by(Equipamento.setor).all()
    areas = db.session.query(Equipamento.area_patrimonial, db.func.count(Equipamento.id)).filter(Equipamento.baixado==False).group_by(Equipamento.area_patrimonial).all()

    return render_template('dashboard.html',
        total=total, baixados=baixados, ativos=ativos,
        proximos=proximos, vencidos=vencidos, sem_manutencao=sem_manutencao,
        setores=setores, areas=areas, config=config
    )

@bp.route('/equipamentos')
@login_required
def equipamentos():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 25, type=int)

    query = Equipamento.query

    filtro_setor = request.args.get('setor', '').lower()
    filtro_area = request.args.get('area_patrimonial', '').lower()
    filtro_local = request.args.get('localizacao', '').lower()
    filtro_equip = request.args.get('equipamento', '').lower()
    filtro_status = request.args.get('status', '')
    filtro_manutencao = request.args.get('manutencao', '')
    filtro_usuario = request.args.get('usuario_id', '')
    busca = request.args.get('busca', '').lower()
    ordenar = request.args.get('ordenar', 'data_inclusao')
    direcao = request.args.get('direcao', 'desc')

    if filtro_setor:
        query = query.filter(Equipamento.setor == filtro_setor)
    if filtro_area:
        query = query.filter(Equipamento.area_patrimonial == filtro_area)
    if filtro_local:
        query = query.filter(Equipamento.localizacao == filtro_local)
    if filtro_equip:
        query = query.filter(Equipamento.equipamento == filtro_equip)
    if filtro_status == 'ativos':
        query = query.filter_by(baixado=False)
    elif filtro_status == 'baixados':
        query = query.filter_by(baixado=True)
    if filtro_manutencao == 'proxima':
        hoje = date.today()
        dias_alertas = [30, 15, 7, 1]
        query = query.filter(Equipamento.proxima_manutencao != None)
        query = query.filter(Equipamento.proxima_manutencao <= hoje + timedelta(days=30))
    elif filtro_manutencao == 'vencida':
        query = query.filter(Equipamento.proxima_manutencao < date.today())
    elif filtro_manutencao == 'sem':
        query = query.filter(Equipamento.proxima_manutencao == None)
    if filtro_usuario:
        query = query.filter_by(usuario_id=int(filtro_usuario))

    if busca:
        busca_like = f'%{busca}%'
        query = query.filter(
            db.or_(
                Equipamento.patrimonio.ilike(busca_like),
                Equipamento.equipamento.ilike(busca_like),
                Equipamento.area_patrimonial.ilike(busca_like),
                Equipamento.setor.ilike(busca_like),
                Equipamento.localizacao.ilike(busca_like),
                Equipamento.ip.ilike(busca_like),
                Equipamento.sistema_operacional.ilike(busca_like),
                Equipamento.processador.ilike(busca_like),
            )
        )

    if ordenar == 'patrimonio':
        col = Equipamento.patrimonio
    elif ordenar == 'data':
        col = Equipamento.data_inclusao
    elif ordenar == 'equipamento':
        col = Equipamento.equipamento
    elif ordenar == 'setor':
        col = Equipamento.setor
    elif ordenar == 'tempo_uso':
        col = Equipamento.data_inclusao
    elif ordenar == 'ultima_manutencao':
        col = Equipamento.ultima_manutencao
    elif ordenar == 'proxima_manutencao':
        col = Equipamento.proxima_manutencao
    else:
        col = Equipamento.data_inclusao

    if direcao == 'desc':
        col = col.desc()

    query = query.order_by(Equipamento.baixado.asc(), col)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    setores = db.session.query(Equipamento.setor).distinct().all()
    areas = db.session.query(Equipamento.area_patrimonial).distinct().all()
    locais = db.session.query(Equipamento.localizacao).distinct().all()
    equip_tipos = db.session.query(Equipamento.equipamento).distinct().all()
    usuarios = Usuario.query.all()

    config = Configuracao.query.first()

    return render_template('equipamentos.html',
        equipamentos=pagination.items,
        pagination=pagination,
        setores=setores, areas=areas, locais=locais,
        equip_tipos=equip_tipos, usuarios=usuarios,
        filtros=request.args, config=config
    )

@bp.route('/equipamento/novo', methods=['GET', 'POST'])
@login_required
def equipamento_novo():
    if request.method == 'POST':
        eq = Equipamento(
            patrimonio=request.form.get('patrimonio', '').strip().lower(),
            data_inclusao=datetime.strptime(request.form.get('data_inclusao', str(date.today())), '%Y-%m-%d').date() if request.form.get('data_inclusao') else date.today(),
            baixado=request.form.get('baixado') == 'on',
            data_baixa=datetime.strptime(request.form.get('data_baixa'), '%Y-%m-%d').date() if request.form.get('data_baixa') else None,
            equipamento=request.form.get('equipamento', '').strip().lower(),
            area_patrimonial=request.form.get('area_patrimonial', '').strip().lower(),
            setor=request.form.get('setor', '').strip().lower(),
            localizacao=request.form.get('localizacao', '').strip().lower(),
            especificacao=request.form.get('especificacao', '').strip().lower(),
            ultima_manutencao=datetime.strptime(request.form.get('ultima_manutencao'), '%Y-%m-%d').date() if request.form.get('ultima_manutencao') else None,
            proxima_manutencao=datetime.strptime(request.form.get('proxima_manutencao'), '%Y-%m-%d').date() if request.form.get('proxima_manutencao') else None,
            sistema_operacional=request.form.get('sistema_operacional', '').strip().lower(),
            placa_mae=request.form.get('placa_mae', '').strip().lower(),
            processador=request.form.get('processador', '').strip().lower(),
            memoria_ram=request.form.get('memoria_ram', '').strip().lower(),
            armazenamento=request.form.get('armazenamento', '').strip().lower(),
            ip=request.form.get('ip', '').strip().lower(),
            usuario_id=current_user.id
        )
        db.session.add(eq)
        db.session.commit()
        registrar_historico('CADASTRO', 'Equipamento', eq.id, f'Equipamento cadastrado: {eq.patrimonio}')
        flash('Equipamento cadastrado com sucesso!', 'success')
        return redirect(url_for('main.equipamentos'))

    config = Configuracao.query.first()
    return render_template('equipamento_form.html', equipamento=None, config=config)

@bp.route('/equipamento/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def equipamento_editar(id):
    eq = Equipamento.query.get_or_404(id)

    if not current_user.is_admin and eq.usuario_id != current_user.id:
        flash('Você não tem permissão para editar este equipamento.', 'danger')
        return redirect(url_for('main.equipamentos'))

    if request.method == 'POST':
        eq.patrimonio = request.form.get('patrimonio', '').strip().lower()
        eq.data_inclusao = datetime.strptime(request.form.get('data_inclusao', str(date.today())), '%Y-%m-%d').date() if request.form.get('data_inclusao') else date.today()
        eq.baixado = request.form.get('baixado') == 'on'
        eq.data_baixa = datetime.strptime(request.form.get('data_baixa'), '%Y-%m-%d').date() if request.form.get('data_baixa') else None
        eq.equipamento = request.form.get('equipamento', '').strip().lower()
        eq.area_patrimonial = request.form.get('area_patrimonial', '').strip().lower()
        eq.setor = request.form.get('setor', '').strip().lower()
        eq.localizacao = request.form.get('localizacao', '').strip().lower()
        eq.especificacao = request.form.get('especificacao', '').strip().lower()
        eq.ultima_manutencao = datetime.strptime(request.form.get('ultima_manutencao'), '%Y-%m-%d').date() if request.form.get('ultima_manutencao') else None
        eq.proxima_manutencao = datetime.strptime(request.form.get('proxima_manutencao'), '%Y-%m-%d').date() if request.form.get('proxima_manutencao') else None
        eq.sistema_operacional = request.form.get('sistema_operacional', '').strip().lower()
        eq.placa_mae = request.form.get('placa_mae', '').strip().lower()
        eq.processador = request.form.get('processador', '').strip().lower()
        eq.memoria_ram = request.form.get('memoria_ram', '').strip().lower()
        eq.armazenamento = request.form.get('armazenamento', '').strip().lower()
        eq.ip = request.form.get('ip', '').strip().lower()
        eq.data_atualizacao = datetime.now()

        db.session.commit()
        registrar_historico('EDICAO', 'Equipamento', eq.id, f'Equipamento editado: {eq.patrimonio}')
        flash('Equipamento atualizado com sucesso!', 'success')
        return redirect(url_for('main.equipamentos'))

    config = Configuracao.query.first()
    return render_template('equipamento_form.html', equipamento=eq, config=config)

@bp.route('/equipamento/<int:id>/excluir', methods=['POST'])
@login_required
def equipamento_excluir(id):
    if not current_user.is_admin:
        flash('Apenas administradores podem excluir equipamentos.', 'danger')
        return redirect(url_for('main.equipamentos'))

    eq = Equipamento.query.get_or_404(id)
    patrimonio = eq.patrimonio
    db.session.delete(eq)
    db.session.commit()
    registrar_historico('EXCLUSAO', 'Equipamento', id, f'Equipamento excluído: {patrimonio}')
    flash('Equipamento excluído com sucesso!', 'success')
    return redirect(url_for('main.equipamentos'))

@bp.route('/equipamento/<int:id>')
@login_required
def equipamento_detalhe(id):
    eq = Equipamento.query.get_or_404(id)
    config = Configuracao.query.first()
    return render_template('equipamento_detail.html', equipamento=eq, config=config)

@bp.route('/equipamento/<int:id>/observacao', methods=['POST'])
@login_required
def adicionar_observacao(id):
    eq = Equipamento.query.get_or_404(id)
    texto = request.form.get('texto', '').strip().lower()

    if texto:
        obs = Observacao(
            equipamento_id=id,
            usuario_id=current_user.id,
            texto=texto,
            data=datetime.now()
        )
        db.session.add(obs)
        db.session.commit()
        registrar_historico('OBSERVACAO', 'Equipamento', id, f'Observação adicionada')
        flash('Observação adicionada!', 'success')

    return redirect(url_for('main.equipamento_detalhe', id=id))

@bp.route('/historico')
@login_required
def historico():
    page = request.args.get('page', 1, type=int)
    query = Historico.query.order_by(Historico.data.desc())
    pagination = query.paginate(page=page, per_page=50, error_out=False)
    config = Configuracao.query.first()
    return render_template('historico.html', historico=pagination.items, pagination=pagination, config=config)

@bp.route('/relatorios')
@login_required
def relatorios():
    config = Configuracao.query.first()
    return render_template('relatorios.html', config=config)

@bp.route('/exportar/csv')
@login_required
def exportar_csv():
    equipamentos = Equipamento.query.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Patrimônio', 'Equipamento', 'Área', 'Setor', 'Localização', 'SO', 'Processador', 'RAM', 'Armazenamento', 'IP', 'Inclusão', 'Baixado', 'Data Baixa', 'Tempo Uso', 'Última Manut.', 'Próxima Manut.'])

    for eq in equipamentos:
        writer.writerow([
            eq.patrimonio, eq.equipamento, eq.area_patrimonial, eq.setor, eq.localizacao,
            eq.sistema_operacional, eq.processador, eq.memoria_ram, eq.armazenamento, eq.ip,
            eq.data_inclusao, 'Sim' if eq.baixado else 'Não', eq.data_baixa or '',
            eq.tempo_uso_formatado, eq.ultima_manutencao or '', eq.proxima_manutencao or ''
        ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=equipamentos.csv'}
    )

@bp.route('/equipamento/<int:id>/confirmar-manutencao', methods=['POST'])
@login_required
def confirmar_manutencao(id):
    eq = Equipamento.query.get_or_404(id)

    if not current_user.is_admin and eq.usuario_id != current_user.id:
        flash('Você não tem permissão para editar este equipamento.', 'danger')
        return redirect(url_for('main.equipamento_detalhe', id=id))

    data_manutencao = date.today()

    if eq.proxima_manutencao and eq.ultima_manutencao:
        intervalo = (eq.proxima_manutencao - eq.ultima_manutencao).days
        proxima = data_manutencao + timedelta(days=intervalo)
    elif eq.proxima_manutencao and eq.proxima_manutencao > data_manutencao:
        intervalo = (eq.proxima_manutencao - data_manutencao).days
        if intervalo <= 0:
            intervalo = 180
        proxima = data_manutencao + timedelta(days=intervalo)
    else:
        proxima = data_manutencao + timedelta(days=180)

    eq.ultima_manutencao = data_manutencao
    eq.proxima_manutencao = proxima
    eq.data_atualizacao = datetime.now()

    db.session.commit()
    registrar_historico('MANUTENCAO', 'Equipamento', eq.id, 
        f'Manutenção confirmada. Próxima: {proxima.strftime("%d/%m/%Y")}')
    flash(f'Manutenção confirmada! Próxima agendada para {proxima.strftime("%d/%m/%Y")}.', 'success')
    return redirect(url_for('main.equipamento_detalhe', id=id))

@bp.route('/impressao')
@login_required
def impressao():
    equipamentos = Equipamento.query.filter_by(baixado=False).order_by(Equipamento.data_inclusao.desc()).all()
    config = Configuracao.query.first()
    return render_template('impressao.html', equipamentos=equipamentos, config=config, data_impressao=datetime.now())