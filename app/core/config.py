"""
Configurações do projeto.
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Configurações da aplicação."""
    
    MONGODB_URL: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "emergency_vehicle_db"
    
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Emergency Vehicle Detection API"
    
    # Configurações dos Modelos
    VEHICLE_MODEL_PATH: str = "./models/vehicle_detector.pt"
    SIREN_MODEL_PATH: str = "./models/siren_detector.pt"
    
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 104857600  # 100MB em bytes
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

