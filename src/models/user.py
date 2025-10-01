from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from src.extensions import db

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha_hash = db.Column(db.String(255), nullable=False)
    tipo_usuario = db.Column(db.String(20), nullable=False)  # 'aluno' ou 'psicologo'
    
    # Campos específicos para alunos
    universidade = db.Column(db.String(200))
    curso = db.Column(db.String(100))
    periodo = db.Column(db.String(20))
    
    # Campos específicos para psicólogos
    crp = db.Column(db.String(20))
    especialidades = db.Column(db.JSON)
    modalidades_atendimento = db.Column(db.JSON) # Ex: ["online", "presencial"]
    disponibilidade = db.Column(db.JSON) # Ex: {"segunda": ["09:00", "10:00"], "terca": ["14:00"]}
    
    # Campos de controle
    ativo = db.Column(db.Boolean, default=True)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_atualizacao = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def set_password(self, password):
        """Define a senha do usuário"""
        self.senha_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verifica se a senha está correta"""
        return check_password_hash(self.senha_hash, password)
    
    def to_dict(self):
        """Converte o usuário para dicionário"""
        return {
            'id': self.id,
            'nome': self.nome,
            'email': self.email,
            'tipo_usuario': self.tipo_usuario,
            'universidade': self.universidade,
            'curso': self.curso,
            'periodo': self.periodo,
            'crp': self.crp,
            'especialidades': self.especialidades,
            'modalidades_atendimento': self.modalidades_atendimento,
            'disponibilidade': self.disponibilidade,
            'ativo': self.ativo,
            'data_criacao': self.data_criacao.isoformat() if self.data_criacao else None,
            'data_atualizacao': self.data_atualizacao.isoformat() if self.data_atualizacao else None
        }
    
    def __repr__(self):
        return f'<User {self.email}>'
