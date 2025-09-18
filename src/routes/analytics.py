from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.extensions import db
from src.models.humor import RegistroHumor
from datetime import datetime, timedelta
import json
from collections import Counter, defaultdict

analytics_bp = Blueprint("analytics", __name__)

@analytics_bp.route("/analytics/correlacao-humor-atividades", methods=["GET"])
@jwt_required()
def correlacao_humor_atividades():
    """Analisa a correlação entre humor e atividades do usuário"""
    user_id = get_jwt_identity()
    
    # Parâmetros opcionais
    dias = request.args.get("dias", 30, type=int)  # Últimos 30 dias por padrão
    
    try:
        # Buscar registros do período
        data_limite = datetime.now().date() - timedelta(days=dias)
        registros = RegistroHumor.query.filter(
            RegistroHumor.usuario_id == user_id,
            RegistroHumor.data_registro >= data_limite
        ).all()
        
        if not registros:
            return jsonify({
                "message": "Não há dados suficientes para análise",
                "correlacoes": [],
                "resumo": {
                    "total_registros": 0,
                    "periodo_dias": dias
                }
            }), 200
        
        # Analisar correlações
        atividades_humor = defaultdict(list)
        emocoes_humor = defaultdict(list)
        fatores_humor = defaultdict(list)
        
        for registro in registros:
            nivel_humor = registro.nivel_humor
            
            # Atividades
            if registro.atividades:
                try:
                    atividades = json.loads(registro.atividades)
                    for atividade in atividades:
                        atividades_humor[atividade].append(nivel_humor)
                except:
                    pass
            
            # Emoções
            if registro.emocoes:
                try:
                    emocoes = json.loads(registro.emocoes)
                    for emocao in emocoes:
                        emocoes_humor[emocao].append(nivel_humor)
                except:
                    pass
            
            # Fatores de influência
            if registro.fatores_influencia:
                try:
                    fatores = json.loads(registro.fatores_influencia)
                    for fator in fatores:
                        fatores_humor[fator].append(nivel_humor)
                except:
                    pass
        
        # Calcular médias e correlações
        def calcular_correlacao(dados_dict, min_ocorrencias=2):
            correlacoes = []
            for item, humores in dados_dict.items():
                if len(humores) >= min_ocorrencias:
                    media_humor = sum(humores) / len(humores)
                    correlacoes.append({
                        "item": item,
                        "media_humor": round(media_humor, 2),
                        "frequencia": len(humores),
                        "impacto": "positivo" if media_humor >= 4 else "neutro" if media_humor >= 3 else "negativo"
                    })
            
            # Ordenar por média de humor (decrescente)
            return sorted(correlacoes, key=lambda x: x["media_humor"], reverse=True)
        
        correlacoes_atividades = calcular_correlacao(atividades_humor)
        correlacoes_emocoes = calcular_correlacao(emocoes_humor)
        correlacoes_fatores = calcular_correlacao(fatores_humor)
        
        # Estatísticas gerais
        media_geral = sum(r.nivel_humor for r in registros) / len(registros)
        
        # Insights automáticos
        insights = []
        
        # Atividades mais positivas
        if correlacoes_atividades:
            melhor_atividade = correlacoes_atividades[0]
            if melhor_atividade["media_humor"] >= 4:
                insights.append(f"A atividade '{melhor_atividade['item']}' está associada ao seu melhor humor (média {melhor_atividade['media_humor']}).")
        
        # Fatores mais negativos
        fatores_negativos = [f for f in correlacoes_fatores if f["impacto"] == "negativo"]
        if fatores_negativos:
            pior_fator = fatores_negativos[-1]  # Último da lista ordenada
            insights.append(f"O fator '{pior_fator['item']}' parece impactar negativamente seu humor (média {pior_fator['media_humor']}).")
        
        # Padrões de humor
        if media_geral >= 4:
            insights.append("Seu humor tem estado consistentemente positivo no período analisado!")
        elif media_geral <= 2:
            insights.append("Seu humor tem estado baixo. Considere buscar atividades que te fazem bem.")
        
        return jsonify({
            "correlacoes": {
                "atividades": correlacoes_atividades,
                "emocoes": correlacoes_emocoes,
                "fatores_influencia": correlacoes_fatores
            },
            "resumo": {
                "total_registros": len(registros),
                "periodo_dias": dias,
                "media_humor_geral": round(media_geral, 2),
                "data_inicio": data_limite.isoformat(),
                "data_fim": datetime.now().date().isoformat()
            },
            "insights": insights
        }), 200
        
    except Exception as e:
        return jsonify({"message": "Erro ao analisar correlações", "error": str(e)}), 500

