from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.humor import db, RegistroHumor
from datetime import datetime

humor_bp = Blueprint("humor", __name__)

@humor_bp.route("/humor", methods=["POST"])
@jwt_required()
def registrar_humor():
    user_id = get_jwt_identity()
    data = request.get_json()

    if not data or not data.get("nivel_humor"):
        return jsonify({"message": "Nível de humor é obrigatório"}), 400

    try:
        novo_registro = RegistroHumor(
            user_id=user_id,
            nivel_humor=data["nivel_humor"],
            descricao=data.get("descricao"),
            emocoes=data.get("emocoes"),
            fatores_influencia=data.get("fatores_influencia"),
            atividades=data.get("atividades"),
            horas_sono=data.get("horas_sono"),
            qualidade_sono=data.get("qualidade_sono"),
            nivel_estresse=data.get("nivel_estresse"),
            data_registro=datetime.strptime(data.get("data_registro"), 
                                            "%Y-%m-%d") if data.get("data_registro") else datetime.now()
        )
        db.session.add(novo_registro)
        db.session.commit()
        return jsonify({"message": "Registro de humor salvo com sucesso!", "registro": novo_registro.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Erro ao salvar registro de humor", "error": str(e)}), 500

@humor_bp.route("/humor", methods=["GET"])
@jwt_required()
def get_registros_humor():
    user_id = get_jwt_identity()
    limite = request.args.get("limite", type=int)

    query = RegistroHumor.query.filter_by(user_id=user_id).order_by(RegistroHumor.data_registro.desc())

    if limite:
        query = query.limit(limite)

    registros = query.all()
    return jsonify({"registros": [registro.to_dict() for registro in registros]}), 200

@humor_bp.route("/humor/estatisticas", methods=["GET"])
@jwt_required()
def get_estatisticas_humor():
    user_id = get_jwt_identity()
    registros = RegistroHumor.query.filter_by(user_id=user_id).all()

    if not registros:
        return jsonify({"total_registros": 0, "media_humor": 0, "emocoes_frequentes": []}), 200

    total_registros = len(registros)
    soma_humor = sum(r.nivel_humor for r in registros)
    media_humor = soma_humor / total_registros

    emocoes_contagem = {}
    for r in registros:
        if r.emocoes:
            for emocao in r.emocoes.split(","): # Assumindo que emoções são string separada por vírgula
                emocao = emocao.strip()
                emocoes_contagem[emocao] = emocoes_contagem.get(emocao, 0) + 1
    
    emocoes_frequentes = sorted(emocoes_contagem.items(), key=lambda item: item[1], reverse=True)

    return jsonify({
        "total_registros": total_registros,
        "media_humor": media_humor,
        "emocoes_frequentes": emocoes_frequentes
    }), 200

