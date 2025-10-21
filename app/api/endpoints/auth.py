"""
Endpoints de autenticação.
"""
from fastapi import APIRouter, HTTPException, status
from datetime import timedelta

from ...models.schemas import LoginRequest, TokenResponse
from ...services.user_service import user_service
from ...core.security import create_access_token
from ...core.config import settings


router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(login_data: LoginRequest):
    """
    Autentica um usuário e retorna um token de acesso.
    
    Args:
        login_data: Dados de login (email e senha)
    
    Returns:
        Token de acesso JWT
    
    Raises:
        HTTPException: Se as credenciais forem inválidas
    """
    user = await user_service.authenticate_user(login_data.email, login_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user["_id"])},
        expires_delta=access_token_expires
    )
    
    return TokenResponse(access_token=access_token)


@router.post("/logout")
async def logout():
    return {"message": "Logout realizado com sucesso"}

