from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict
from security.auth.auth_middleware import AuthMiddleware
from security.auth.jwt_manager import JWTManager
from security.auth.refresh_token import RefreshTokenManager
from loguru import logger

router = APIRouter()
auth = AuthMiddleware()
jwt_manager = JWTManager()
refresh_manager = RefreshTokenManager()

@router.post("/auth/login")
async def login(email: str, password: str):
    """Endpoint de login que retorna access e refresh tokens."""
    try:
        # Aqui você implementaria a validação do usuário
        # Este é apenas um exemplo
        user = {"id": "user_id", "email": email}
        
        # Criar tokens
        access_token = jwt_manager.create_access_token(user)
        refresh_token = jwt_manager.create_refresh_token(user)
        
        # Armazenar refresh token
        await refresh_manager.store_refresh_token(user["id"], refresh_token)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    except Exception as e:
        logger.error(f"Erro no login: {str(e)}")
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

@router.post("/auth/refresh")
async def refresh_token(refresh_token: str):
    """Endpoint para atualizar o access token usando um refresh token."""
    try:
        # Validar refresh token
        user_id = await refresh_manager.validate_refresh_token(refresh_token)
        if not user_id:
            raise HTTPException(status_code=401, detail="Refresh token inválido")
        
        # Criar novo access token
        new_access_token = jwt_manager.create_access_token({"user_id": user_id})
        
        return {
            "access_token": new_access_token,
            "token_type": "bearer"
        }
    except Exception as e:
        logger.error(f"Erro ao atualizar token: {str(e)}")
        raise HTTPException(status_code=401, detail="Erro ao atualizar token")

@router.post("/auth/logout")
@auth.require_auth()
async def logout(refresh_token: str, auth_payload: Dict):
    """Endpoint para logout, invalidando o refresh token."""
    try:
        await refresh_manager.invalidate_refresh_token(refresh_token)
        return {"message": "Logout realizado com sucesso"}
    except Exception as e:
        logger.error(f"Erro no logout: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro ao realizar logout")

# Exemplo de rota protegida que requer autenticação
@router.get("/api/prices")
@auth.require_auth(required_roles=["viewer", "admin"])
async def get_prices(auth_payload: Dict):
    """Endpoint protegido que requer autenticação e role específica."""
    try:
        # Implementação da lógica de negócio
        return {"message": "Lista de preços", "user_id": auth_payload["user_id"]}
    except Exception as e:
        logger.error(f"Erro ao obter preços: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro ao obter preços")

# Exemplo de rota protegida que requer role de admin
@router.post("/api/prices")
@auth.require_auth(required_roles=["admin"])
async def update_prices(auth_payload: Dict):
    """Endpoint protegido que requer role de admin."""
    try:
        # Implementação da lógica de negócio
        return {"message": "Preços atualizados", "user_id": auth_payload["user_id"]}
    except Exception as e:
        logger.error(f"Erro ao atualizar preços: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro ao atualizar preços") 