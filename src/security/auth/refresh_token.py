from datetime import datetime, timedelta
from typing import Optional, Dict
from supabase import create_client, Client
from loguru import logger
from src.config.settings import settings

class RefreshTokenManager:
    def __init__(self):
        self.supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        self.max_refresh_tokens = 5  # Número máximo de refresh tokens ativos por usuário

    async def store_refresh_token(self, user_id: str, token: str) -> bool:
        """Armazena um novo refresh token."""
        try:
            # Limpar tokens antigos se necessário
            await self._cleanup_old_tokens(user_id)

            # Armazenar novo token
            await self.supabase.table('refresh_tokens').insert({
                'user_id': user_id,
                'token': token,
                'created_at': datetime.utcnow().isoformat(),
                'is_valid': True
            }).execute()
            return True
        except Exception as e:
            logger.error(f"Erro ao armazenar refresh token para usuário {user_id}: {str(e)}")
            return False

    async def invalidate_refresh_token(self, token: str) -> bool:
        """Invalida um refresh token específico."""
        try:
            await self.supabase.table('refresh_tokens').update({
                'is_valid': False
            }).eq('token', token).execute()
            return True
        except Exception as e:
            logger.error(f"Erro ao invalidar refresh token: {str(e)}")
            return False

    async def invalidate_all_user_tokens(self, user_id: str) -> bool:
        """Invalida todos os refresh tokens de um usuário."""
        try:
            await self.supabase.table('refresh_tokens').update({
                'is_valid': False
            }).eq('user_id', user_id).execute()
            return True
        except Exception as e:
            logger.error(f"Erro ao invalidar todos os tokens do usuário {user_id}: {str(e)}")
            return False

    async def validate_refresh_token(self, token: str) -> Optional[str]:
        """Valida um refresh token e retorna o ID do usuário se válido."""
        try:
            response = await self.supabase.table('refresh_tokens').select('user_id').eq('token', token).eq('is_valid', True).execute()
            if response.data:
                return response.data[0]['user_id']
            return None
        except Exception as e:
            logger.error(f"Erro ao validar refresh token: {str(e)}")
            return None

    async def _cleanup_old_tokens(self, user_id: str):
        """Limpa tokens antigos do usuário, mantendo apenas o limite máximo."""
        try:
            # Obter tokens ativos do usuário
            response = await self.supabase.table('refresh_tokens').select('*').eq('user_id', user_id).eq('is_valid', True).order('created_at', desc=True).execute()
            
            # Se exceder o limite, invalidar os mais antigos
            if len(response.data) >= self.max_refresh_tokens:
                tokens_to_invalidate = response.data[self.max_refresh_tokens-1:]
                for token in tokens_to_invalidate:
                    await self.invalidate_refresh_token(token['token'])
        except Exception as e:
            logger.error(f"Erro ao limpar tokens antigos do usuário {user_id}: {str(e)}")

    async def cleanup_expired_tokens(self):
        """Limpa todos os tokens expirados do banco de dados."""
        try:
            expiry_date = (datetime.utcnow() - timedelta(days=7)).isoformat()
            await self.supabase.table('refresh_tokens').delete().lt('created_at', expiry_date).execute()
        except Exception as e:
            logger.error(f"Erro ao limpar tokens expirados: {str(e)}")

    async def get_active_tokens_count(self, user_id: str) -> int:
        """Retorna o número de tokens ativos para um usuário."""
        try:
            response = await self.supabase.table('refresh_tokens').select('*').eq('user_id', user_id).eq('is_valid', True).execute()
            return len(response.data)
        except Exception as e:
            logger.error(f"Erro ao contar tokens ativos do usuário {user_id}: {str(e)}")
            return 0 