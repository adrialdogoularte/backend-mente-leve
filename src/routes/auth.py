from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity, get_jwt, decode_token
from src.models.user import db, User
import re

def validar_senha_forte(senha):
    """
    Verifica se a senha atende aos critérios de segurança:
    - Mínimo de 8 caracteres
    - Pelo menos uma letra maiúscula
    - Pelo menos uma letra minúscula
    - Pelo menos um número
    - Pelo menos um caractere especial
    """
    if len(senha) < 8:
        return False, "A senha deve ter no mínimo 8 caracteres."
    if not re.search(r"[A-Z]", senha):
        return False, "A senha deve conter pelo menos uma letra maiúscula."
    if not re.search(r"[a-z]", senha):
        return False, "A senha deve conter pelo menos uma letra minúscula."
    if not re.search(r"[0-9]", senha):
        return False, "A senha deve conter pelo menos um número."
    if not re.search(r"[!@#$%^&*()_+=\-{}\[\]:;\"'<>,.?/\\|]", senha):
        return False, "A senha deve conter pelo menos um caractere especial."
    return True, ""
from datetime import timedelta, datetime

auth_bp = Blueprint("auth", __name__)

# Set para armazenar tokens revogados (em produção, usar Redis)
revoked_tokens = set()

@auth_bp.route("/registro-aluno", methods=["POST"])
def registro_aluno():
    """Registra um novo aluno"""
    try:
        data = request.get_json()
        
        # Validar dados obrigatórios para aluno
        required_fields = ["nome", "email", "senha", "universidade", "curso", "periodo", "consentimentoTermos", "consentimentoPolitica", "versaoTermos", "versaoPolitica"]
        for field in required_fields:
            if not data.get(field):
                return jsonify({"message": f"Campo {field} é obrigatório"}), 400
        
        # Validação de senha forte
        senha = data.get("senha")
        is_valid, message = validar_senha_forte(senha)
        if not is_valid:
            return jsonify({"message": message}), 400
        
        if not data["consentimentoTermos"] or not data["consentimentoPolitica"]:
            return jsonify({"message": "É obrigatório consentir com os Termos de Uso e a Política de Privacidade"}), 400
        
        # Verificar se email já existe
        if User.query.filter_by(email=data["email"]).first():
            return jsonify({"message": "Email já cadastrado"}), 400
        
        # Criar usuário aluno
        user = User(
            nome=data["nome"],
            email=data["email"],
            tipo_usuario="aluno",
            universidade=data["universidade"],
            curso=data["curso"],
            periodo=data["periodo"],
            crp=None, # Definir como None para alunos
            especialidades=[], # Definir como lista vazia para alunos
            modalidades_atendimento=[], # Definir como lista vazia para alunos
            disponibilidade={}, # Definir como dicionário vazio para alunos
            # Campos de Consentimento
            consentimento_termos=data["consentimentoTermos"],
            consentimento_politica=data["consentimentoPolitica"],
            data_consentimento=datetime.utcnow(),
            versao_termos=data["versaoTermos"],
            versao_politica=data["versaoPolitica"]
        )
        user.set_password(data["senha"])
        
        db.session.add(user)
        db.session.commit()
        
        # Criar tokens
        access_token = create_access_token(
            identity=str(user.id),  # Converter para string
            expires_delta=timedelta(hours=1)
        )
        refresh_token = create_refresh_token(
            identity=str(user.id),  # Converter para string
            expires_delta=timedelta(days=30)
        )
        
        return jsonify({
            "message": "Aluno cadastrado com sucesso",
            "user": user.to_dict(),
            "access_token": access_token,
            "refresh_token": refresh_token
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"Erro interno: {str(e)}"}), 500

