from functools import wraps
from typing import Callable, List, Optional, Dict
from loguru import logger
from .jwt_manager import JWTManager
from .role_manager import RoleManager

class UnauthorizedError(Exception):
    pass

class ForbiddenError(Exception):
    pass

class AuthMiddleware:
    def __init__(self):
        self.jwt_manager = JWTManager()
        self.role_manager = RoleManager()

    def _extract_token_from_header(self, headers: Dict) -> Optional[str]:
        """Extrai o token JWT do header Authorization."""
        try:
            auth_header = headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                return None
            return auth_header.split(' ')[1]
        except Exception as e:
            logger.error(f"Erro ao extrair token do header: {str(e)}")
            return None

    def require_auth(self, required_roles: List[str] = None):
        """Decorator para proteger rotas que requerem autenticação."""
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                try:
                    # Extrair token do header
                    token = self._extract_token_from_header(kwargs.get('headers', {}))
                    if not token:
                        raise UnauthorizedError("Token não fornecido")

                    # Verificar token
                    payload = self.jwt_manager.verify_token(token)
                    if not payload:
                        raise UnauthorizedError("Token inválido ou expirado")

                    # Verificar tipo do token
                    if payload.get('type') != 'access':
                        raise UnauthorizedError("Tipo de token inválido")

                    # Verificar roles se necessário
                    if required_roles:
                        if not await self.role_manager.has_required_roles(payload['user_id'], required_roles):
                            raise ForbiddenError("Permissão insuficiente")

                    # Adicionar payload ao contexto
                    kwargs['auth_payload'] = payload
                    return await func(*args, **kwargs)

                except UnauthorizedError as e:
                    logger.warning(f"Erro de autenticação: {str(e)}")
                    return {"error": str(e)}, 401
                except ForbiddenError as e:
                    logger.warning(f"Erro de autorização: {str(e)}")
                    return {"error": str(e)}, 403
                except Exception as e:
                    logger.error(f"Erro inesperado na autenticação: {str(e)}")
                    return {"error": "Erro interno do servidor"}, 500

            return wrapper
        return decorator

    async def refresh_token(self, refresh_token: str) -> Optional[Dict]:
        """Atualiza um token de acesso usando um refresh token."""
        try:
            # Verificar refresh token
            payload = self.jwt_manager.verify_token(refresh_token)
            if not payload or payload.get('type') != 'refresh':
                return None

            # Criar novo access token
            new_access_token = self.jwt_manager.create_access_token({
                'user_id': payload['user_id'],
                'email': payload.get('email')
            })

            return {
                'access_token': new_access_token,
                'token_type': 'bearer'
            }
        except Exception as e:
            logger.error(f"Erro ao atualizar token: {str(e)}")
            return None

    def get_current_user(self, headers: Dict) -> Optional[Dict]:
        """Obtém o usuário atual a partir do token."""
        try:
            token = self._extract_token_from_header(headers)
            if not token:
                return None

            payload = self.jwt_manager.verify_token(token)
            if not payload or payload.get('type') != 'access':
                return None

            return {
                'user_id': payload['user_id'],
                'email': payload.get('email')
            }
        except Exception as e:
            logger.error(f"Erro ao obter usuário atual: {str(e)}")
            return None 