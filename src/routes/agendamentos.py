from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.extensions import db
from src.models.agendamento import Agendamento
from src.models.user import User
from datetime import datetime

agendamentos_bp = Blueprint("agendamentos", __name__)

@agendamentos_bp.route("/agendamentos", methods=["POST"])
@jwt_required()
def create_agendamento():
    current_user_id = get_jwt_identity()
    aluno = User.query.get(current_user_id)

    if not aluno or aluno.tipo_usuario != "aluno":
        return jsonify({"message": "Apenas alunos podem criar agendamentos"}), 403

    data = request.get_json()
    psicologo_id = data.get("psicologo_id")
    data_agendamento_str = data.get("data_agendamento")
    hora_agendamento_str = data.get("hora_agendamento")
    modalidade = data.get("modalidade")
    notas = data.get("notas")

    if not all([psicologo_id, data_agendamento_str, hora_agendamento_str, modalidade]):
        return jsonify({"message": "Dados de agendamento incompletos"}), 400

    psicologo = User.query.get(psicologo_id)
    if not psicologo or psicologo.tipo_usuario != "psicologo":
        return jsonify({"message": "Psicólogo não encontrado ou inválido"}), 404
    
    if modalidade not in psicologo.modalidades_atendimento:
        return jsonify({"message": f"Psicólogo não oferece atendimento na modalidade {modalidade}"}), 400

    try:
        data_agendamento = datetime.strptime(data_agendamento_str, "%Y-%m-%d").date()
        hora_agendamento = datetime.strptime(hora_agendamento_str, "%H:%M").time()
    except ValueError:
        return jsonify({"message": "Formato de data ou hora inválido. Use YYYY-MM-DD e HH:MM"}), 400

    novo_agendamento = Agendamento(
        aluno_id=aluno.id,
        psicologo_id=psicologo.id,
        data_agendamento=data_agendamento,
        hora_agendamento=hora_agendamento,
        modalidade=modalidade,
        notas=notas
    )

    db.session.add(novo_agendamento)
    db.session.commit()

    return jsonify({"message": "Agendamento criado com sucesso", "agendamento": novo_agendamento.to_dict()}), 201

@agendamentos_bp.route("/agendamentos/meus", methods=["GET"])
@jwt_required()
def get_my_agendamentos():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if not user:
        return jsonify({"message": "Usuário não encontrado"}), 404

    if user.tipo_usuario == "aluno":
        agendamentos = Agendamento.query.filter_by(aluno_id=user.id).order_by(Agendamento.data_agendamento.desc(), Agendamento.hora_agendamento.desc()).all()
    elif user.tipo_usuario == "psicologo":
        agendamentos = Agendamento.query.filter_by(psicologo_id=user.id).order_by(Agendamento.data_agendamento.desc(), Agendamento.hora_agendamento.desc()).all()
    else:
        return jsonify({"message": "Tipo de usuário inválido para agendamentos"}), 403

    return jsonify([agendamento.to_dict() for agendamento in agendamentos]), 200

@agendamentos_bp.route("/psicologos", methods=["GET"])
def get_psicologos():
    psicologos = User.query.filter_by(tipo_usuario="psicologo", ativo=True).all()
    return jsonify([
        {
            "id": p.id,
            "name": p.nome,
            "specialty": p.especialidades[0] if p.especialidades else "Geral", # Assumindo que especialidades é uma lista
            "availability": "", # Será preenchido no frontend ou por outra lógica
            "description": "", # Será preenchido no frontend ou por outra lógica
            "modes": p.modalidades_atendimento if p.modalidades_atendimento else []
        }
        for p in psicologos
    ]), 200

