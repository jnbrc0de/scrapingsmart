from typing import List, Dict, Optional
from supabase import create_client, Client
from loguru import logger
from config.settings import settings
from datetime import datetime, timedelta

class RoleManager:
    def __init__(self):
        self.supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        self.role_cache: Dict[str, Dict] = {}
        self.cache_expiry: Dict[str, datetime] = {}
        self.cache_duration = timedelta(minutes=30)

    async def get_user_roles(self, user_id: str) -> List[str]:
        """Obtém as roles de um usuário, usando cache quando possível."""
        try:
            # Verificar cache
            if self._is_cache_valid(user_id):
                return self.role_cache[user_id]["roles"]

            # Buscar roles do banco
            response = await self.supabase.table('user_roles').select('role').eq('user_id', user_id).execute()
            roles = [role['role'] for role in response.data]
            
            # Atualizar cache
            self._update_cache(user_id, roles)
            return roles
        except Exception as e:
            logger.error(f"Erro ao obter roles do usuário {user_id}: {str(e)}")
            return []

    def has_required_roles(self, user_id: str, required_roles: List[str]) -> bool:
        """Verifica se um usuário possui todas as roles necessárias."""
        try:
            user_roles = self.get_user_roles(user_id)
            return all(role in user_roles for role in required_roles)
        except Exception as e:
            logger.error(f"Erro ao verificar roles do usuário {user_id}: {str(e)}")
            return False

    def _is_cache_valid(self, user_id: str) -> bool:
        """Verifica se o cache para um usuário ainda é válido."""
        if user_id not in self.role_cache or user_id not in self.cache_expiry:
            return False
        return datetime.utcnow() < self.cache_expiry[user_id]

    def _update_cache(self, user_id: str, roles: List[str]):
        """Atualiza o cache de roles para um usuário."""
        self.role_cache[user_id] = {"roles": roles}
        self.cache_expiry[user_id] = datetime.utcnow() + self.cache_duration

    async def add_role_to_user(self, user_id: str, role: str) -> bool:
        """Adiciona uma role a um usuário."""
        try:
            await self.supabase.table('user_roles').insert({
                'user_id': user_id,
                'role': role
            }).execute()
            # Invalidar cache
            if user_id in self.role_cache:
                del self.role_cache[user_id]
            return True
        except Exception as e:
            logger.error(f"Erro ao adicionar role {role} ao usuário {user_id}: {str(e)}")
            return False

    async def remove_role_from_user(self, user_id: str, role: str) -> bool:
        """Remove uma role de um usuário."""
        try:
            await self.supabase.table('user_roles').delete().eq('user_id', user_id).eq('role', role).execute()
            # Invalidar cache
            if user_id in self.role_cache:
                del self.role_cache[user_id]
            return True
        except Exception as e:
            logger.error(f"Erro ao remover role {role} do usuário {user_id}: {str(e)}")
            return False 