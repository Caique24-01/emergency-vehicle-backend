"""
Endpoints de relatórios.
"""
from fastapi import APIRouter, Depends, Query
from datetime import datetime
from typing import Optional

from ...models.schemas import (
    DetectionStats,
    VehicleType,
    UserResponse
)
from ...services.report_service import report_service
from ...utils.dependencies import get_current_user


router = APIRouter()


@router.get("/traffic")
async def get_traffic_report(
    start_date: datetime = Query(..., description="Data inicial do relatório"),
    end_date: datetime = Query(..., description="Data final do relatório"),
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Gera um relatório de tráfego.
    
    Args:
        start_date: Data inicial
        end_date: Data final
        current_user: Usuário autenticado
    
    Returns:
        Relatório de tráfego com detecções agrupadas por hora
    """
    report = await report_service.get_traffic_report(start_date, end_date)
    return report


@router.get("/detections", response_model=DetectionStats)
async def get_detection_report(
    start_date: datetime = Query(..., description="Data inicial do relatório"),
    end_date: datetime = Query(..., description="Data final do relatório"),
    vehicle_type: Optional[VehicleType] = Query(None, description="Tipo de veículo (opcional)"),
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Gera um relatório de detecções com estatísticas.
    
    Args:
        start_date: Data inicial
        end_date: Data final
        vehicle_type: Tipo de veículo (opcional)
        current_user: Usuário autenticado
    
    Returns:
        Estatísticas de detecção
    """
    stats = await report_service.get_detection_stats(start_date, end_date, vehicle_type)
    return stats


@router.get("/confidence")
async def get_confidence_report(
    start_date: datetime = Query(..., description="Data inicial do relatório"),
    end_date: datetime = Query(..., description="Data final do relatório"),
    vehicle_type: Optional[VehicleType] = Query(None, description="Tipo de veículo (opcional)"),
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Gera um relatório de confiabilidade das detecções.
    
    Args:
        start_date: Data inicial
        end_date: Data final
        vehicle_type: Tipo de veículo (opcional)
        current_user: Usuário autenticado
    
    Returns:
        Relatório de confiabilidade com distribuição de scores
    """
    report = await report_service.get_confidence_report(start_date, end_date, vehicle_type)
    return report