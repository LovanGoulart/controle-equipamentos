from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app import db
from app.models.models import Equipamento, Observacao, Configuracao
from datetime import datetime, date

bp = Blueprint('api', __name__)

@bp.route('/equipamentos/busca')
@login_required
def busca_equipamentos():
    q = request.args.get('q', '')
    if len(q) < 2:
        return jsonify([])

    busca_like = f'%{q}%'
    equipamentos = Equipamento.query.filter(
        db.or_(
            Equipamento.patrimonio.ilike(busca_like),
            Equipamento.equipamento.ilike(busca_like),
            Equipamento.setor.ilike(busca_like),
            Equipamento.localizacao.ilike(busca_like),
            Equipamento.ip.ilike(busca_like),
        )
    ).limit(10).all()

    return jsonify([{
        'id': e.id,
        'patrimonio': e.patrimonio,
        'equipamento': e.equipamento,
        'setor': e.setor,
        'localizacao': e.localizacao,
        'baixado': e.baixado
    } for e in equipamentos])

@bp.route('/equipamento/<int:id>/dados')
@login_required
def dados_equipamento(id):
    eq = Equipamento.query.get_or_404(id)
    return jsonify({
        'id': eq.id,
        'patrimonio': eq.patrimonio,
        'equipamento': eq.equipamento,
        'tempo_uso': eq.tempo_uso_formatado,
        'status_manutencao': eq.status_manutencao,
        'proxima_manutencao': eq.proxima_manutencao.isoformat() if eq.proxima_manutencao else None,
        'baixado': eq.baixado
    })

@bp.route('/notificacoes/manutencao')
@login_required
def notificacoes_manutencao():
    config = Configuracao.query.first()
    dias_alertas = [int(d) for d in config.dias_lembrete_manutencao.split(',') if d.strip().isdigit()]
    hoje = date.today()

    equipamentos = Equipamento.query.filter_by(baixado=False).all()
    notificacoes = []

    for eq in equipamentos:
        if eq.proxima_manutencao:
            delta = (eq.proxima_manutencao - hoje).days
            if delta < 0:
                notificacoes.append({
                    'id': eq.id,
                    'patrimonio': eq.patrimonio,
                    'equipamento': eq.equipamento,
                    'tipo': 'vencido',
                    'mensagem': f'Manutenção vencida há {abs(delta)} dias',
                    'dias': delta
                })
            elif any(delta <= d for d in dias_alertas):
                notificacoes.append({
                    'id': eq.id,
                    'patrimonio': eq.patrimonio,
                    'equipamento': eq.equipamento,
                    'tipo': 'proximo',
                    'mensagem': f'Manutenção em {delta} dias',
                    'dias': delta
                })

    notificacoes.sort(key=lambda x: x['dias'])
    return jsonify(notificacoes)
