from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.user import db, User
from src.models.avaliacao import Avaliacao
import json

avaliacoes_bp = Blueprint("avaliacoes", __name__)

@avaliacoes_bp.route("/avaliacoes", methods=["POST"])
@jwt_required()
def criar_avaliacao():
    user_id = get_jwt_identity()
    data = request.get_json()

    if not data:
        return jsonify({"message": "Dados da avaliação são obrigatórios"}), 400

    try:
        # Certifique-se de que as respostas e recomendações são strings JSON
        respostas_json = json.dumps(data.get("respostas", {}))
        recomendacoes_json = json.dumps(data.get("recomendacoes", {}))

        nova_avaliacao = Avaliacao(
            usuario_id=user_id,
            pontuacao_total=data.get("pontuacao_total"),
            nivel_risco=data.get("nivel_risco"),
            respostas=respostas_json,
            recomendacoes=recomendacoes_json
        )
        db.session.add(nova_avaliacao)
        db.session.commit()
        return jsonify({"message": "Avaliação salva com sucesso!", "avaliacao": nova_avaliacao.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Erro ao salvar avaliação", "error": str(e)}), 500

@avaliacoes_bp.route("/avaliacoes", methods=["GET"])
@jwt_required()
def get_avaliacoes():
    user_id = get_jwt_identity()
    avaliacoes = Avaliacao.query.filter_by(usuario_id=user_id).order_by(Avaliacao.data_criacao.desc()).all()
    return jsonify({"avaliacoes": [avaliacao.to_dict() for avaliacao in avaliacoes]}), 200