@auth_bp.route("/registro-psicologo", methods=["POST"])
def registro_psicologo():
    """Registra um novo psicólogo"""
    try:
        data = request.get_json()
        
        # Validar dados obrigatórios para psicólogo
        required_fields = ["nome", "email", "senha", "crp", "consentimentoTermos", "consentimentoPolitica", "versaoTermos", "versaoPolitica"]
        for field in required_fields:
            if not data.get(field):
                return jsonify({"message": f"Campo {field} é obrigatório"}), 400
        
        # Validação de senha forte
        senha = data.get("senha")
        is_valid, message = validar_senha_forte(senha)
        if not is_valid:
            return jsonify({"message": message}), 400
        
        if not data["consentimentoTermos"] or not data["consentimentoPolitica"]:
            return jsonify({"message": "É obrigatório consentir com os Termos de Uso e a Política de Privacidade"}), 400

        if not data.get("especialidades") or not isinstance(data.get("especialidades"), list) or len(data.get("especialidades")) == 0:
            return jsonify({"message": "Pelo menos uma especialidade é obrigatória"}), 400
        
        if not data.get("modalidades_atendimento") or not isinstance(data.get("modalidades_atendimento"), list) or len(data.get("modalidades_atendimento")) == 0:
            return jsonify({"message": "Pelo menos uma modalidade de atendimento é obrigatória"}), 400
        
        # Verificar se email já existe
        if User.query.filter_by(email=data["email"]).first():
            return jsonify({"message": "Email já cadastrado"}), 400
        
        # Criar usuário psicólogo
        user = User(
            nome=data["nome"],
            email=data["email"],
            tipo_usuario="psicologo",
            crp=data["crp"],
            especialidades=data["especialidades"],
            modalidades_atendimento=data["modalidades_atendimento"],
            disponibilidade=data.get("disponibilidade", {}), # Adicionar disponibilidade
            # Campos de Consentimento
            consentimento_termos=data["consentimentoTermos"],
            consentimento_politica=data["consentimentoPolitica"],
            data_consentimento=datetime.utcnow(),
            versao_termos=data["versaoTermos"],
            versao_politica=data["versaoPolitica"]
        )
        
        user.set_password(data["senha"])
        
        db.session.add(user)
        db.session.commit()
        
        # Criar tokens
        access_token = create_access_token(
            identity=str(user.id),  # Converter para string
            expires_delta=timedelta(hours=1)
        )
        refresh_token = create_refresh_token(
            identity=str(user.id),  # Converter para string
            expires_delta=timedelta(days=30)
        )
        
        return jsonify({
            "message": "Psicólogo cadastrado com sucesso",
            "user": user.to_dict(),
            "access_token": access_token,
            "refresh_token": refresh_token
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"Erro interno: {str(e)}"}), 500

@auth_bp.route("/login", methods=["POST"])
def login():
    """Faz login do usuário"""
    try:
        data = request.get_json()
        
        if not data.get("email") or not data.get("senha"):
            return jsonify({"message": "Email e senha são obrigatórios"}), 400
        
        user = User.query.filter_by(email=data["email"]).first()
        
        if not user or not user.check_password(data["senha"]):
            return jsonify({"message": "Email ou senha incorretos"}), 401
        
        if not user.ativo:
            return jsonify({"message": "Usuário inativo"}), 401
        
        # Criar tokens
        access_token = create_access_token(
            identity=str(user.id),  # Converter para string
            expires_delta=timedelta(hours=1)
        )
        refresh_token = create_refresh_token(
            identity=str(user.id),  # Converter para string
            expires_delta=timedelta(days=30)
        )
        
        return jsonify({
            "message": "Login realizado com sucesso",
            "user": user.to_dict(),
            "access_token": access_token,
            "refresh_token": refresh_token
        }), 200
        
    except Exception as e:
        return jsonify({"message": f"Erro interno: {str(e)}"}), 500

