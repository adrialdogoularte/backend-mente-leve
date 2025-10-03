from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.extensions import db
from src.models.agendamento import Agendamento
from src.models.user import User
from src.models.avaliacao import Avaliacao

avaliacoes_agendamento_bp = Blueprint("avaliacoes_agendamento", __name__)

@avaliacoes_agendamento_bp.route("/agendamentos/<int:agendamento_id>/avaliacoes", methods=["GET"])
@jwt_required()
def get_avaliacoes_por_agendamento(agendamento_id):
    """
    Busca as avaliações de um aluno para um agendamento específico,
    apenas se o psicólogo tiver permissão para acessá-las.
    """
    current_user_id = get_jwt_identity()
    user = User.query.get(int(current_user_id))

    if not user or user.tipo_usuario != "psicologo":
        return jsonify({"message": "Apenas psicólogos podem acessar esta rota"}), 403

    # Buscar o agendamento
    agendamento = Agendamento.query.get(agendamento_id)
    if not agendamento:
        return jsonify({"message": "Agendamento não encontrado"}), 404

    # Verificar se o psicólogo é o responsável pelo agendamento
    if agendamento.psicologo_id != int(current_user_id):
        return jsonify({"message": "Você não tem permissão para acessar este agendamento"}), 403

    # Verificar se o aluno permitiu o acesso às avaliações
    if not agendamento.permitir_acesso_avaliacoes:
        return jsonify({"message": "O aluno não permitiu o acesso às suas autoavaliações para esta consulta"}), 403

    # Buscar as autoavaliações do aluno
    avaliacoes = Avaliacao.query.filter_by(usuario_id=agendamento.aluno_id).order_by(Avaliacao.data_criacao.desc()).all()
    
    avaliacoes_list = []
    for avaliacao in avaliacoes:
        avaliacao_dict = avaliacao.to_dict()
        avaliacoes_list.append(avaliacao_dict)

    return jsonify({
        "agendamento_id": agendamento_id,
        "aluno_nome": agendamento.aluno.nome if agendamento.aluno else "Desconhecido",
        "avaliacoes": avaliacoes_list
    }), 200