"""
Schemas Pydantic para validação de dados.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


# ===== Enums =====

class UserRole(str, Enum):
    """Papéis de usuário."""
    ADMIN = "admin"
    OPERATOR = "operator"


class VehicleType(str, Enum):
    """Tipos de veículos de emergência."""
    AMBULANCE = "ambulance"
    POLICE_CAR = "police_car"
    FIRE_TRUCK = "fire_truck"
    TRAFFIC_ENFORCEMENT = "traffic_enforcement"


class JobStatus(str, Enum):
    """Status de processamento de vídeo."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# ===== Schemas de Usuário =====

class UserBase(BaseModel):
    """Schema base de usuário."""
    name: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    role: UserRole = UserRole.OPERATOR


class UserCreate(UserBase):
    """Schema para criação de usuário."""
    password: str = Field(..., min_length=6)


class UserUpdate(BaseModel):
    """Schema para atualização de usuário."""
    name: Optional[str] = Field(None, min_length=3, max_length=100)
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    password: Optional[str] = Field(None, min_length=6)


class UserResponse(UserBase):
    """Schema de resposta de usuário."""
    id: str = Field(..., alias="_id")
    created_at: datetime
    updated_at: datetime
    
    class Config:
        populate_by_name = True


# ===== Schemas de Autenticação =====

class LoginRequest(BaseModel):
    """Schema para requisição de login."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Schema de resposta de token."""
    access_token: str
    token_type: str = "bearer"


# ===== Schemas de Detecção =====

class BoundingBox(BaseModel):
    """Coordenadas da caixa delimitadora."""
    x: int
    y: int
    w: int
    h: int


class Location(BaseModel):
    """Localização geográfica."""
    type: str = "Point"
    coordinates: List[float] = Field(..., min_length=2, max_length=2)  # [longitude, latitude]


class DetectionBase(BaseModel):
    """Schema base de detecção."""
    source_id: str
    vehicle_type: VehicleType
    siren_on: bool
    bounding_box: BoundingBox
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    location: Optional[Location] = None


class DetectionCreate(DetectionBase):
    """Schema para criação de detecção."""
    media_reference: str
    user_id: str


class DetectionResponse(DetectionBase):
    """Schema de resposta de detecção."""
    id: str = Field(..., alias="_id")
    timestamp: datetime
    media_reference: str
    processed_at: datetime
    user_id: str
    annotated_image_path: Optional[str] = None 
    
    class Config:
        populate_by_name = True


# ===== Schemas de Job de Processamento =====

class JobCreate(BaseModel):
    """Schema para criação de job."""
    original_filename: str


class JobResponse(BaseModel):
    """Schema de resposta de job."""
    id: str = Field(..., alias="_id")
    job_id: str
    original_filename: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    results: List[str] = []
    annotated_video_path: Optional[str] = None
    error_message: Optional[str] = None
    user_id: str
    
    class Config:
        populate_by_name = True


# ===== Schemas de Relatórios =====

class TrafficReportQuery(BaseModel):
    """Parâmetros para relatório de tráfego."""
    start_date: datetime
    end_date: datetime


class DetectionReportQuery(BaseModel):
    """Parâmetros para relatório de detecções."""
    start_date: datetime
    end_date: datetime
    vehicle_type: Optional[VehicleType] = None


class DetectionStats(BaseModel):
    """Estatísticas de detecção."""
    total_detections: int
    detections_by_type: dict
    detections_with_siren: int
    average_confidence: float


# ===== Schemas de Resposta Genérica =====

class MessageResponse(BaseModel):
    """Schema de resposta genérica com mensagem."""
    message: str

