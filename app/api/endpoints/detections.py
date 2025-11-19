"""
Endpoints de detecção de veículos de emergência.
"""
from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse
from typing import List
from pathlib import Path
import uuid
from datetime import datetime
from bson import ObjectId
import os

from ...models.schemas import (
    DetectionResponse,
    JobResponse,
    JobStatus,
    UserResponse
)
from ...services.detection_service import detection_service
from ...utils.dependencies import get_current_user
from ...core.database import get_db
from ...core.config import settings


router = APIRouter()


@router.post("/image", response_model=List[DetectionResponse])
async def detect_in_image(
    file: UploadFile = File(...),
    source_id: str = "uploaded_image",
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Processa uma imagem para detectar veículos de emergência.
    
    Retorna as detecções com bounding boxes, tipos de veículos e confiança.
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo deve ser uma imagem"
        )
    
    upload_dir = Path(settings.UPLOAD_DIR) / "images"
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    file_extension = Path(file.filename).suffix
    file_path = upload_dir / f"{uuid.uuid4()}{file_extension}"
    
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    try:
        detections = await detection_service.detect_in_image(str(file_path), source_id, current_user.id)
        
        annotated_image_path = detection_service.generate_annotated_image(str(file_path))

        db = get_db()
        detection_responses = []
        
        for detection in detections:
            detection_dict = detection.model_dump()
            detection_dict["user_id"] = current_user.id
            detection_dict["timestamp"] = datetime.utcnow()
            detection_dict["annotated_image_path"] = annotated_image_path
            detection_dict["user_id"] = current_user.id
            detection_dict["processed_at"] = datetime.utcnow()
            detection_dict["annotated_image_path"] = annotated_image_path
            
            result = await db["detections"].insert_one(detection_dict)
            
            # Busca a detecção criada
            created_detection = await db["detections"].find_one({"_id": result.inserted_id})
            created_detection["_id"] = str(created_detection["_id"])
            
            detection_responses.append(DetectionResponse(**created_detection))
        
        return detection_responses
    
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Modelo de detecção não encontrado: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao processar imagem: {str(e)}"
        )


@router.get("/image/annotated/{detection_id}")
async def get_annotated_image(
    detection_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Retorna a imagem anotada com as detecções.
    
    Args:
        detection_id: ID da detecção
        current_user: Usuário autenticado
    
    Returns:
        Imagem anotada com bounding boxes
    """
    db = get_db()
    
    detection = await db["detections"].find_one({"_id": ObjectId(detection_id)})
    if not detection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Detecção não encontrada"
        )
    
    annotated_path = detection.get("annotated_image_path")
    if not annotated_path or not os.path.exists(annotated_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Imagem anotada não encontrada"
        )
    
    return FileResponse(
        annotated_path,
        media_type="image/jpeg",
        filename=f"annotated_{Path(annotated_path).name}"
    )


async def process_video_task(video_path: str, source_id: str, job_id: str, user_id: str):
    """Tarefa em background para processar vídeo."""
    db = get_db()
    
    try:
        await db["detection_jobs"].update_one(
            {"job_id": job_id},
            {"$set": {"status": JobStatus.PROCESSING.value}}
        )
        
        detections, annotated_video_path = await detection_service.detect_in_video(
            video_path, source_id, job_id, user_id
        )
        
        if annotated_video_path:
            annotated_video_path = annotated_video_path.replace('\\', '/')

        detection_ids = []
        
        for detection in detections:
            detection_dict = detection.model_dump()
            detection_dict["timestamp"] = datetime.utcnow()
            detection_dict["processed_at"] = datetime.utcnow()
            
            result = await db["detections"].insert_one(detection_dict)
            detection_ids.append(str(result.inserted_id))
        
        await db["detection_jobs"].update_one(
            {"job_id": job_id},
            {
                "$set": {
                    "status": JobStatus.COMPLETED.value,
                    "completed_at": datetime.utcnow(),
                    "results": detection_ids,
                    "annotated_video_path": annotated_video_path
                }
            }
        )
        
        print(f"✅ Processamento de vídeo concluído. Salvas {len(detection_ids)} melhores detecções.")
    
    except Exception as e:
        # Atualiza o job como falho
        await db["detection_jobs"].update_one(
            {"job_id": job_id},
            {
                "$set": {
                    "status": JobStatus.FAILED.value,
                    "completed_at": datetime.utcnow(),
                    "error_message": str(e)
                }
            }
        )
        print(f"❌ Erro no processamento de vídeo: {str(e)}")


@router.post("/video", response_model=JobResponse)
async def detect_in_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    source_id: str = "uploaded_video",
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Processa um vídeo para detectar veículos de emergência.
    
    O processamento é feito em background. Use o endpoint GET /video/{job_id}
    para verificar o status.
    """
    if not file.content_type.startswith("video/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo deve ser um vídeo"
        )

    upload_dir = Path(settings.UPLOAD_DIR) / "videos"
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    file_extension = Path(file.filename).suffix
    file_path = upload_dir / f"{uuid.uuid4()}{file_extension}"
    
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    # Cria o job
    db = get_db()
    job_id = str(uuid.uuid4())
    
    job_dict = {
        "job_id": job_id,
        "original_filename": file.filename,
        "status": JobStatus.PENDING.value,
        "created_at": datetime.utcnow(),
        "completed_at": None,
        "results": [],
        "annotated_video_path": None,
        "user_id": current_user.id
    }
    
    result = await db["detection_jobs"].insert_one(job_dict)
    
    background_tasks.add_task(process_video_task, str(file_path), source_id, job_id, current_user.id)

    created_job = await db["detection_jobs"].find_one({"_id": result.inserted_id})
    created_job["_id"] = str(created_job["_id"])
    
    return JobResponse(**created_job)


@router.get("/video/{job_id}", response_model=JobResponse)
async def get_video_job_status(
    job_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Verifica o status do processamento de um vídeo.
    """
    db = get_db()
    
    job = await db["detection_jobs"].find_one({"job_id": job_id})
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job não encontrado"
        )
    
    job["_id"] = str(job["_id"])
    
    return JobResponse(**job)


@router.get("/video/annotated/{job_id}")
async def get_annotated_video(
    job_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Retorna o vídeo anotado com as detecções.
    
    Args:
        job_id: ID do job de processing
        current_user: Usuário autenticado
    
    Returns:
        Vídeo anotado com bounding boxes e status das sirenes
    """
    db = get_db()
    
    job = await db["detection_jobs"].find_one({"job_id": job_id})
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job não encontrado"
        )

    if job.get("status") != JobStatus.COMPLETED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vídeo ainda não foi processado completamente"
        )
    
    annotated_path = job.get("annotated_video_path")
    if not annotated_path or not os.path.exists(annotated_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vídeo anotado não encontrado"
        )
    
    return FileResponse(
        annotated_path,
        media_type="video/mp4",
        filename=f"annotated_{Path(annotated_path).name}"
    )

@router.get("/jobs", response_model=List[JobResponse])
async def list_detection_jobs(
    current_user: UserResponse = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100
):
    """
    Lista todos os jobs de detecção do usuário.
    """
    db = get_db()

    jobs = await db["detection_jobs"].find(
        {"user_id": current_user.id}
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(length=limit)

    for job in jobs:
        job["_id"] = str(job["_id"])
    
    return jobs