from src.models.user import db
from datetime import datetime
import json

class RegistroHumor(db.Model):
    __tablename__ = 'registros_humor'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Dados do humor
    nivel_humor = db.Column(db.Integer, nullable=False)  # 1-5 (muito ruim a muito bom)
    emocoes = db.Column(db.Text)  # JSON array das emoções selecionadas
    descricao = db.Column(db.Text)  # Descrição opcional do usuário
    
    # Fatores que influenciaram o humor
    fatores_influencia = db.Column(db.Text)  # JSON array dos fatores
    
    # Atividades realizadas
    atividades = db.Column(db.Text)  # JSON array das atividades
    
    # Qualidade do sono (opcional)
    horas_sono = db.Column(db.Float)
    qualidade_sono = db.Column(db.Integer)  # 1-5
    
    # Nível de estresse (opcional)
    nivel_estresse = db.Column(db.Integer)  # 1-5
    
    # Campos de controle
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_registro = db.Column(db.Date, nullable=False)  # Data do dia que está sendo registrado
    
    # Relacionamento com usuário
    usuario = db.relationship('User', backref=db.backref('registros_humor', lazy=True))
    
    def set_emocoes(self, emocoes_list):
        """Define as emoções do registro"""
        self.emocoes = json.dumps(emocoes_list) if emocoes_list else None
    
    def get_emocoes(self):
        """Obtém as emoções do registro"""
        return json.loads(self.emocoes) if self.emocoes else []
    
    def set_fatores_influencia(self, fatores_list):
        """Define os fatores de influência"""
        self.fatores_influencia = json.dumps(fatores_list) if fatores_list else None
    
    def get_fatores_influencia(self):
        """Obtém os fatores de influência"""
        return json.loads(self.fatores_influencia) if self.fatores_influencia else []
    
    def set_atividades(self, atividades_list):
        """Define as atividades realizadas"""
        self.atividades = json.dumps(atividades_list) if atividades_list else None
    
    def get_atividades(self):
        """Obtém as atividades realizadas"""
        return json.loads(self.atividades) if self.atividades else []
    
    def to_dict(self):
        """Converte o registro para dicionário"""
        return {
            'id': self.id,
            'usuario_id': self.usuario_id,
            'nivel_humor': self.nivel_humor,
            'emocoes': self.get_emocoes(),
            'descricao': self.descricao,
            'fatores_influencia': self.get_fatores_influencia(),
            'atividades': self.get_atividades(),
            'horas_sono': self.horas_sono,
            'qualidade_sono': self.qualidade_sono,
            'nivel_estresse': self.nivel_estresse,
            'data_criacao': self.data_criacao.isoformat() if self.data_criacao else None,
            'data_registro': self.data_registro.isoformat() if self.data_registro else None
        }
    
    def __repr__(self):
        return f'<RegistroHumor {self.id} - {self.data_registro}>'

