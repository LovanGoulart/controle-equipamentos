from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
from app import db

class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    ativo = db.Column(db.Boolean, default=True)
    data_criacao = db.Column(db.DateTime, default=datetime.now)

    equipamentos = db.relationship('Equipamento', backref='usuario_cadastro', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<Usuario {self.username}>'

class Equipamento(db.Model):
    __tablename__ = 'equipamentos'

    id = db.Column(db.Integer, primary_key=True)
    patrimonio = db.Column(db.String(50))
    data_inclusao = db.Column(db.Date, default=date.today)
    baixado = db.Column(db.Boolean, default=False)
    data_baixa = db.Column(db.Date, nullable=True)

    equipamento = db.Column(db.String(100))
    area_patrimonial = db.Column(db.String(100))
    setor = db.Column(db.String(100))
    localizacao = db.Column(db.String(100))
    especificacao = db.Column(db.Text)

    ultima_manutencao = db.Column(db.Date, nullable=True)
    proxima_manutencao = db.Column(db.Date, nullable=True)

    sistema_operacional = db.Column(db.String(100))
    placa_mae = db.Column(db.String(100))
    processador = db.Column(db.String(100))
    memoria_ram = db.Column(db.String(50))
    armazenamento = db.Column(db.String(100))
    ip = db.Column(db.String(50))

    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    data_criacao = db.Column(db.DateTime, default=datetime.now)
    data_atualizacao = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    observacoes = db.relationship('Observacao', backref='equipamento', lazy=True, cascade='all, delete-orphan')

    @property
    def tempo_uso(self):
        if self.baixado and self.data_baixa:
            end_date = self.data_baixa
        else:
            end_date = date.today()

        if not self.data_inclusao:
            return {'anos': 0, 'meses': 0, 'dias': 0}

        delta = end_date - self.data_inclusao
        anos = delta.days // 365
        meses = (delta.days % 365) // 30
        dias = (delta.days % 365) % 30

        return {'anos': anos, 'meses': meses, 'dias': dias, 'total_dias': delta.days}

    @property
    def tempo_uso_formatado(self):
        t = self.tempo_uso
        partes = []
        if t['anos'] > 0:
            partes.append(f"{t['anos']} ano{'s' if t['anos'] > 1 else ''}")
        if t['meses'] > 0:
            partes.append(f"{t['meses']} mes{'es' if t['meses'] > 1 else ''}")
        if t['dias'] > 0:
            partes.append(f"{t['dias']} dia{'s' if t['dias'] > 1 else ''}")
        return ', '.join(partes) if partes else '0 dias'

    @property
    def status_manutencao(self):
        if not self.proxima_manutencao:
            return 'sem_manutencao'

        hoje = date.today()
        delta = (self.proxima_manutencao - hoje).days

        if delta < 0:
            return 'vencido'
        elif delta <= 30:
            return 'proximo'
        else:
            return 'ok'

    def __repr__(self):
        return f'<Equipamento {self.patrimonio}>'

class Observacao(db.Model):
    __tablename__ = 'observacoes'

    id = db.Column(db.Integer, primary_key=True)
    equipamento_id = db.Column(db.Integer, db.ForeignKey('equipamentos.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    texto = db.Column(db.Text, nullable=False)
    data = db.Column(db.DateTime, default=datetime.now)

    usuario = db.relationship('Usuario')

class Historico(db.Model):
    __tablename__ = 'historico'

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    usuario_nome = db.Column(db.String(100))
    acao = db.Column(db.String(50), nullable=False)
    entidade = db.Column(db.String(50), nullable=False)
    entidade_id = db.Column(db.Integer)
    descricao = db.Column(db.Text)
    data = db.Column(db.DateTime, default=datetime.now)
    ip = db.Column(db.String(50))

class Configuracao(db.Model):
    __tablename__ = 'configuracoes'

    id = db.Column(db.Integer, primary_key=True)
    nome_empresa = db.Column(db.String(200), default='Controle de Patrimônio')
    logo = db.Column(db.String(200), nullable=True)
    dias_lembrete_manutencao = db.Column(db.String(50), default='30,15,7,1')
    tema = db.Column(db.String(20), default='claro')
    data_atualizacao = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
