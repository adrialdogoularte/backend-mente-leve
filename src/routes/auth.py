from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity, get_jwt, decode_token
from src.models.user import db, User
from datetime import timedelta

auth_bp = Blueprint("auth", __name__)

# Set para armazenar tokens revogados (em produção, usar Redis)
revoked_tokens = set()

@auth_bp.route("/registro-aluno", methods=["POST"])
def registro_aluno():
    """Registra um novo aluno"""
    try:
        data = request.get_json()
        
        # Validar dados obrigatórios para aluno
        required_fields = ["nome", "email", "senha", "universidade", "curso", "periodo"]
        for field in required_fields:
            if not data.get(field):
                return jsonify({"message": f"Campo {field} é obrigatório"}), 400
        
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
            periodo=data["periodo"]
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
        required_fields = ["nome", "email", "senha", "crp"]
        for field in required_fields:
            if not data.get(field):
                return jsonify({"message": f"Campo {field} é obrigatório"}), 400

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
            modalidades_atendimento=data["modalidades_atendimento"]
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