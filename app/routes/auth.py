from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from app import db, login_manager
from app.models.models import Usuario, Historico
from datetime import datetime

bp = Blueprint('auth', __name__)

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

def registrar_historico(acao, entidade, entidade_id=None, descricao=None):
    hist = Historico(
        usuario_id=current_user.id if current_user.is_authenticated else None,
        usuario_nome=current_user.nome if current_user.is_authenticated else 'Sistema',
        acao=acao,
        entidade=entidade,
        entidade_id=entidade_id,
        descricao=descricao,
        ip=request.remote_addr,
        data=datetime.now()
    )
    db.session.add(hist)
    db.session.commit()

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = Usuario.query.filter_by(username=username).first()

        if user and user.check_password(password) and user.ativo:
            login_user(user, remember=True)
            registrar_historico('LOGIN', 'Usuario', user.id, f'Login realizado: {user.username}')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.dashboard'))
        else:
            flash('Usuário ou senha inválidos.', 'danger')

    return render_template('login.html')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated and not current_user.is_admin:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm', '')
        is_admin = request.form.get('is_admin') == 'on'

        if not nome or not username or not email or not password:
            flash('Todos os campos são obrigatórios.', 'warning')
            return render_template('register.html')

        if password != confirm:
            flash('As senhas não conferem.', 'warning')
            return render_template('register.html')

        if Usuario.query.filter_by(username=username).first():
            flash('Nome de usuário já existe.', 'warning')
            return render_template('register.html')

        if Usuario.query.filter_by(email=email).first():
            flash('E-mail já cadastrado.', 'warning')
            return render_template('register.html')

        user = Usuario(
            nome=nome,
            username=username,
            email=email,
            is_admin=is_admin,
            ativo=True
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        registrar_historico('CADASTRO', 'Usuario', user.id, f'Usuário cadastrado: {user.username}')
        flash('Usuário cadastrado com sucesso!', 'success')

        if current_user.is_authenticated:
            return redirect(url_for('admin.usuarios'))
        return redirect(url_for('auth.login'))

    return render_template('register.html')

@bp.route('/logout')
@login_required
def logout():
    registrar_historico('LOGOUT', 'Usuario', current_user.id, f'Logout: {current_user.username}')
    logout_user()
    flash('Você saiu do sistema.', 'info')
    return redirect(url_for('auth.login'))
