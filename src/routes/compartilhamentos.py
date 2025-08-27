from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.user import db, User
from src.models.avaliacao import Avaliacao
from src.models.compartilhamento import Compartilhamento

compartilhamentos_bp = Blueprint('compartilhamentos', __name__)

@compartilhamentos_bp.route('', methods=['POST'])
@jwt_required()
def compartilhar_avaliacao():
    """Compartilha uma avaliação com um psicólogo"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or user.tipo_usuario != 'aluno':
            return jsonify({'message': 'Apenas alunos podem compartilhar avaliações'}), 403
        
        data = request.get_json()
        
        if not data.get('avaliacao_id') or not data.get('psicologo_id'):
            return jsonify({'message': 'ID da avaliação e do psicólogo são obrigatórios'}), 400
        
        # Verificar se a avaliação existe e pertence ao usuário
        avaliacao = Avaliacao.query.filter_by(
            id=data['avaliacao_id'], 
            usuario_id=current_user_id
        ).first()
        
        if not avaliacao:
            return jsonify({'message': 'Avaliação não encontrada'}), 404
        
        # Verificar se o psicólogo existe
        psicologo = User.query.filter_by(
            id=data['psicologo_id'], 
            tipo_usuario='psicologo'
        ).first()
        
        if not psicologo:
            return jsonify({'message': 'Psicólogo não encontrado'}), 404
        
        # Verificar se já não foi compartilhado
        compartilhamento_existente = Compartilhamento.query.filter_by(
            avaliacao_id=data['avaliacao_id'],
            psicologo_id=data['psicologo_id']
        ).first()
        
        if compartilhamento_existente:
            return jsonify({'message': 'Avaliação já foi compartilhada com este psicólogo'}), 400
        
        # Criar compartilhamento
        compartilhamento = Compartilhamento(
            avaliacao_id=data['avaliacao_id'],
            aluno_id=current_user_id,
            psicologo_id=data['psicologo_id']
        )
        
        # Marcar avaliação como compartilhada
        avaliacao.compartilhada = True
        
        db.session.add(compartilhamento)
        db.session.commit()
        
        return jsonify({
            'message': 'Avaliação compartilhada com sucesso',
            'compartilhamento': compartilhamento.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Erro interno: {str(e)}'}), 500

@compartilhamentos_bp.route('/enviados', methods=['GET'])
@jwt_required()
def listar_compartilhamentos_enviados():
    """Lista compartilhamentos enviados pelo aluno"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or user.tipo_usuario != 'aluno':
            return jsonify({'message': 'Apenas alunos podem ver compartilhamentos enviados'}), 403
        
        compartilhamentos = Compartilhamento.query.filter_by(aluno_id=current_user_id).all()
        
        resultado = []
        for comp in compartilhamentos:
            comp_dict = comp.to_dict()
            # Adicionar informações do psicólogo
            psicologo = User.query.get(comp.psicologo_id)
            comp_dict['psicologo'] = psicologo.to_dict() if psicologo else None
            # Adicionar informações da avaliação
            avaliacao = Avaliacao.query.get(comp.avaliacao_id)
            comp_dict['avaliacao'] = avaliacao.to_dict() if avaliacao else None
            resultado.append(comp_dict)
        
        return jsonify({'compartilhamentos': resultado}), 200
        
    except Exception as e:
        return jsonify({'message': f'Erro interno: {str(e)}'}), 500

@compartilhamentos_bp.route('/recebidos', methods=['GET'])
@jwt_required()
def listar_compartilhamentos_recebidos():
    """Lista compartilhamentos recebidos pelo psicólogo"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or user.tipo_usuario != 'psicologo':
            return jsonify({'message': 'Apenas psicólogos podem ver compartilhamentos recebidos'}), 403
        
        compartilhamentos = Compartilhamento.query.filter_by(psicologo_id=current_user_id).all()
        
        resultado = []
        for comp in compartilhamentos:
            comp_dict = comp.to_dict()
            # Adicionar informações do aluno
            aluno = User.query.get(comp.aluno_id)
            comp_dict['aluno'] = aluno.to_dict() if aluno else None
            # Adicionar informações da avaliação
            avaliacao = Avaliacao.query.get(comp.avaliacao_id)
            comp_dict['avaliacao'] = avaliacao.to_dict() if avaliacao else None
            resultado.append(comp_dict)
        
        return jsonify({'compartilhamentos': resultado}), 200
        
    except Exception as e:
        return jsonify({'message': f'Erro interno: {str(e)}'}), 500

@compartilhamentos_bp.route('/<int:compartilhamento_id>/visualizar', methods=['POST'])
@jwt_required()
def marcar_como_visualizado(compartilhamento_id):
    """Marca um compartilhamento como visualizado"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or user.tipo_usuario != 'psicologo':
            return jsonify({'message': 'Apenas psicólogos podem marcar como visualizado'}), 403
        
        compartilhamento = Compartilhamento.query.filter_by(
            id=compartilhamento_id,
            psicologo_id=current_user_id
        ).first()
        
        if not compartilhamento:
            return jsonify({'message': 'Compartilhamento não encontrado'}), 404
        
        compartilhamento.marcar_como_visualizado()
        db.session.commit()
        
        return jsonify({
            'message': 'Compartilhamento marcado como visualizado',
            'compartilhamento': compartilhamento.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Erro interno: {str(e)}'}), 500

@compartilhamentos_bp.route('/psicologos', methods=['GET'])
@jwt_required()
def listar_psicologos():
    """Lista todos os psicólogos disponíveis para compartilhamento"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or user.tipo_usuario != 'aluno':
            return jsonify({'message': 'Apenas alunos podem ver lista de psicólogos'}), 403
        
        psicologos = User.query.filter_by(tipo_usuario='psicologo', ativo=True).all()
        
        return jsonify({
            'psicologos': [psicologo.to_dict() for psicologo in psicologos]
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Erro interno: {str(e)}'}), 500

