"""
Serviço de detecção de veículos de emergência.
"""
import cv2
import numpy as np
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime
import uuid
from pathlib import Path
import os
from ultralytics import YOLO
import tensorflow as tf
from collections import deque

from ..models.schemas import DetectionCreate, VehicleType, BoundingBox
from ..core.config import settings


class SirenDetector:
    """Detector de sirene baseado em CNN e análise de cores."""
    
    def __init__(self, model_path: str):
        """
        Inicializa o detector de sirene.
        
        Args:
            model_path: Caminho para o modelo CNN de detecção de sirene
        """
        try:
            self.model = tf.keras.models.load_model(model_path)
            print(f"✅ Modelo de sirene carregado com sucesso: {model_path}")
        except Exception as e:
            print(f"⚠️  Aviso: Não foi possível carregar modelo de sirene: {str(e)}")
            self.model = None
        
        self.historico_intensidade = {}
    
    def preprocessar_imagem(self, frame: np.ndarray) -> np.ndarray:
        """Pré-processa imagem para o modelo CNN."""
        if frame.size == 0:
            return np.zeros((1, 128, 128, 3))
        
        img = cv2.resize(frame, (128, 128))
        img = img.astype("float32") / 255.0
        img = np.expand_dims(img, axis=0)
        return img
    
    def detectar_sirene(self, frame: np.ndarray, box_id: int) -> bool:
        """
        Detecta a presença de uma sirene (vermelho + azul piscando) em uma área específica.
        
        Args:
            frame: Frame da imagem
            box_id: Identificador da área analisada
        
        Returns:
            True se detectar sirene, False caso contrário
        """
        if self.model is None:
            return False
        
        if frame.size == 0:
            return False
        
        try:
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            
            vermelho_mask1 = cv2.inRange(hsv, (0, 120, 150), (10, 255, 255))
            vermelho_mask2 = cv2.inRange(hsv, (170, 120, 150), (180, 255, 255))
            vermelho_mask = cv2.bitwise_or(vermelho_mask1, vermelho_mask2)
            
            azul_mask = cv2.inRange(hsv, (90, 100, 100), (130, 255, 255))
            
            intensidade = np.mean(vermelho_mask + azul_mask)
            
            if box_id not in self.historico_intensidade:
                self.historico_intensidade[box_id] = deque(maxlen=15)
            self.historico_intensidade[box_id].append(intensidade)
            
            if len(self.historico_intensidade[box_id]) >= 5:
                variacao = np.std(self.historico_intensidade[box_id])
                piscando = variacao > 25
            else:
                piscando = False
            
            img_pre = self.preprocessar_imagem(frame)
            pred = self.model.predict(img_pre, verbose=0)[0][0]
            
            rede_confirma = pred > 0.5
            
            return piscando and rede_confirma
            
        except Exception as e:
            print(f"Erro na detecção de sirene: {str(e)}")
            return False


