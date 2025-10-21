"""
Aplicação principal da API.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .core.config import settings
from .core.database import Database
from .api.endpoints import auth, users, detections, reports


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia o ciclo de vida da aplicação."""

    await Database.connect_db()
    yield

    await Database.close_db()


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    auth.router,
    prefix=f"{settings.API_V1_STR}/auth",
    tags=["Autenticação"]
)

app.include_router(
    users.router,
    prefix=f"{settings.API_V1_STR}/employees",
    tags=["Funcionários"]
)

app.include_router(
    detections.router,
    prefix=f"{settings.API_V1_STR}/detections",
    tags=["Detecções"]
)

app.include_router(
    reports.router,
    prefix=f"{settings.API_V1_STR}/reports",
    tags=["Relatórios"]
)


@app.get("/")
async def root():
    """Endpoint raiz da API."""
    return {
        "message": "Emergency Vehicle Detection API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Verifica o status da API."""
    return {
        "status": "healthy",
        "database": "connected"
    }

