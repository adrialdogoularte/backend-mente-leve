from src.models.user import db
from datetime import datetime

class Compartilhamento(db.Model):
    __tablename__ = 'compartilhamentos'
    
    id = db.Column(db.Integer, primary_key=True)
    avaliacao_id = db.Column(db.Integer, db.ForeignKey('avaliacoes.id'), nullable=False)
    aluno_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    psicologo_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Campos de controle
    data_compartilhamento = db.Column(db.DateTime, default=datetime.utcnow)
    visualizado = db.Column(db.Boolean, default=False)
    data_visualizacao = db.Column(db.DateTime)
    
    # Observações do psicólogo
    observacoes = db.Column(db.Text)
    
    def marcar_como_visualizado(self):
        """Marca o compartilhamento como visualizado"""
        self.visualizado = True
        self.data_visualizacao = datetime.utcnow()
    
    def to_dict(self):
        """Converte o compartilhamento para dicionário"""
        return {
            'id': self.id,
            'avaliacao_id': self.avaliacao_id,
            'aluno_id': self.aluno_id,
            'psicologo_id': self.psicologo_id,
            'data_compartilhamento': self.data_compartilhamento.isoformat() if self.data_compartilhamento else None,
            'visualizado': self.visualizado,
            'data_visualizacao': self.data_visualizacao.isoformat() if self.data_visualizacao else None,
            'observacoes': self.observacoes
        }
    
    def __repr__(self):
        return f'<Compartilhamento {self.id}>'

