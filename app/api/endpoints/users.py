"""
Endpoints de gerenciamento de usuários.
"""
from fastapi import APIRouter, HTTPException, status, Depends
from typing import List

from ...models.schemas import (
    UserCreate, 
    UserUpdate, 
    UserResponse, 
    MessageResponse
)
from ...services.user_service import user_service
from ...utils.dependencies import get_current_user, get_current_admin_user


router = APIRouter()


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    current_user: UserResponse = Depends(get_current_admin_user)
):
    """
    Cria um novo usuário.
    
    Requer permissão de administrador.
    
    Args:
        user_data: Dados do novo usuário
        current_user: Usuário autenticado (admin)
    
    Returns:
        Usuário criado
    
    Raises:
        HTTPException: Se o email já estiver cadastrado
    """
    try:
        user = await user_service.create_user(user_data)
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("", response_model=List[UserResponse])
async def list_users(
    current_user: UserResponse = Depends(get_current_admin_user)
):
    """
    Lista todos os usuários.
    
    Requer permissão de administrador.
    
    Args:
        current_user: Usuário autenticado (admin)
    
    Returns:
        Lista de usuários
    """
    users = await user_service.get_all_users()
    return users


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Obtém os detalhes de um usuário específico.
    
    Args:
        user_id: ID do usuário
        current_user: Usuário autenticado
    
    Returns:
        Dados do usuário
    
    Raises:
        HTTPException: Se o usuário não for encontrado
    """
    user = await user_service.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    current_user: UserResponse = Depends(get_current_admin_user)
):
    """
    Atualiza os dados de um usuário.
    
    Requer permissão de administrador.
    
    Args:
        user_id: ID do usuário
        user_data: Dados para atualização
        current_user: Usuário autenticado (admin)
    
    Returns:
        Usuário atualizado
    
    Raises:
        HTTPException: Se o usuário não for encontrado
    """
    user = await user_service.update_user(user_id, user_data)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    return user


@router.delete("/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: str,
    current_user: UserResponse = Depends(get_current_admin_user)
):
    """
    Remove um usuário.
    
    Requer permissão de administrador.
    
    Args:
        user_id: ID do usuário
        current_user: Usuário autenticado (admin)
    
    Returns:
        Mensagem de sucesso
    
    Raises:
        HTTPException: Se o usuário não for encontrado
    """
    success = await user_service.delete_user(user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    return MessageResponse(message="Usuário removido com sucesso")

