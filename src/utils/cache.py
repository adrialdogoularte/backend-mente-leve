from functools import wraps
from datetime import datetime, timedelta
import json

# Cache simples em memória (para produção, usar Redis ou Memcached)
_cache = {}
_cache_expiry = {}

def cache_result(expiry_minutes=5):
    """
    Decorator para cache de resultados de funções
    
    Args:
        expiry_minutes (int): Tempo de expiração do cache em minutos
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Criar chave única baseada na função e argumentos
            cache_key = f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # Verificar se existe cache válido
            if cache_key in _cache and cache_key in _cache_expiry:
                if datetime.now() < _cache_expiry[cache_key]:
                    return _cache[cache_key]
                else:
                    # Cache expirado, remover
                    del _cache[cache_key]
                    del _cache_expiry[cache_key]
            
            # Executar função e cachear resultado
            result = func(*args, **kwargs)
            _cache[cache_key] = result
            _cache_expiry[cache_key] = datetime.now() + timedelta(minutes=expiry_minutes)
            
            return result
        return wrapper
    return decorator

def clear_cache():
    """Limpa todo o cache"""
    global _cache, _cache_expiry
    _cache.clear()
    _cache_expiry.clear()

def clear_user_cache(user_id):
    """Limpa cache específico de um usuário"""
    keys_to_remove = []
    for key in _cache.keys():
        if f"user_{user_id}" in key or str(user_id) in key:
            keys_to_remove.append(key)
    
    for key in keys_to_remove:
        if key in _cache:
            del _cache[key]
        if key in _cache_expiry:
            del _cache_expiry[key]

def get_cache_stats():
    """Retorna estatísticas do cache"""
    now = datetime.now()
    valid_entries = sum(1 for expiry in _cache_expiry.values() if expiry > now)
    expired_entries = len(_cache_expiry) - valid_entries
    
    return {
        "total_entries": len(_cache),
        "valid_entries": valid_entries,
        "expired_entries": expired_entries,
        "cache_size_mb": len(str(_cache)) / (1024 * 1024)
    }

# Cache específico para consultas de humor
class HumorCache:
    @staticmethod
    @cache_result(expiry_minutes=10)
    def get_user_stats(user_id):
        """Cache para estatísticas do usuário"""
        from src.models.humor import RegistroHumor
        
        registros = RegistroHumor.query.filter_by(usuario_id=user_id).all()
        
        if not registros:
            return {
                "total_registros": 0,
                "media_humor": 0,
                "emocoes_frequentes": [],
                "fatores_frequentes": []
            }
        
        # Calcular estatísticas
        humores = [r.nivel_humor for r in registros]
        media_humor = sum(humores) / len(humores)
        
        # Emoções mais frequentes
        todas_emocoes = []
        for registro in registros:
            if registro.emocoes:
                try:
                    emocoes = json.loads(registro.emocoes)
                    todas_emocoes.extend(emocoes)
                except:
                    pass
        
        from collections import Counter
        emocoes_counter = Counter(todas_emocoes)
        emocoes_frequentes = [
            {"emocao": emocao, "count": count} 
            for emocao, count in emocoes_counter.most_common(5)
        ]
        
        # Fatores mais frequentes
        todos_fatores = []
        for registro in registros:
            if registro.fatores_influencia:
                try:
                    fatores = json.loads(registro.fatores_influencia)
                    todos_fatores.extend(fatores)
                except:
                    pass
        
        fatores_counter = Counter(todos_fatores)
        fatores_frequentes = [
            {"fator": fator, "count": count} 
            for fator, count in fatores_counter.most_common(5)
        ]
        
        return {
            "total_registros": len(registros),
            "media_humor": round(media_humor, 2),
            "emocoes_frequentes": emocoes_frequentes,
            "fatores_frequentes": fatores_frequentes
        }
    
    @staticmethod
    @cache_result(expiry_minutes=15)
    def get_recent_records(user_id, limit=10):
        """Cache para registros recentes"""
        from src.models.humor import RegistroHumor
        
        registros = RegistroHumor.query.filter_by(usuario_id=user_id)\
                                      .order_by(RegistroHumor.data_registro.desc())\
                                      .limit(limit).all()
        
        return [registro.to_dict() for registro in registros]
    
    @staticmethod
    def invalidate_user_cache(user_id):
        """Invalida cache específico do usuário"""
        clear_user_cache(user_id)

# Cache para analytics
class AnalyticsCache:
    @staticmethod
    @cache_result(expiry_minutes=30)
    def get_correlation_data(user_id, days=30):
        """Cache para dados de correlação"""
        from src.models.humor import RegistroHumor
        from datetime import datetime, timedelta
        from collections import defaultdict
        
        data_limite = datetime.now().date() - timedelta(days=days)
        registros = RegistroHumor.query.filter(
            RegistroHumor.usuario_id == user_id,
            RegistroHumor.data_registro >= data_limite
        ).all()
        
        if not registros:
            return {
                "atividades": [],
                "emocoes": [],
                "fatores_influencia": []
            }
        
        # Processar correlações (lógica similar à rota analytics)
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
            
            # Fatores
            if registro.fatores_influencia:
                try:
                    fatores = json.loads(registro.fatores_influencia)
                    for fator in fatores:
                        fatores_humor[fator].append(nivel_humor)
                except:
                    pass
        
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
            
            return sorted(correlacoes, key=lambda x: x["media_humor"], reverse=True)
        
        return {
            "atividades": calcular_correlacao(atividades_humor),
            "emocoes": calcular_correlacao(emocoes_humor),
            "fatores_influencia": calcular_correlacao(fatores_humor)
        }

