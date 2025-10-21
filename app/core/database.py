"""
Conexão com o banco de dados MongoDB.
"""
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
from .config import settings


class Database:
    """Gerenciador de conexão com o MongoDB."""
    
    client: Optional[AsyncIOMotorClient] = None
    
    @classmethod
    async def connect_db(cls):
        """Conecta ao banco de dados."""
        cls.client = AsyncIOMotorClient(settings.MONGODB_URL)
        print(f"Conectado ao MongoDB em {settings.MONGODB_URL}")
    
    @classmethod
    async def close_db(cls):
        """Fecha a conexão com o banco de dados."""
        if cls.client:
            cls.client.close()
            print("Conexão com MongoDB fechada")
    
    @classmethod
    def get_database(cls):
        """Retorna a instância do banco de dados."""
        if cls.client is None:
            raise Exception("Banco de dados não conectado. Chame connect_db() primeiro.")
        return cls.client[settings.DATABASE_NAME]


def get_db():
    """Dependency para obter a instância do banco de dados."""
    return Database.get_database()

