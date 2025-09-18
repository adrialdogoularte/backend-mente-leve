from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.extensions import db
from src.models.humor import RegistroHumor
from src.utils.cache import HumorCache
import json
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
            usuario_id=user_id,
            nivel_humor=data["nivel_humor"],
            descricao=data.get("descricao"),
            emocoes=json.dumps(data.get("emocoes")) if data.get("emocoes") else None,
            fatores_influencia=json.dumps(data.get("fatores_influencia")) if data.get("fatores_influencia") else None,
            atividades=json.dumps(data.get("atividades")) if data.get("atividades") else None,
            atividades_planejadas=json.dumps(data.get("atividades_planejadas")) if data.get("atividades_planejadas") else None,
            horas_sono=data.get("horas_sono"),
            qualidade_sono=data.get("qualidade_sono"),
            nivel_estresse=data.get("nivel_estresse"),
            notas=data.get("notas"),
            data_registro=datetime.strptime(data.get("data_registro"), 
                                            "%Y-%m-%d") if data.get("data_registro") else datetime.now()
        )
        db.session.add(novo_registro)
        db.session.commit()
        
        # Invalidar cache do usuário após novo registro
        HumorCache.invalidate_user_cache(user_id)
        
        return jsonify({"message": "Registro de humor salvo com sucesso!", "registro": novo_registro.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Erro ao salvar registro de humor", "error": str(e)}), 500

@humor_bp.route("/humor", methods=["GET"])
@jwt_required()
def get_registros_humor():
    user_id = get_jwt_identity()
    limite = request.args.get("limite", 10, type=int)

    try:
        # Usar cache para registros recentes
        registros = HumorCache.get_recent_records(user_id, limite)
        return jsonify({"registros": registros}), 200
    except Exception as e:
        # Fallback para consulta direta se cache falhar
        query = RegistroHumor.query.filter_by(usuario_id=user_id).order_by(RegistroHumor.data_registro.desc())
        if limite:
            query = query.limit(limite)
        registros = query.all()
        return jsonify({"registros": [registro.to_dict() for registro in registros]}), 200

@humor_bp.route("/humor/estatisticas", methods=["GET"])
@jwt_required()
def get_estatisticas_humor():
    user_id = get_jwt_identity()
    
    try:
        # Usar cache para estatísticas
        stats = HumorCache.get_user_stats(user_id)
        
        # Converter formato para compatibilidade com frontend existente
        emocoes_frequentes = [(item["emocao"], item["count"]) for item in stats["emocoes_frequentes"]]
        
        return jsonify({
            "total_registros": stats["total_registros"],
            "media_humor": stats["media_humor"],
            "emocoes_frequentes": emocoes_frequentes
        }), 200
    except Exception as e:
        # Fallback para consulta direta se cache falhar
        registros = RegistroHumor.query.filter_by(usuario_id=user_id).all()

        if not registros:
            return jsonify({"total_registros": 0, "media_humor": 0, "emocoes_frequentes": []}), 200

        total_registros = len(registros)
        soma_humor = sum(r.nivel_humor for r in registros)
        media_humor = soma_humor / total_registros

        emocoes_contagem = {}
        for r in registros:
            if r.emocoes:
                try:
                    emocoes = json.loads(r.emocoes)
                    for emocao in emocoes:
                        emocoes_contagem[emocao] = emocoes_contagem.get(emocao, 0) + 1
                except:
                    # Fallback para formato antigo (string separada por vírgula)
                    for emocao in r.emocoes.split(","):
                        emocao = emocao.strip()
                        emocoes_contagem[emocao] = emocoes_contagem.get(emocao, 0) + 1
        
        emocoes_frequentes = sorted(emocoes_contagem.items(), key=lambda item: item[1], reverse=True)

        return jsonify({
            "total_registros": total_registros,
            "media_humor": round(media_humor, 2),
            "emocoes_frequentes": emocoes_frequentes
        }), 200

@humor_bp.route("/humor/tendencias", methods=["GET"])
@jwt_required()
def get_tendencias_humor():
    """Nova rota otimizada para tendências de humor"""
    try:
        user_id = get_jwt_identity()
        days = request.args.get('days', 30, type=int)
        
        # Consulta otimizada com limite de data
        from datetime import datetime, timedelta
        data_limite = datetime.now().date() - timedelta(days=days)
        
        registros = RegistroHumor.query.filter(
            RegistroHumor.usuario_id == user_id,
            RegistroHumor.data_registro >= data_limite
        ).order_by(RegistroHumor.data_registro.asc()).all()
        
        # Processar dados para gráfico de tendências
        tendencias = []
        for registro in registros:
            tendencias.append({
                'data': registro.data_registro.strftime('%Y-%m-%d'),
                'humor': registro.nivel_humor,
                'estresse': registro.nivel_estresse or 0,
                'sono': registro.qualidade_sono or 0
            })
        
        return jsonify({'tendencias': tendencias}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@humor_bp.route("/humor/cache/stats", methods=["GET"])
@jwt_required()
def get_cache_stats():
    """Rota para monitorar estatísticas do cache (apenas para debug)"""
    try:
        from src.utils.cache import get_cache_stats
        stats = get_cache_stats()
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
