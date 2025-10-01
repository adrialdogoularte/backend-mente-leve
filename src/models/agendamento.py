from datetime import datetime
from src.extensions import db

class Agendamento(db.Model):
    __tablename__ = 'agendamentos'

    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    psicologo_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    data_agendamento = db.Column(db.Date, nullable=False)
    hora_agendamento = db.Column(db.Time, nullable=False)
    modalidade = db.Column(db.String(50), nullable=False) # 'online' ou 'presencial'
    notas = db.Column(db.Text)
    status = db.Column(db.String(50), default='Pendente') # 'Pendente', 'Confirmado', 'Cancelado'
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_atualizacao = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    aluno = db.relationship('User', foreign_keys=[aluno_id], backref='agendamentos_feitos')
    psicologo = db.relationship('User', foreign_keys=[psicologo_id], backref='agendamentos_recebidos')

    def to_dict(self):
        return {
            'id': self.id,
            'aluno_id': self.aluno_id,
            'psicologo_id': self.psicologo_id,
            'data_agendamento': self.data_agendamento.isoformat() if self.data_agendamento else None,
            'hora_agendamento': self.hora_agendamento.isoformat() if self.hora_agendamento else None,
            'modalidade': self.modalidade,
            'notas': self.notas,
            'status': self.status,
            'data_criacao': self.data_criacao.isoformat() if self.data_criacao else None,
            'data_atualizacao': self.data_atualizacao.isoformat() if self.data_atualizacao else None
        }

    def __repr__(self):
        return f'<Agendamento {self.id} - {self.data_agendamento} {self.hora_agendamento}>'