@analytics_bp.route("/analytics/tendencias-humor", methods=["GET"])
@jwt_required()
def tendencias_humor():
    """Analisa tendências do humor ao longo do tempo"""
    user_id = get_jwt_identity()
    
    # Parâmetros
    dias = request.args.get("dias", 30, type=int)
    
    try:
        data_limite = datetime.now().date() - timedelta(days=dias)
        registros = RegistroHumor.query.filter(
            RegistroHumor.usuario_id == user_id,
            RegistroHumor.data_registro >= data_limite
        ).order_by(RegistroHumor.data_registro.asc()).all()
        
        if not registros:
            return jsonify({
                "message": "Não há dados suficientes",
                "tendencias": []
            }), 200
        
        # Agrupar por data
        humor_por_data = {}
        for registro in registros:
            data_str = registro.data_registro.isoformat()
            humor_por_data[data_str] = registro.nivel_humor
        
        # Calcular tendência (simples: comparar primeira e última semana)
        datas_ordenadas = sorted(humor_por_data.keys())
        
        tendencia = "estável"
        if len(datas_ordenadas) >= 7:
            # Primeira semana
            primeira_semana = datas_ordenadas[:7]
            media_primeira = sum(humor_por_data[d] for d in primeira_semana) / len(primeira_semana)
            
            # Última semana
            ultima_semana = datas_ordenadas[-7:]
            media_ultima = sum(humor_por_data[d] for d in ultima_semana) / len(ultima_semana)
            
            diferenca = media_ultima - media_primeira
            if diferenca > 0.5:
                tendencia = "melhorando"
            elif diferenca < -0.5:
                tendencia = "piorando"
        
        # Preparar dados para gráfico
        dados_grafico = [
            {
                "data": data,
                "humor": humor_por_data[data],
                "data_formatada": datetime.fromisoformat(data).strftime("%d/%m")
            }
            for data in datas_ordenadas
        ]
        
        return jsonify({
            "tendencias": dados_grafico,
            "resumo": {
                "tendencia_geral": tendencia,
                "total_dias": len(dados_grafico),
                "media_periodo": round(sum(humor_por_data.values()) / len(humor_por_data), 2)
            }
        }), 200
        
    except Exception as e:
        return jsonify({"message": "Erro ao analisar tendências", "error": str(e)}), 500

@analytics_bp.route("/analytics/relatorio-completo", methods=["GET"])
@jwt_required()
def relatorio_completo():
    """Gera um relatório completo de análise do humor"""
    user_id = get_jwt_identity()
    
    try:
        # Buscar dados dos últimos 30 dias
        data_limite = datetime.now().date() - timedelta(days=30)
        registros = RegistroHumor.query.filter(
            RegistroHumor.usuario_id == user_id,
            RegistroHumor.data_registro >= data_limite
        ).all()
        
        if not registros:
            return jsonify({
                "message": "Não há dados suficientes para gerar relatório"
            }), 200
        
        # Estatísticas básicas
        humores = [r.nivel_humor for r in registros]
        media_humor = sum(humores) / len(humores)
        humor_mais_frequente = Counter(humores).most_common(1)[0][0]
        
        # Distribuição de humor
        distribuicao = Counter(humores)
        distribuicao_percentual = {
            str(k): round((v / len(humores)) * 100, 1) 
            for k, v in distribuicao.items()
        }
        
        # Atividades mais frequentes
        todas_atividades = []
        for registro in registros:
            if registro.atividades:
                try:
                    atividades = json.loads(registro.atividades)
                    todas_atividades.extend(atividades)
                except:
                    pass
        
        atividades_frequentes = Counter(todas_atividades).most_common(5)
        
        # Fatores de influência mais comuns
        todos_fatores = []
        for registro in registros:
            if registro.fatores_influencia:
                try:
                    fatores = json.loads(registro.fatores_influencia)
                    todos_fatores.extend(fatores)
                except:
                    pass
        
        fatores_frequentes = Counter(todos_fatores).most_common(5)
        
        # Qualidade do sono (se disponível)
        sono_dados = [r.qualidade_sono for r in registros if r.qualidade_sono]
        media_sono = sum(sono_dados) / len(sono_dados) if sono_dados else None
        
        # Nível de estresse (se disponível)
        estresse_dados = [r.nivel_estresse for r in registros if r.nivel_estresse]
        media_estresse = sum(estresse_dados) / len(estresse_dados) if estresse_dados else None
        
        relatorio = {
            "periodo": {
                "inicio": data_limite.isoformat(),
                "fim": datetime.now().date().isoformat(),
                "total_registros": len(registros)
            },
            "estatisticas_humor": {
                "media": round(media_humor, 2),
                "mais_frequente": humor_mais_frequente,
                "distribuicao_percentual": distribuicao_percentual
            },
            "atividades_frequentes": [
                {"atividade": ativ, "frequencia": freq} 
                for ativ, freq in atividades_frequentes
            ],
            "fatores_influencia_frequentes": [
                {"fator": fator, "frequencia": freq} 
                for fator, freq in fatores_frequentes
            ],
            "qualidade_sono_media": round(media_sono, 2) if media_sono else None,
            "nivel_estresse_medio": round(media_estresse, 2) if media_estresse else None,
            "recomendacoes": []
        }
        
        # Gerar recomendações
        if media_humor >= 4:
            relatorio["recomendacoes"].append("Parabéns! Seu humor tem estado ótimo. Continue com as atividades que te fazem bem!")
        elif media_humor <= 2:
            relatorio["recomendacoes"].append("Seu humor tem estado baixo. Considere buscar ajuda profissional e praticar atividades que te trazem alegria.")
        
        if media_sono and media_sono < 3:
            relatorio["recomendacoes"].append("Sua qualidade de sono pode estar afetando seu humor. Tente melhorar sua higiene do sono.")
        
        if media_estresse and media_estresse > 3:
            relatorio["recomendacoes"].append("Seus níveis de estresse estão elevados. Considere técnicas de relaxamento e manejo do estresse.")
        
        return jsonify(relatorio), 200
        
    except Exception as e:
        return jsonify({"message": "Erro ao gerar relatório", "error": str(e)}), 500

