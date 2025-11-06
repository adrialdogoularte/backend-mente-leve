from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.extensions import db
from src.models.agendamento import Agendamento
from src.models.user import User
from datetime import datetime, timedelta, date, time
import uuid

agendamentos_bp = Blueprint("agendamentos", __name__)

def get_available_times_for_psicologo(psicologo_id, disponibilidade):
    """
    Filtra os horários de disponibilidade de um psicólogo, removendo aqueles que já estão agendados.
    A disponibilidade retornada é um dicionário onde a chave é o dia da semana (ex: 'monday')
    e o valor é um dicionário de datas (ISO format) e seus horários disponíveis.
    """
    
    # 1. Obter todos os agendamentos futuros confirmados ou pendentes para este psicólogo
    # Consideramos 'Pendente' e 'Confirmado' como horários ocupados.
    # Agendamentos 'Cancelado' ou 'Finalizado' não ocupam o horário.
    agendamentos_ocupados = Agendamento.query.filter(
        Agendamento.psicologo_id == psicologo_id,
        Agendamento.status.in_(['Pendente', 'Confirmado']),
        Agendamento.data_agendamento >= date.today() # Apenas agendamentos futuros ou de hoje
    ).all()

    # 2. Criar um conjunto de (data, hora) dos agendamentos ocupados para consulta rápida
    horarios_ocupados = set()
    for agendamento in agendamentos_ocupados:
        # Converte a hora para o formato de string "HH:MM" que está na disponibilidade
        hora_str = agendamento.hora_agendamento.strftime("%H:%M")
        horarios_ocupados.add((agendamento.data_agendamento, hora_str))

    # 3. Filtrar a disponibilidade
    disponibilidade_filtrada = {}
    
    # Mapeamento de dia da semana (string em inglês) para o weekday() (0=Segunda, 6=Domingo)
    dias_semana_map_weekday = {
        'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3, 
        'friday': 4, 'saturday': 5, 'sunday': 6
    }
    
    for dia_semana, horarios_do_dia in disponibilidade.items():
        try:
            target_weekday = dias_semana_map_weekday[dia_semana]
        except KeyError:
            continue

        hoje = date.today()
        horarios_disponiveis_por_data = {}
        
        # Vamos procurar por datas futuras (ex: 30 dias à frente)
        for i in range(30): # Limitar a 30 dias para evitar processamento excessivo
            data_futura = hoje + timedelta(days=i)
            
            # O weekday() retorna 0 para Segunda, 6 para Domingo
            if data_futura.weekday() == target_weekday:
                
                horarios_disponiveis_na_data = []
                for hora_str in horarios_do_dia:
                    # Verificar se o horário já está ocupado
                    if (data_futura, hora_str) not in horarios_ocupados:
                        horarios_disponiveis_na_data.append(hora_str)
                
                if horarios_disponiveis_na_data:
                    # Adicionar a lista de horários disponíveis para esta data
                    horarios_disponiveis_por_data[data_futura.isoformat()] = horarios_disponiveis_na_data
        
        if horarios_disponiveis_por_data:
            disponibilidade_filtrada[dia_semana] = horarios_disponiveis_por_data
            
    return disponibilidade_filtrada

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

    # Validação: Não permitir agendamento para horários que já passaram
    agendamento_datetime = datetime.combine(data_agendamento, hora_agendamento)
    if agendamento_datetime < datetime.now():
        return jsonify({"message": "Não é possível agendar para um horário que já passou."}), 400

    # Verificar se o psicólogo tem disponibilidade para a data e hora
    # O dia da semana é usado para verificar a disponibilidade geral, mas o filtro
    # de horários ocupados já garante que o horário não está mais disponível.
    dia_semana = data_agendamento.strftime("%A").lower() # Ex: "monday"
    
    # A verificação de disponibilidade deve ser feita com base na disponibilidade filtrada
    # Para simplificar, vamos manter a verificação original, mas o frontend deve usar a rota /psicologos
    # para obter os horários disponíveis.
    if psicologo.disponibilidade and dia_semana in psicologo.disponibilidade:
        horarios_disponiveis_no_dia = psicologo.disponibilidade[dia_semana]
        if hora_agendamento_str not in horarios_disponiveis_no_dia:
            return jsonify({"message": "Horário selecionado não está disponível na agenda do psicólogo."}), 400
    else:
        return jsonify({"message": "Psicólogo não tem disponibilidade para o dia selecionado."}), 400

    # Verificar se já existe um agendamento para o mesmo psicólogo, data e hora
    # 1. Verificar se já existe um agendamento para o mesmo psicólogo, data e hora (evita duplicidade)
    agendamento_psicologo_existente = Agendamento.query.filter_by(
        psicologo_id=psicologo_id,
        data_agendamento=data_agendamento,
        hora_agendamento=hora_agendamento
    ).filter(
        Agendamento.status.in_(['Pendente', 'Confirmado']) # Apenas agendamentos ativos
    ).first()

    if agendamento_psicologo_existente:
        return jsonify({"message": "Horário indisponível. Já existe um agendamento ativo para este psicólogo neste horário."}), 409

    # 2. Validação: Verificar se o aluno já tem um agendamento com qualquer psicólogo na mesma data e hora
    agendamento_aluno_existente = Agendamento.query.filter(
        Agendamento.aluno_id == aluno.id,
        Agendamento.data_agendamento == data_agendamento,
        Agendamento.hora_agendamento == hora_agendamento,
        Agendamento.status.in_(['Pendente', 'Confirmado']) # Considerar apenas agendamentos ativos
    ).first()

    if agendamento_aluno_existente:
        # Se o agendamento existente for com um psicólogo diferente do que está sendo agendado
        psicologo_agendado = User.query.get(agendamento_aluno_existente.psicologo_id)
        psicologo_nome = psicologo_agendado.nome if psicologo_agendado else "outro psicólogo"
        return jsonify({
            "message": "Você já possui consulta agendada para esse mesmo dia e horário. Tente novamente com outra data ou horário.",
        }), 409

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
    
    psicologos_list = []
    for p in psicologos:
        # Chama a nova função para obter a disponibilidade filtrada
        disponibilidade_filtrada = get_available_times_for_psicologo(p.id, p.disponibilidade if p.disponibilidade else {})
        
        psicologos_list.append({
            "id": p.id,
            "name": p.nome,
            "specialty": p.especialidades[0] if p.especialidades else "Geral", # Assumindo que especialidades é uma lista
            "availability": disponibilidade_filtrada,
            "description": "", # Será preenchido no frontend ou por outra lógica
            "modes": p.modalidades_atendimento if p.modalidades_atendimento else []
        })
    
    return jsonify(psicologos_list), 200


