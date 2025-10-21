"""
Serviço de gerenciamento de usuários.
"""
from typing import Optional, List
from datetime import datetime
from bson import ObjectId

from ..models.schemas import UserCreate, UserUpdate, UserResponse
from ..core.security import get_password_hash, verify_password
from ..core.database import get_db


class UserService:
    """Serviço para gerenciamento de usuários."""
    
    def __init__(self):
        """Inicializa o serviço de usuários."""
        self.collection_name = "users"
    
    async def create_user(self, user_data: UserCreate) -> UserResponse:
        """Cria um novo usuário."""
        db = get_db()
        
        existing_user = await db[self.collection_name].find_one({"email": user_data.email})
        if existing_user:
            raise ValueError("Email já cadastrado")
        
        user_dict = user_data.model_dump()
        user_dict["password"] = get_password_hash(user_data.password)
        user_dict["created_at"] = datetime.utcnow()
        user_dict["updated_at"] = datetime.utcnow()
        
        result = await db[self.collection_name].insert_one(user_dict)
        
        created_user = await db[self.collection_name].find_one({"_id": result.inserted_id})
        
        return self._user_to_response(created_user)
    
    async def get_user_by_id(self, user_id: str) -> Optional[UserResponse]:
        """Busca um usuário por ID."""
        db = get_db()
        
        try:
            user = await db[self.collection_name].find_one({"_id": ObjectId(user_id)})
        except Exception:
            return None
        
        if user:
            return self._user_to_response(user)
        
        return None
    
    async def get_user_by_email(self, email: str) -> Optional[dict]:
        """Busca um usuário por email (retorna dict completo com senha)."""
        db = get_db()
        user = await db[self.collection_name].find_one({"email": email})
        return user
    
    async def get_all_users(self) -> List[UserResponse]:
        """Lista todos os usuários."""
        db = get_db()
        
        users = []
        cursor = db[self.collection_name].find()
        
        async for user in cursor:
            users.append(self._user_to_response(user))
        
        return users
    
    async def update_user(self, user_id: str, user_data: UserUpdate) -> Optional[UserResponse]:
        """Atualiza um usuário."""
        db = get_db()
        
        update_dict = user_data.model_dump(exclude_unset=True)
        
        if not update_dict:
            return await self.get_user_by_id(user_id)
        
        if "password" in update_dict:
            update_dict["password"] = get_password_hash(update_dict["password"])
        
        update_dict["updated_at"] = datetime.utcnow()
        
        try:
            result = await db[self.collection_name].update_one(
                {"_id": ObjectId(user_id)},
                {"$set": update_dict}
            )
        except Exception:
            return None
        
        if result.modified_count == 0:
            return None
        
        return await self.get_user_by_id(user_id)
    
    async def delete_user(self, user_id: str) -> bool:
        """Remove um usuário."""
        db = get_db()
        
        try:
            result = await db[self.collection_name].delete_one({"_id": ObjectId(user_id)})
        except Exception:
            return False
        
        return result.deleted_count > 0
    
    async def authenticate_user(self, email: str, password: str) -> Optional[dict]:
        """Autentica um usuário."""
        user = await self.get_user_by_email(email)
        
        if not user:
            return None
        
        if not verify_password(password, user["password"]):
            return None
        
        return user
    
    def _user_to_response(self, user: dict) -> UserResponse:
        """Converte um documento de usuário para UserResponse."""
        user["_id"] = str(user["_id"])
        return UserResponse(**user)


user_service = UserService()