@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    """Renova o token de acesso"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(int(current_user_id))  # Converter para int
        
        if not user or not user.ativo:
            return jsonify({"message": "Usuário não encontrado ou inativo"}), 404
        
        new_token = create_access_token(
            identity=current_user_id,
            expires_delta=timedelta(hours=1)
        )
        
        return jsonify({
            "access_token": new_token
        }), 200
        
    except Exception as e:
        return jsonify({"message": f"Erro interno: {str(e)}"}), 500

@auth_bp.route("/refresh-token", methods=["POST"])
def refresh_with_body():
    try:
        data = request.get_json() or {}
        token = data.get("refresh_token")
        if not token:
            return jsonify({"message": "refresh_token é obrigatório"}), 400

        decoded = decode_token(token)
        if decoded.get("type") != "refresh":
            return jsonify({"message": "Token inválido (não é refresh)"}), 401

        user_id = decoded.get("sub")
        user = User.query.get(int(user_id))  # Converter para int
        if not user or not user.ativo:
            return jsonify({"message": "Usuário não encontrado ou inativo"}), 404

        new_token = create_access_token(identity=user_id, expires_delta=timedelta(hours=1))
        return jsonify({"access_token": new_token}), 200

    except Exception as e:
        return jsonify({"message": f"Token inválido: {str(e)}"}), 401

@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    """Faz logout do usuário"""
    try:
        jti = get_jwt()["jti"]
        revoked_tokens.add(jti)
        
        return jsonify({"message": "Logout realizado com sucesso"}), 200
        
    except Exception as e:
        return jsonify({"message": f"Erro interno: {str(e)}"}), 500

@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_current_user():
    """Obtém informações do usuário atual"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(int(current_user_id))  # Converter para int
        
        if not user:
            return jsonify({"message": "Usuário não encontrado"}), 404
        
        return jsonify({"user": user.to_dict()}), 200
        
    except Exception as e:
        return jsonify({"message": f"Erro interno: {str(e)}"}), 500

@auth_bp.route("/perfil", methods=["PUT"])
@jwt_required()
def update_perfil():
    """Atualiza os dados do perfil do usuário (aluno ou psicólogo)"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(int(current_user_id))

        if not user:
            return jsonify({"message": "Usuário não encontrado"}), 404

        data = request.get_json()

        # Campos comuns
        user.nome = data.get("nome", user.nome)
        # O email não deve ser alterado aqui, pois é a chave de login.

        if user.tipo_usuario == "aluno":
            user.universidade = data.get("universidade", user.universidade)
            user.curso = data.get("curso", user.curso)
            user.periodo = data.get("periodo", user.periodo)
        
        elif user.tipo_usuario == "psicologo":
            user.crp = data.get("crp", user.crp)
            # A especialidade é enviada como lista do frontend, mas o frontend envia como string separada por vírgula.
            # No frontend (Perfil.jsx), a lógica de conversão está correta.
            # Aqui, o backend espera uma lista de strings.
            especialidades = data.get("especialidades")
            if especialidades is not None:
                user.especialidades = especialidades

        db.session.commit()

        return jsonify({"message": "Perfil atualizado com sucesso", "user": user.to_dict()}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"Erro interno: {str(e)}"}), 500

@auth_bp.route("/psicologo/disponibilidade", methods=["PUT"])
@jwt_required()
def update_psicologo_disponibilidade():
    """Atualiza a disponibilidade de um psicólogo"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(int(current_user_id))
    
        if not user or user.tipo_usuario != "psicologo":
            return jsonify({"message": "Acesso negado. Somente psicólogos podem atualizar a disponibilidade."}), 403
    
        data = request.get_json()
        disponibilidade = data.get("disponibilidade")
    
        if not isinstance(disponibilidade, dict):
            return jsonify({"message": "Formato de disponibilidade inválido."}), 400
    
        user.disponibilidade = disponibilidade
        db.session.commit()
    
        return jsonify({"message": "Disponibilidade atualizada com sucesso", "user": user.to_dict()}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"Erro interno: {str(e)}"}), 500

@auth_bp.route("/delete-account", methods=["DELETE"])
@jwt_required()
def delete_account():
    """Implementa o Direito ao Esquecimento (exclusão total da conta)"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(int(current_user_id))

        if not user:
            return jsonify({"message": "Usuário não encontrado"}), 404
        
        # Exclui o usuário do banco de dados
        user.delete_account()

        # O logout no frontend será feito após o sucesso desta requisição
        return jsonify({"message": "Conta excluída permanentemente (Direito ao Esquecimento)"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"Erro interno ao excluir conta: {str(e)}"}), 500
