from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.extensions import db
from src.models.agendamento import Agendamento
from src.models.user import User
from datetime import datetime
import uuid

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
    permitir_acesso_avaliacoes = data.get("permitir_acesso_avaliacoes", False)

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

    # Verificar se o psicólogo tem disponibilidade para a data e hora
    dia_semana = data_agendamento.strftime("%A").lower() # Ex: "monday"
    if psicologo.disponibilidade and dia_semana in psicologo.disponibilidade:
        horarios_disponiveis_no_dia = psicologo.disponibilidade[dia_semana]
        if hora_agendamento_str not in horarios_disponiveis_no_dia:
            return jsonify({"message": "Horário selecionado não está disponível na agenda do psicólogo."}), 400
    else:
        return jsonify({"message": "Psicólogo não tem disponibilidade para o dia selecionado."}), 400

    # Verificar se já existe um agendamento para o mesmo psicólogo, data e hora
    agendamento_existente = Agendamento.query.filter_by(
        psicologo_id=psicologo_id,
        data_agendamento=data_agendamento,
        hora_agendamento=hora_agendamento
    ).first()

    if agendamento_existente:
        return jsonify({"message": "Este horário já está agendado. Por favor, escolha outro."}), 409

    link_videoconferencia = None
    if modalidade == 'online':
        # Gerar um link único para a sala Jitsi Meet
        # Usamos um UUID para garantir a unicidade da sala
        room_name = f"MenteLeve-{uuid.uuid4().hex}"
        link_videoconferencia = f"https://meet.jit.si/{room_name}"

    novo_agendamento = Agendamento(
        aluno_id=aluno.id,
        psicologo_id=psicologo.id,
        data_agendamento=data_agendamento,
        hora_agendamento=hora_agendamento,
        modalidade=modalidade,
        notas=notas,
        permitir_acesso_avaliacoes=permitir_acesso_avaliacoes,
        link_videoconferencia=link_videoconferencia
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

    agendamentos_list = []
    for agendamento in agendamentos:
        agendamento_dict = agendamento.to_dict()
        aluno = User.query.get(agendamento.aluno_id)
        psicologo = User.query.get(agendamento.psicologo_id)
        agendamento_dict["aluno_nome"] = aluno.nome if aluno else "Desconhecido"
        agendamento_dict["psicologo_nome"] = psicologo.nome if psicologo else "Desconhecido"
        agendamentos_list.append(agendamento_dict)

    return jsonify(agendamentos_list), 200

@agendamentos_bp.route("/agendamentos/psicologo", methods=["GET"])
@jwt_required()
def get_agendamentos_psicologo():
    """Rota específica para psicólogos visualizarem seus agendamentos"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if not user or user.tipo_usuario != "psicologo":
        return jsonify({"message": "Apenas psicólogos podem acessar esta rota"}), 403

    agendamentos = Agendamento.query.filter_by(psicologo_id=user.id).order_by(
        Agendamento.data_agendamento.desc(), 
        Agendamento.hora_agendamento.desc()
    ).all()

    agendamentos_list = []
    for agendamento in agendamentos:
        agendamento_dict = agendamento.to_dict()
        aluno = User.query.get(agendamento.aluno_id)
        agendamento_dict["aluno_nome"] = aluno.nome if aluno else "Desconhecido"
        agendamento_dict["psicologo_nome"] = user.nome
        agendamentos_list.append(agendamento_dict)

    return jsonify(agendamentos_list), 200

@agendamentos_bp.route("/psicologos", methods=["GET"])
def get_psicologos_api():
    psicologos = User.query.filter_by(tipo_usuario="psicologo", ativo=True).all()
    return jsonify([
        {
            "id": p.id,
            "name": p.nome,
            "specialty": p.especialidades[0] if p.especialidades else "Geral", # Assumindo que especialidades é uma lista
            "availability": p.disponibilidade if p.disponibilidade else {},
            "description": "", # Será preenchido no frontend ou por outra lógica
            "modes": p.modalidades_atendimento if p.modalidades_atendimento else []
        }
        for p in psicologos
    ]), 200