class DetectionService:
    """Serviço para detecção de veículos de emergência usando YOLO."""
    
    def __init__(self):
        """Inicializa o serviço de detecção com o modelo YOLO."""
        self.model_path = "./models/best.pt"
        self.siren_model_path = "./models/sirene_cnn.h5" 
        
        self.model = self._load_model()
        self.siren_detector = SirenDetector(self.siren_model_path)
        
        self.class_mapping = {
            0: VehicleType.AMBULANCE,
            1: VehicleType.FIRE_TRUCK,
            2: VehicleType.POLICE_CAR,
        }
    
    def _load_model(self):
        """
        Carrega o modelo YOLO treinado.
        
        Returns:
            Modelo YOLO carregado
        
        Raises:
            FileNotFoundError: Se o modelo não for encontrado
        """
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Modelo não encontrado em: {self.model_path}")
        
        try:
            model = YOLO(self.model_path)
            print(f"✅ Modelo YOLO carregado com sucesso: {self.model_path}")
            return model
        except Exception as e:
            raise RuntimeError(f"Erro ao carregar modelo: {str(e)}")
    
    async def detect_in_image(
        self, 
        image_path: str, 
        source_id: str,
        user_id: str
    ) -> List[DetectionCreate]:
        """
        Detecta veículos de emergência em uma imagem usando YOLO.
        
        Args:
            image_path: Caminho para a imagem
            source_id: ID da fonte (câmera ou arquivo)
        
        Returns:
            Lista de detecções encontradas com bounding boxes e confiança
        """
        if not os.path.exists(image_path):
            raise ValueError(f"Imagem não encontrada: {image_path}")
        
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Não foi possível carregar a imagem: {image_path}")
        
        results = self.model(image)
        
        detections = []
        
        for r in results:

            boxes = r.boxes
            if boxes is not None:
                for i, box in enumerate(boxes):

                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    confidence = box.conf[0].cpu().numpy()
                    class_id = int(box.cls[0].cpu().numpy())
                    
                    vehicle_type = self.class_mapping.get(
                        class_id, 
                        VehicleType.AMBULANCE
                    )
                    
                    bbox = BoundingBox(
                        x=int(x1),
                        y=int(y1),
                        w=int(x2 - x1),
                        h=int(y2 - y1)
                    )

                    x1_int, y1_int, x2_int, y2_int = int(x1), int(y1), int(x2), int(y2)
                    vehicle_region = image[y1_int:y2_int, x1_int:x2_int]
                    
                    siren_on = False
                    if vehicle_region.size > 0:
                        siren_on = self.siren_detector.detectar_sirene(vehicle_region, i)
                    
                    detection = DetectionCreate(
                        source_id=source_id,
                        vehicle_type=vehicle_type,
                        siren_on=siren_on,
                        bounding_box=bbox,
                        confidence_score=float(confidence),
                        media_reference=image_path,
                        user_id=user_id,
                        timestamp=datetime.utcnow()
                    )
                    detections.append(detection)
        
        return detections
    
    def generate_annotated_image(
        self, 
        image_path: str, 
        output_path: str = None
    ) -> str:
        """
        Gera uma imagem anotada com as detecções.
        
        Args:
            image_path: Caminho para a imagem original
            output_path: Caminho para salvar a imagem anotada (opcional)
        
        Returns:
            Caminho da imagem anotada
        """
        if not os.path.exists(image_path):
            raise ValueError(f"Imagem não encontrada: {image_path}")

        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Não foi possível carregar a imagem: {image_path}")

        results = self.model(image)
        
        annotated_image = image.copy()
        
        for r in results:
            boxes = r.boxes
            if boxes is not None:
                for i, box in enumerate(boxes):
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    confidence = box.conf[0].cpu().numpy()
                    class_id = int(box.cls[0].cpu().numpy())
                    
                    x1_int, y1_int, x2_int, y2_int = int(x1), int(y1), int(x2), int(y2)
                    vehicle_region = image[y1_int:y2_int, x1_int:x2_int]
                    
                    siren_on = False
                    if vehicle_region.size > 0:
                        siren_on = self.siren_detector.detectar_sirene(vehicle_region, i)
                    
                    if siren_on:
                        color = (0, 255, 0) 
                        status_text = "EM OPERACAO"
                    else:
                        color = (0, 0, 255)  
                        status_text = "FORA DE OPERACAO"
                    
                    cv2.rectangle(annotated_image, (x1_int, y1_int), (x2_int, y2_int), color, 2)
                    
                    vehicle_type = self.class_mapping.get(class_id, "VEICULO")
                    label = f"{vehicle_type} {status_text} {confidence:.2f}"
                    
                    (text_width, text_height), baseline = cv2.getTextSize(
                        label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
                    )
                    cv2.rectangle(
                        annotated_image,
                        (x1_int, y1_int - text_height - 10),
                        (x1_int + text_width, y1_int),
                        color,
                        -1
                    )
                    
                    cv2.putText(
                        annotated_image,
                        label,
                        (x1_int, y1_int - 5),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (255, 255, 255),
                        2
                    )
        
        if output_path is None:
            output_dir = Path(image_path).parent / "annotated"
            output_dir.mkdir(exist_ok=True)
            original_name = Path(image_path).stem
            output_path = output_dir / f"annotated_{original_name}.jpg"
        
        output_path_str = str(output_path).replace("\\", "/")
        
        cv2.imwrite(str(output_path_str), annotated_image)
        
        return str(output_path)
    
    async def detect_in_video(
        self, 
        video_path: str, 
        source_id: str,
        job_id: str,
        user_id: str 
    ) -> Tuple[List[DetectionCreate], str]:
        """
        Detecta veículos de emergência em um vídeo e gera vídeo anotado.
        
        Args:
            video_path: Caminho para o vídeo
            source_id: ID da fonte
            job_id: ID do job de processamento
            user_id: ID do usuário
        
        Returns:
            Tuple: (Lista de detecções encontradas, caminho do vídeo anotado)
        """
        if not os.path.exists(video_path):
            raise ValueError(f"Vídeo não encontrado: {video_path}")
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Não foi possível abrir o vídeo: {video_path}")
        
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        
        output_dir = Path(video_path).parent / "annotated"
        output_dir.mkdir(exist_ok=True)
        original_name = Path(video_path).stem
        annotated_video_path = output_dir / f"annotated_{original_name}.mp4"
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(str(annotated_video_path), fourcc, fps, (frame_width, frame_height))
        
        best_detections = {}
        frame_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            results = self.model(frame)
            annotated_frame = frame.copy()
            
            for r in results:
                boxes = r.boxes
                if boxes is not None:
                    for i, box in enumerate(boxes):
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        confidence = box.conf[0].cpu().numpy()
                        class_id = int(box.cls[0].cpu().numpy())
                        
                        x1_int, y1_int, x2_int, y2_int = int(x1), int(y1), int(x2), int(y2)
                        vehicle_region = frame[y1_int:y2_int, x1_int:x2_int]
                        
                        siren_on = False
                        if vehicle_region.size > 0:
                            siren_on = self.siren_detector.detectar_sirene(vehicle_region, i)
                        
                        if siren_on:
                            color = (0, 255, 0) 
                            status_text = "EM OPERACAO"
                        else:
                            color = (0, 0, 255)  
                            status_text = "FORA DE OPERACAO"
                        
                        cv2.rectangle(annotated_frame, (x1_int, y1_int), (x2_int, y2_int), color, 2)
                        
                        vehicle_type = self.class_mapping.get(class_id, "VEICULO")
                        label = f"{vehicle_type} {status_text} {confidence:.2f}"
                        
                        (text_width, text_height), baseline = cv2.getTextSize(
                            label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
                        )
                        cv2.rectangle(
                            annotated_frame,
                            (x1_int, y1_int - text_height - 10),
                            (x1_int + text_width, y1_int),
                            color,
                            -1
                        )
                        
                        cv2.putText(
                            annotated_frame,
                            label,
                            (x1_int, y1_int - 5),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.6,
                            (255, 255, 255),
                            2
                        )
                        
                        if frame_count % 30 == 0:
                            vehicle_type_enum = self.class_mapping.get(class_id, VehicleType.AMBULANCE)
                            position_key = f"{vehicle_type_enum.value}_{x1_int//100}_{y1_int//100}"
                            
                            if position_key not in best_detections:
                                frame_path = self._save_frame(frame, job_id, frame_count)
                                
                                detection = DetectionCreate(
                                    source_id=source_id,
                                    vehicle_type=vehicle_type_enum,
                                    siren_on=siren_on,
                                    bounding_box=BoundingBox(
                                        x=int(x1),
                                        y=int(y1),
                                        w=int(x2 - x1),
                                        h=int(y2 - y1)
                                    ),
                                    confidence_score=float(confidence),
                                    media_reference=frame_path,
                                    user_id=user_id,
                                    timestamp=datetime.utcnow()
                                )
                                best_detections[position_key] = detection
                            else:
                                if float(confidence) > best_detections[position_key].confidence_score:
                                    frame_path = self._save_frame(frame, job_id, frame_count)
                                    
                                    detection = DetectionCreate(
                                        source_id=source_id,
                                        vehicle_type=vehicle_type_enum,
                                        siren_on=siren_on,
                                        bounding_box=BoundingBox(
                                            x=int(x1),
                                            y=int(y1),
                                            w=int(x2 - x1),
                                            h=int(y2 - y1)
                                        ),
                                        confidence_score=float(confidence),
                                        media_reference=frame_path,
                                        user_id=user_id,
                                        timestamp=datetime.utcnow()
                                    )
                                    best_detections[position_key] = detection
            
            out.write(annotated_frame)
            frame_count += 1
        
        cap.release()
        out.release()
        
        final_detections = list(best_detections.values())
        
        print(f"✅ Processamento de vídeo concluído. Encontrados {len(final_detections)} veículos únicos.")
        
        return final_detections, str(annotated_video_path)
    
    def _save_frame(self, frame: np.ndarray, job_id: str, frame_number: int) -> str:
        """Salva um frame do vídeo."""
        upload_dir = Path(settings.UPLOAD_DIR) / "frames" / job_id
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        frame_path = upload_dir / f"frame_{frame_number:06d}.jpg"
        cv2.imwrite(str(frame_path), frame)
        
        return str(frame_path)

detection_service = DetectionService()