@agendamentos_bp.route("/agendamentos/<int:agendamento_id>/status", methods=["PUT"])
@jwt_required()
def update_agendamento_status(agendamento_id):
    """
    Rota para psicólogos atualizarem o status do agendamento (Confirmado, Cancelado, Finalizado)
    e marcarem o comparecimento do aluno.
    """
    current_user_id = get_jwt_identity()
    psicologo = User.query.get(current_user_id)

    if not psicologo or psicologo.tipo_usuario != "psicologo":
        return jsonify({"message": "Apenas psicólogos podem alterar o status do agendamento"}), 403

    agendamento = Agendamento.query.get(agendamento_id)
    if not agendamento:
        return jsonify({"message": "Agendamento não encontrado"}), 404

    # O psicólogo só pode alterar o status de seus próprios agendamentos
    if agendamento.psicologo_id != psicologo.id:
        return jsonify({"message": "Acesso negado. Você não é o psicólogo responsável por este agendamento."}), 403

    data = request.get_json()
    novo_status = data.get("status")
    compareceu = data.get("compareceu") # Usado apenas para status 'Finalizado'

    if not novo_status:
        return jsonify({"message": "Status não fornecido"}), 400

    status_permitidos = ['Pendente', 'Confirmado', 'Cancelado', 'Finalizado']
    if novo_status not in status_permitidos:
        return jsonify({"message": f"Status inválido. Status permitidos: {', '.join(status_permitidos)}"}), 400

    # Lógica de transição de status
    if novo_status == 'Finalizado':
        # Para finalizar, o status anterior deve ser 'Confirmado'
        if agendamento.status != 'Confirmado':
            return jsonify({"message": "O agendamento deve estar 'Confirmado' para ser 'Finalizado'."}), 400
        
        # O campo 'compareceu' é obrigatório para finalizar
        if compareceu is None or not isinstance(compareceu, bool):
            return jsonify({"message": "O campo 'compareceu' (true/false) é obrigatório para finalizar o agendamento."}), 400
        
        agendamento.compareceu = compareceu
        agendamento.status = novo_status
        
    elif novo_status == 'Confirmado':
        # Apenas permite confirmar se estiver 'Pendente'
        if agendamento.status != 'Pendente':
            return jsonify({"message": "O agendamento só pode ser 'Confirmado' se estiver 'Pendente'."}), 400
        agendamento.status = novo_status
        
    elif novo_status == 'Cancelado':
        # Permite cancelar se estiver 'Pendente' ou 'Confirmado'
        if agendamento.status not in ['Pendente', 'Confirmado']:
            return jsonify({"message": "O agendamento só pode ser 'Cancelado' se estiver 'Pendente' ou 'Confirmado'."}), 400
        agendamento.status = novo_status
        
    else:
        # Para 'Pendente', não deve haver transição direta por esta rota, mas por segurança:
        if agendamento.status != 'Pendente':
            return jsonify({"message": "Transição de status inválida para 'Pendente'."}), 400
        agendamento.status = novo_status


    db.session.commit()

    return jsonify({"message": f"Status do agendamento {agendamento_id} atualizado para {novo_status}", "agendamento": agendamento.to_dict()}), 200