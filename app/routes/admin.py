from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from app import db
from app.models.models import Usuario, Configuracao, Historico
from app.routes.auth import registrar_historico
from datetime import datetime

bp = Blueprint('admin', __name__)

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Acesso restrito a administradores.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/usuarios')
@login_required
@admin_required
def usuarios():
    page = request.args.get('page', 1, type=int)
    usuarios = Usuario.query.order_by(Usuario.nome).paginate(page=page, per_page=25, error_out=False)
    config = Configuracao.query.first()
    return render_template('usuarios.html', usuarios=usuarios, config=config)

@bp.route('/usuario/<int:id>/editar', methods=['GET', 'POST'])
@login_required
@admin_required
def usuario_editar(id):
    user = Usuario.query.get_or_404(id)

    if request.method == 'POST':
        user.nome = request.form.get('nome', '').strip()
        user.email = request.form.get('email', '').strip()
        user.is_admin = request.form.get('is_admin') == 'on'
        user.ativo = request.form.get('ativo') == 'on'

        db.session.commit()
        registrar_historico('EDICAO', 'Usuario', user.id, f'Usuário editado: {user.username}')
        flash('Usuário atualizado!', 'success')
        return redirect(url_for('admin.usuarios'))

    config = Configuracao.query.first()
    return render_template('usuario_form.html', usuario=user, config=config)

@bp.route('/usuario/<int:id>/resetar-senha', methods=['POST'])
@login_required
@admin_required
def usuario_resetar_senha(id):
    user = Usuario.query.get_or_404(id)
    nova_senha = request.form.get('nova_senha', '')

    if len(nova_senha) < 4:
        flash('A senha deve ter pelo menos 4 caracteres.', 'warning')
        return redirect(url_for('admin.usuarios'))

    user.set_password(nova_senha)
    db.session.commit()
    registrar_historico('RESET_SENHA', 'Usuario', user.id, f'Senha resetada: {user.username}')
    flash(f'Senha de {user.nome} resetada com sucesso!', 'success')
    return redirect(url_for('admin.usuarios'))

@bp.route('/usuario/<int:id>/excluir', methods=['POST'])
@login_required
@admin_required
def usuario_excluir(id):
    if id == current_user.id:
        flash('Você não pode excluir seu próprio usuário.', 'danger')
        return redirect(url_for('admin.usuarios'))

    user = Usuario.query.get_or_404(id)
    username = user.username
    db.session.delete(user)
    db.session.commit()
    registrar_historico('EXCLUSAO', 'Usuario', id, f'Usuário excluído: {username}')
    flash('Usuário excluído com sucesso!', 'success')
    return redirect(url_for('admin.usuarios'))

@bp.route('/configuracoes', methods=['GET', 'POST'])
@login_required
@admin_required
def configuracoes():
    config = Configuracao.query.first()

    if request.method == 'POST':
        config.nome_empresa = request.form.get('nome_empresa', 'Controle de Patrimônio')
        config.dias_lembrete_manutencao = request.form.get('dias_lembrete', '30,15,7,1')
        config.tema = request.form.get('tema', 'claro')
        config.data_atualizacao = datetime.now()

        db.session.commit()
        registrar_historico('CONFIGURACAO', 'Configuracao', config.id, 'Configurações atualizadas')
        flash('Configurações salvas com sucesso!', 'success')
        return redirect(url_for('admin.configuracoes'))

    return render_template('configuracoes.html', config=config)
