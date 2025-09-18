from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.extensions import db
from src.models.user import User
from src.models.humor import RegistroHumor
from datetime import datetime, timedelta
import json

lembretes_bp = Blueprint("lembretes", __name__)

@lembretes_bp.route("/lembretes/configurar", methods=["POST"])
@jwt_required()
def configurar_lembrete():
    """Configura lembrete diário para o usuário"""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({"message": "Usuário não encontrado"}), 404
        
        # Configurações do lembrete
        horario_lembrete = data.get("horario", "20:00")  # Padrão: 20:00
        ativo = data.get("ativo", True)
        
        # Salvar configurações no perfil do usuário (pode ser expandido para uma tabela separada)
        configuracoes = {
            "lembrete_diario": {
                "ativo": ativo,
                "horario": horario_lembrete,
                "data_configuracao": datetime.utcnow().isoformat()
            }
        }
        
        # Por simplicidade, vamos salvar nas especialidades (pode ser criada uma tabela específica)
        user.especialidades = json.dumps(configuracoes)
        db.session.commit()
        
        return jsonify({
            "message": "Lembrete configurado com sucesso!",
            "configuracao": configuracoes["lembrete_diario"]
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Erro ao configurar lembrete", "error": str(e)}), 500

@lembretes_bp.route("/lembretes/status", methods=["GET"])
@jwt_required()
def status_lembrete():
    """Verifica o status do lembrete do usuário"""
    user_id = get_jwt_identity()
    
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({"message": "Usuário não encontrado"}), 404
        
        # Verificar se há configuração de lembrete
        if user.especialidades:
            try:
                configuracoes = json.loads(user.especialidades)
                lembrete_config = configuracoes.get("lembrete_diario", {})
            except:
                lembrete_config = {}
        else:
            lembrete_config = {}
        
        # Verificar se já registrou humor hoje
        hoje = datetime.now().date()
        registro_hoje = RegistroHumor.query.filter_by(
            usuario_id=user_id,
            data_registro=hoje
        ).first()
        
        return jsonify({
            "lembrete_ativo": lembrete_config.get("ativo", False),
            "horario": lembrete_config.get("horario", "20:00"),
            "registrou_hoje": registro_hoje is not None,
            "data_ultimo_registro": registro_hoje.data_registro.isoformat() if registro_hoje else None
        }), 200
        
    except Exception as e:
        return jsonify({"message": "Erro ao verificar status", "error": str(e)}), 500

@lembretes_bp.route("/lembretes/sugestoes", methods=["GET"])
@jwt_required()
def sugestoes_baseadas_historico():
    """Fornece sugestões baseadas no histórico do usuário"""
    user_id = get_jwt_identity()
    
    try:
        # Buscar registros dos últimos 7 dias
        data_limite = datetime.now().date() - timedelta(days=7)
        registros = RegistroHumor.query.filter(
            RegistroHumor.usuario_id == user_id,
            RegistroHumor.data_registro >= data_limite
        ).all()
        
        if not registros:
            return jsonify({
                "sugestoes": [
                    "Que tal começar registrando como você se sente hoje?",
                    "Registrar seu humor diariamente pode ajudar no autoconhecimento.",
                    "Experimente anotar uma atividade que planeja fazer amanhã!"
                ]
            }), 200
        
        # Analisar padrões
        atividades_positivas = []
        emocoes_frequentes = []
        
        for registro in registros:
            if registro.nivel_humor >= 4:  # Humor bom ou muito bom
                if registro.atividades:
                    try:
                        atividades = json.loads(registro.atividades)
                        atividades_positivas.extend(atividades)
                    except:
                        pass
            
            if registro.emocoes:
                try:
                    emocoes = json.loads(registro.emocoes)
                    emocoes_frequentes.extend(emocoes)
                except:
                    pass
        
        # Contar frequências
        from collections import Counter
        atividades_counter = Counter(atividades_positivas)
        emocoes_counter = Counter(emocoes_frequentes)
        
        sugestoes = []
        
        if atividades_counter:
            atividade_top = atividades_counter.most_common(1)[0][0]
            sugestoes.append(f"Você costuma se sentir bem quando faz: {atividade_top}. Que tal planejar isso para hoje?")
        
        if emocoes_counter:
            emocao_top = emocoes_counter.most_common(1)[0][0]
            sugestoes.append(f"Você tem se sentido {emocao_top.lower()} frequentemente. Como está se sentindo hoje?")
        
        if len(registros) >= 3:
            media_humor = sum(r.nivel_humor for r in registros) / len(registros)
            if media_humor >= 4:
                sugestoes.append("Seu humor tem estado ótimo! Continue assim!")
            elif media_humor <= 2:
                sugestoes.append("Notamos que seu humor tem estado baixo. Lembre-se de que é normal e você pode buscar ajuda se precisar.")
        
        if not sugestoes:
            sugestoes = [
                "Continue registrando seu humor para obtermos insights personalizados!",
                "Que tal experimentar uma nova atividade hoje?",
                "Lembre-se de cuidar do seu bem-estar mental."
            ]
        
        return jsonify({"sugestoes": sugestoes}), 200
        
    except Exception as e:
        return jsonify({"message": "Erro ao gerar sugestões", "error": str(e)}), 500

