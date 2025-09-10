from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.user import db, User

user_bp = Blueprint('user', __name__)

@user_bp.route('/perfil', methods=['GET'])
@jwt_required()
def obter_perfil():
    """Obtém o perfil do usuário atual"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(int(current_user_id))  # Converter para int
        
        if not user:
            return jsonify({'message': 'Usuário não encontrado'}), 404
        
        return jsonify({'user': user.to_dict()}), 200
        
    except Exception as e:
        return jsonify({'message': f'Erro interno: {str(e)}'}), 500

@user_bp.route('/perfil', methods=['PUT'])
@jwt_required()
def atualizar_perfil():
    """Atualiza o perfil do usuário atual"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(int(current_user_id))  # Converter para int
        
        if not user:
            return jsonify({'message': 'Usuário não encontrado'}), 404
        
        data = request.get_json()
        
        # Atualizar campos permitidos
        if 'nome' in data:
            user.nome = data['nome']
        
        if 'email' in data:
            # Verificar se o email já está em uso por outro usuário
            existing_user = User.query.filter_by(email=data['email']).first()
            if existing_user and existing_user.id != user.id:
                return jsonify({'message': 'Email já está em uso'}), 400
            user.email = data['email']
        
        # Campos específicos para alunos
        if user.tipo_usuario == 'aluno':
            if 'universidade' in data:
                user.universidade = data['universidade']
            if 'curso' in data:
                user.curso = data['curso']
            if 'periodo' in data:
                user.periodo = data['periodo']
        
        # Campos específicos para psicólogos
        if user.tipo_usuario == 'psicologo':
            if 'crp' in data:
                user.crp = data['crp']
            
            # Tratar especialidades - aceitar tanto 'especialidade' quanto 'especialidades'
            if 'especialidade' in data:
                # Se vier como string, converter para lista
                especialidade_input = data['especialidade']
                if isinstance(especialidade_input, str):
                    # Se for string separada por vírgulas, dividir em lista
                    if ',' in especialidade_input:
                        user.especialidades = [esp.strip() for esp in especialidade_input.split(',') if esp.strip()]
                    else:
                        # Se for uma única especialidade, criar lista com um item
                        user.especialidades = [especialidade_input.strip()] if especialidade_input.strip() else []
                elif isinstance(especialidade_input, list):
                    # Se já for lista, usar diretamente
                    user.especialidades = especialidade_input
                else:
                    user.especialidades = []
            
            if 'especialidades' in data:
                # Se vier como lista diretamente
                if isinstance(data['especialidades'], list):
                    user.especialidades = data['especialidades']
                elif isinstance(data['especialidades'], str):
                    # Se vier como string, dividir por vírgulas
                    if ',' in data['especialidades']:
                        user.especialidades = [esp.strip() for esp in data['especialidades'].split(',') if esp.strip()]
                    else:
                        user.especialidades = [data['especialidades'].strip()] if data['especialidades'].strip() else []
                else:
                    user.especialidades = []
        
        db.session.commit()
        
        return jsonify({
            'message': 'Perfil atualizado com sucesso',
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Erro interno: {str(e)}'}), 500

@user_bp.route('/users', methods=['GET'])
def get_users():
    users = User.query.all()
    return jsonify([user.to_dict() for user in users])

@user_bp.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict())
