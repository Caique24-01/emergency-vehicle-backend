"""
Script para criar o primeiro usuário administrador.
"""
import asyncio
from app.core.database import Database
from app.services.user_service import user_service
from app.models.schemas import UserCreate, UserRole


async def create_admin():
    """Cria um usuário administrador."""
    # Conecta ao banco
    await Database.connect_db()
    
    try:
        # Dados do administrador
        admin_data = UserCreate(
            name="Administrador",
            email="admin@example.com",
            password="admin123",
            role=UserRole.ADMIN
        )
        
        # Cria o usuário
        user = await user_service.create_user(admin_data)
        
        print("✓ Usuário administrador criado com sucesso!")
        print(f"  Email: {user.email}")
        print(f"  Nome: {user.name}")
        print(f"  Role: {user.role}")
        print(f"\n⚠️  IMPORTANTE: Altere a senha padrão após o primeiro login!")
    
    except ValueError as e:
        print(f"✗ Erro: {e}")
    
    finally:
        # Fecha a conexão
        await Database.close_db()


if __name__ == "__main__":
    asyncio.run(create_admin())

