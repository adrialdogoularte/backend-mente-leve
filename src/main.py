import os
import sys
# DON\'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__ )))

from flask import Flask, send_from_directory, jsonify
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from datetime import timedelta

# Importar modelos
from src.extensions import db
from src.models.user import User
from src.models.avaliacao import Avaliacao  # noqa: F401 (garante criação da tabela)
from src.models.compartilhamento import Compartilhamento  # noqa: F401
from src.models.humor import RegistroHumor  # noqa: F401
from src.models.agendamento import Agendamento # noqa: F401

# Importar blueprints
from src.routes.user import user_bp
from src.routes.auth import auth_bp, revoked_tokens
from src.routes.avaliacoes import avaliacoes_bp
from src.routes.compartilhamentos import compartilhamentos_bp
from src.routes.humor import humor_bp
from src.routes.agendamentos import agendamentos_bp
from src.routes.avaliacoes_agendamento import avaliacoes_agendamento_bp # Importar o blueprint

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))

# Configurações
app.config['SECRET_KEY'] = 'mente-leve-secret-key-2024'
app.config['JWT_SECRET_KEY'] = 'jwt-secret-key-mente-leve'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)

# Configuração do banco de dados (SQLite local)
db_path = os.path.join(os.path.dirname(__file__), 'database', 'app.db')
os.makedirs(os.path.dirname(db_path), exist_ok=True)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializar extensões
db.init_app(app)
jwt = JWTManager(app)
# CORS configurado para permitir todas as origens durante desenvolvimento
# ATENÇÃO: Em produção, configure origens específicas por segurança
CORS(app, origins=[
    'http://localhost:5173',
    'http://127.0.0.1:5173',
    'http://45.180.159.55:8000', # Porta externa do Frontend (Regra 2)
    'http://45.180.159.55:8001', # Porta externa do Backend (Regra 1)
    
    # Expressão Regular para permitir qualquer IP na rede 192.168.x.x
    r'http://192\.168\..*',

    # Expressão Regular para permitir qualquer IP na rede 10.x.x.x
    r'http://10\..*',

    # Expressão Regular para permitir qualquer IP na rede 172.16.x.x a 172.31.x.x
    r'http://172\.(1[6-9]|2[0-9]|3[0-1])\..*'
    
], supports_credentials=True )

# Registrar blueprints
app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(avaliacoes_bp, url_prefix='/api') # Corrigido o prefixo aqui
app.register_blueprint(compartilhamentos_bp, url_prefix="/api/compartilhamentos")
app.register_blueprint(humor_bp, url_prefix="/api") # ALTERADO AQUI
app.register_blueprint(agendamentos_bp, url_prefix="/api")
# Importar e registrar blueprint de lembretes
from src.routes.lembretes import lembretes_bp
app.register_blueprint(lembretes_bp, url_prefix='/api')

# Importar e registrar blueprint de analytics
from src.routes.analytics import analytics_bp
app.register_blueprint(analytics_bp, url_prefix='/api')

# Registrar o blueprint de avaliações de agendamento
app.register_blueprint(avaliacoes_agendamento_bp, url_prefix='/api')

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/')
def index():
    return send_from_directory(os.path.join(os.path.dirname(__file__), 'static'), 'index.html')

@app.route('/<path:path>')
def serve_react_app(path):
    static_folder_path = os.path.join(os.path.dirname(__file__), 'static')
    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return 'index.html not found', 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

with app.app_context():
    db.create_all()
