from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, Response
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from app import db
from app.models.models import Usuario, Equipamento, Observacao, Historico, Configuracao
from app.routes.auth import registrar_historico
import csv
import io
from sqlalchemy import case, asc
from flask import send_from_directory
import os


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
    busca = request.args.get('busca', '').strip().lower()

    query = Equipamento.query

    # Campo de busca único
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

    # === ORDENAÇÃO POR PRIORIDADE DE MANUTENÇÃO ===
    hoje = date.today()
    limite_proximo = hoje + timedelta(days=30)

    prioridade_manutencao = case(
        # 1 = Próxima (dentro de 30 dias, não vencida)
        (db.and_(
            Equipamento.proxima_manutencao.isnot(None),
            Equipamento.proxima_manutencao >= hoje,
            Equipamento.proxima_manutencao <= limite_proximo
        ), 1),
        # 2 = Vencida (passou da data)
        (db.and_(
            Equipamento.proxima_manutencao.isnot(None),
            Equipamento.proxima_manutencao < hoje
        ), 2),
        # 3 = OK (tem data, mas está além de 30 dias)
        (Equipamento.proxima_manutencao.isnot(None), 3),
        # 4 = Sem manutenção agendada
        else_=4
    )

    query = query.order_by(
        Equipamento.baixado.asc(),               # Ativos primeiro
        asc(prioridade_manutencao),              # Próxima → Vencida → OK → Sem
        asc(Equipamento.proxima_manutencao)      # Mesmo grupo: data mais próxima/mais antiga primeiro
    )

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    config = Configuracao.query.first()

    return render_template('equipamentos.html',
        equipamentos=pagination.items,
        pagination=pagination,
        config=config
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

@bp.route('/observacao/<int:id>/excluir', methods=['POST'])
@login_required
def excluir_observacao(id):
    obs = Observacao.query.get_or_404(id)
    equipamento_id = obs.equipamento_id

    # Só admin ou quem criou pode excluir
    if not current_user.is_admin and obs.usuario_id != current_user.id:
        flash('Você não tem permissão para excluir esta observação.', 'danger')
        return redirect(url_for('main.equipamento_detalhe', id=equipamento_id))

    db.session.delete(obs)
    db.session.commit()
    registrar_historico('EXCLUSAO', 'Observacao', id, f'Observação excluída do equipamento {equipamento_id}')
    flash('Observação excluída com sucesso!', 'success')
    return redirect(url_for('main.equipamento_detalhe', id=equipamento_id))

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

@bp.route('/manifest.json')
def manifest():
    return send_from_directory(
        os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static'),
        'manifest.json',
        mimetype='application/json'
    )

@bp.route('/service-worker.js')
def service_worker():
    return send_from_directory(
        os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static'),
        'service-worker.js',
        mimetype='application/javascript'
    )

@bp.route('/offline.html')
def offline():
    config = Configuracao.query.first()
    return render_template('offline.html', config=config)