from datetime import datetime, timedelta
import jwt
from typing import Dict, Optional
from loguru import logger
from config.settings import settings

class JWTManager:
    def __init__(self):
        self.secret_key = settings.JWT_SECRET_KEY
        self.algorithm = "HS256"
        self.access_token_expire = timedelta(minutes=15)
        self.refresh_token_expire = timedelta(days=7)

    def create_access_token(self, data: Dict) -> str:
        """Cria um token de acesso JWT."""
        try:
            to_encode = data.copy()
            expire = datetime.utcnow() + self.access_token_expire
            to_encode.update({
                "exp": expire,
                "type": "access"
            })
            return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        except Exception as e:
            logger.error(f"Erro ao criar access token: {str(e)}")
            raise

    def create_refresh_token(self, data: Dict) -> str:
        """Cria um refresh token JWT."""
        try:
            to_encode = data.copy()
            expire = datetime.utcnow() + self.refresh_token_expire
            to_encode.update({
                "exp": expire,
                "type": "refresh"
            })
            return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        except Exception as e:
            logger.error(f"Erro ao criar refresh token: {str(e)}")
            raise

    def verify_token(self, token: str) -> Optional[Dict]:
        """Verifica e decodifica um token JWT."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token expirado")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Token inválido: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Erro ao verificar token: {str(e)}")
            return None

    def is_token_expired(self, token: str) -> bool:
        """Verifica se um token está expirado."""
        try:
            payload = self.verify_token(token)
            if not payload:
                return True
            exp = payload.get("exp")
            if not exp:
                return True
            return datetime.utcnow().timestamp() > exp
        except Exception as e:
            logger.error(f"Erro ao verificar expiração do token: {str(e)}")
            return True 