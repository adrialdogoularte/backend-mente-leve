from src.models.user import db
from datetime import datetime
import json

class Avaliacao(db.Model):
    __tablename__ = 'avaliacoes'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Dados da avaliação
    respostas = db.Column(db.Text, nullable=False)  # JSON das respostas
    pontuacao_total = db.Column(db.Integer, nullable=False)
    nivel_risco = db.Column(db.String(20), nullable=False)  # 'baixo', 'medio', 'alto'
    
    # Pontuações por categoria
    categorias_pontuacao = db.Column(db.Text)  # JSON das pontuações por categoria
    
    # Recomendações geradas
    recomendacoes = db.Column(db.Text)  # JSON das recomendações
    
    # Campos de controle
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    compartilhada = db.Column(db.Boolean, default=False)
    
    # Relacionamentos
    compartilhamentos = db.relationship('Compartilhamento', backref='avaliacao', lazy=True, cascade='all, delete-orphan')
    
    def set_respostas(self, respostas_dict):
        """Define as respostas da avaliação"""
        self.respostas = json.dumps(respostas_dict)
    
    def get_respostas(self):
        """Obtém as respostas da avaliação"""
        return json.loads(self.respostas) if self.respostas else {}
    
    def set_categorias_pontuacao(self, categorias_dict):
        """Define as pontuações por categoria"""
        self.categorias_pontuacao = json.dumps(categorias_dict)
    
    def get_categorias_pontuacao(self):
        """Obtém as pontuações por categoria"""
        return json.loads(self.categorias_pontuacao) if self.categorias_pontuacao else {}
    
    def set_recomendacoes(self, recomendacoes_list):
        """Define as recomendações"""
        self.recomendacoes = json.dumps(recomendacoes_list)
    
    def get_recomendacoes(self):
        """Obtém as recomendações"""
        return json.loads(self.recomendacoes) if self.recomendacoes else []
    
    def calcular_pontuacao_e_risco(self, respostas):
        """Calcula a pontuação total e o nível de risco"""
        # Categorias das perguntas
        categorias = {
            1: 'estresse_academico',
            2: 'sono_descanso', 
            3: 'relacionamentos',
            4: 'humor_emocoes',
            5: 'ansiedade',
            6: 'autocuidado',
            7: 'concentracao',
            8: 'bem_estar_geral'
        }
        
        # Calcular pontuação total
        pontuacao_total = sum(respostas.values())
        
        # Calcular pontuação por categoria
        categorias_pontuacao = {}
        for pergunta_id, resposta in respostas.items():
            categoria = categorias.get(int(pergunta_id))
            if categoria:
                categorias_pontuacao[categoria] = resposta
        
        # Determinar nível de risco
        if pontuacao_total <= 16:
            nivel_risco = 'baixo'
        elif pontuacao_total <= 28:
            nivel_risco = 'medio'
        else:
            nivel_risco = 'alto'
        
        # Gerar recomendações
        recomendacoes = self._gerar_recomendacoes(nivel_risco, categorias_pontuacao)
        
        # Definir valores
        self.pontuacao_total = pontuacao_total
        self.nivel_risco = nivel_risco
        self.set_categorias_pontuacao(categorias_pontuacao)
        self.set_recomendacoes(recomendacoes)
    
    def _gerar_recomendacoes(self, nivel_risco, categorias_pontuacao):
        """Gera recomendações baseadas no nível de risco e pontuações"""
        recomendacoes = []
        
        if nivel_risco == 'baixo':
            recomendacoes.append("Continue mantendo seus bons hábitos de bem-estar mental.")
            recomendacoes.append("Pratique atividades que te dão prazer regularmente.")
            recomendacoes.append("Mantenha uma rotina de sono saudável.")
        elif nivel_risco == 'medio':
            recomendacoes.append("Considere implementar técnicas de relaxamento em sua rotina.")
            recomendacoes.append("Busque apoio de amigos, família ou profissionais quando necessário.")
            recomendacoes.append("Avalie sua carga de trabalho e organize melhor seu tempo.")
        else:  # alto
            recomendacoes.append("É recomendável buscar apoio profissional de um psicólogo.")
            recomendacoes.append("Considere conversar com alguém de confiança sobre como se sente.")
            recomendacoes.append("Pratique técnicas de respiração e mindfulness.")
            recomendacoes.append("Não hesite em procurar ajuda imediata se necessário.")
        
        # Recomendações específicas por categoria
        for categoria, pontuacao in categorias_pontuacao.items():
            if pontuacao >= 4:
                if categoria == 'estresse_academico':
                    recomendacoes.append("Organize melhor seus estudos e estabeleça prioridades.")
                elif categoria == 'sono_descanso':
                    recomendacoes.append("Melhore sua higiene do sono e estabeleça horários regulares.")
                elif categoria == 'ansiedade':
                    recomendacoes.append("Pratique técnicas de respiração e relaxamento.")
                elif categoria == 'autocuidado':
                    recomendacoes.append("Dedique mais tempo para atividades de autocuidado.")
        
        return recomendacoes
    
    def to_dict(self):
        """Converte a avaliação para dicionário"""
        return {
            'id': self.id,
            'usuario_id': self.usuario_id,
            'respostas': self.get_respostas(),
            'pontuacao_total': self.pontuacao_total,
            'nivel_risco': self.nivel_risco,
            'categorias_pontuacao': self.get_categorias_pontuacao(),
            'recomendacoes': self.get_recomendacoes(),
            'data_criacao': self.data_criacao.isoformat() if self.data_criacao else None,
            'compartilhada': self.compartilhada
        }
    
    def __repr__(self):
        return f'<Avaliacao {self.id} - {self.nivel_risco}>'

