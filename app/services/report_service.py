"""
Serviço de geração de relatórios.
"""
from typing import Optional
from datetime import datetime

from ..models.schemas import DetectionStats, VehicleType
from ..core.database import get_db


class ReportService:
    """Serviço para geração de relatórios."""
    
    def __init__(self):
        """Inicializa o serviço de relatórios."""
        self.collection_name = "detections"
    
    async def get_detection_stats(
        self,
        start_date: datetime,
        end_date: datetime,
        vehicle_type: Optional[VehicleType] = None
    ) -> DetectionStats:
        """
        Gera estatísticas de detecções.
        
        Args:
            start_date: Data inicial
            end_date: Data final
            vehicle_type: Tipo de veículo (opcional)
        
        Returns:
            Estatísticas de detecção
        """
        db = get_db()
        
        match_filter = {
            "timestamp": {
                "$gte": start_date,
                "$lte": end_date
            }
        }
        
        if vehicle_type:
            match_filter["vehicle_type"] = vehicle_type.value
        
        pipeline = [
            {"$match": match_filter},
            {
                "$group": {
                    "_id": None,
                    "total_detections": {"$sum": 1},
                    "detections_with_siren": {
                        "$sum": {"$cond": ["$siren_on", 1, 0]}
                    },
                    "average_confidence": {"$avg": "$confidence_score"},
                    "detections_by_type": {
                        "$push": "$vehicle_type"
                    }
                }
            }
        ]
        
        result = await db[self.collection_name].aggregate(pipeline).to_list(length=1)
        
        if not result:
            return DetectionStats(
                total_detections=0,
                detections_by_type={},
                detections_with_siren=0,
                average_confidence=0.0
            )
        
        stats = result[0]
        
        detections_by_type = {}
        for vtype in stats.get("detections_by_type", []):
            detections_by_type[vtype] = detections_by_type.get(vtype, 0) + 1
        
        return DetectionStats(
            total_detections=stats.get("total_detections", 0),
            detections_by_type=detections_by_type,
            detections_with_siren=stats.get("detections_with_siren", 0),
            average_confidence=round(stats.get("average_confidence", 0.0), 4)
        )
    
    async def get_traffic_report(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> dict:
        """
        Gera relatório de tráfego.
        
        Args:
            start_date: Data inicial
            end_date: Data final
        
        Returns:
            Relatório de tráfego
        """
        db = get_db()
        
        pipeline = [
            {
                "$match": {
                    "timestamp": {
                        "$gte": start_date,
                        "$lte": end_date
                    }
                }
            },
            {
                "$group": {
                    "_id": {
                        "year": {"$year": "$timestamp"},
                        "month": {"$month": "$timestamp"},
                        "day": {"$dayOfMonth": "$timestamp"},
                        "hour": {"$hour": "$timestamp"}
                    },
                    "count": {"$sum": 1},
                    "with_siren": {
                        "$sum": {"$cond": ["$siren_on", 1, 0]}
                    }
                }
            },
            {
                "$sort": {
                    "_id.year": 1,
                    "_id.month": 1,
                    "_id.day": 1,
                    "_id.hour": 1
                }
            }
        ]
        
        results = await db[self.collection_name].aggregate(pipeline).to_list(length=None)
        
        traffic_data = []
        for item in results:
            date_info = item["_id"]
            traffic_data.append({
                "datetime": f"{date_info['year']}-{date_info['month']:02d}-{date_info['day']:02d} {date_info['hour']:02d}:00",
                "total_detections": item["count"],
                "detections_with_siren": item["with_siren"]
            })
        
        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "data": traffic_data
        }
    
    async def get_vehicle_activity_report(
        self,
        start_date: datetime,
        end_date: datetime,
        group_by: str = "day"
    ) -> dict:
        """
        Gera relatório de atividade por tipo de veículo.
        
        Args:
            start_date: Data inicial
            end_date: Data final
            group_by: Período de agrupamento (hour, day, month)
        
        Returns:
            Dados para gráfico de atividade por tipo de veículo
        """
        db = get_db()
        
        if group_by == "hour":
            time_group = {"hour": {"$hour": "$timestamp"}}
        elif group_by == "month":
            time_group = {
                "year": {"$year": "$timestamp"},
                "month": {"$month": "$timestamp"}
            }
        else:
            time_group = {
                "year": {"$year": "$timestamp"},
                "month": {"$month": "$timestamp"},
                "day": {"$dayOfMonth": "$timestamp"}
            }
        
        pipeline = [
            {
                "$match": {
                    "timestamp": {
                        "$gte": start_date,
                        "$lte": end_date
                    }
                }
            },
            {
                "$group": {
                    "_id": {
                        "time_period": time_group,
                        "vehicle_type": "$vehicle_type"
                    },
                    "count": {"$sum": 1},
                    "siren_on_count": {
                        "$sum": {"$cond": ["$siren_on", 1, 0]}
                    },
                    "avg_confidence": {"$avg": "$confidence_score"}
                }
            },
            {
                "$sort": {
                    "_id.time_period": 1,
                    "_id.vehicle_type": 1
                }
            }
        ]
        
        results = await db[self.collection_name].aggregate(pipeline).to_list(length=None)
        
        processed_data = self._process_vehicle_activity_data(results, group_by)
        
        return processed_data
    
    async def get_confidence_report(
        self,
        start_date: datetime,
        end_date: datetime,
        vehicle_type: Optional[VehicleType] = None
    ) -> dict:
        """
        Gera relatório de confiabilidade das detecções.
        
        Args:
            start_date: Data inicial
            end_date: Data final
            vehicle_type: Tipo de veículo (opcional)
        
        Returns:
            Relatório de confiabilidade com distribuição de scores
        """
        db = get_db()
        
        match_filter = {
            "timestamp": {
                "$gte": start_date,
                "$lte": end_date
            }
        }
        
        if vehicle_type:
            match_filter["vehicle_type"] = vehicle_type.value
        
        pipeline = [
            {"$match": match_filter},
            {
                "$group": {
                    "_id": None,
                    "total_detections": {"$sum": 1},
                    "average_confidence": {"$avg": "$confidence_score"},
                    "min_confidence": {"$min": "$confidence_score"},
                    "max_confidence": {"$max": "$confidence_score"},
                    "std_dev_confidence": {"$stdDevPop": "$confidence_score"},
                    "confidence_scores": {"$push": "$confidence_score"},
                    "detections_by_type": {
                        "$push": {
                            "vehicle_type": "$vehicle_type",
                            "confidence": "$confidence_score"
                        }
                    }
                }
            }
        ]
        
        result = await db[self.collection_name].aggregate(pipeline).to_list(length=1)
        
        if not result or not result[0].get("confidence_scores"):
            return self._get_empty_confidence_report()
        
        stats = result[0]
        confidence_scores = stats.get("confidence_scores", [])
        
        confidence_distribution = self._calculate_confidence_distribution(confidence_scores)
        
        confidence_by_vehicle = self._calculate_confidence_by_vehicle(stats.get("detections_by_type", []))
        
        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "summary": {
                "total_detections": stats.get("total_detections", 0),
                "average_confidence": round(stats.get("average_confidence", 0.0), 4),
                "min_confidence": round(stats.get("min_confidence", 0.0), 4),
                "max_confidence": round(stats.get("max_confidence", 0.0), 4),
                "std_dev_confidence": round(stats.get("std_dev_confidence", 0.0), 4)
            },
            "confidence_distribution": confidence_distribution,
            "confidence_by_vehicle": confidence_by_vehicle,
            "quality_metrics": self._calculate_quality_metrics(confidence_scores)
        }
    
    def _get_empty_confidence_report(self) -> dict:
        """Retorna estrutura vazia para relatório de confiança."""
        return {
            "period": {"start": "", "end": ""},
            "summary": {
                "total_detections": 0,
                "average_confidence": 0.0,
                "min_confidence": 0.0,
                "max_confidence": 0.0,
                "std_dev_confidence": 0.0
            },
            "confidence_distribution": {
                "very_high": 0, 
                "high": 0,      
                "medium": 0,  
                "low": 0,       
                "very_low": 0   
            },
            "confidence_by_vehicle": {},
            "quality_metrics": {
                "high_quality_rate": 0.0, 
                "reliable_rate": 0.0,      
                "needs_review_rate": 0.0   
            }
        }
    
    def _calculate_confidence_distribution(self, confidence_scores: list) -> dict:
        """Calcula a distribuição dos scores de confiança."""
        distribution = {
            "very_high": 0,  
            "high": 0,      
            "medium": 0,     
            "low": 0,       
            "very_low": 0    
        }
        
        for score in confidence_scores:
            if score >= 0.9:
                distribution["very_high"] += 1
            elif score >= 0.7:
                distribution["high"] += 1
            elif score >= 0.5:
                distribution["medium"] += 1
            elif score >= 0.3:
                distribution["low"] += 1
            else:
                distribution["very_low"] += 1
        
        return distribution
    
    def _calculate_confidence_by_vehicle(self, detections_by_type: list) -> dict:
        """Calcula estatísticas de confiança por tipo de veículo."""
        vehicle_stats = {}
        
        for detection in detections_by_type:
            vtype = detection.get("vehicle_type")
            confidence = detection.get("confidence", 0.0)
            
            if vtype not in vehicle_stats:
                vehicle_stats[vtype] = {
                    "count": 0,
                    "total_confidence": 0.0,
                    "min_confidence": 1.0,
                    "max_confidence": 0.0
                }
            
            stats = vehicle_stats[vtype]
            stats["count"] += 1
            stats["total_confidence"] += confidence
            stats["min_confidence"] = min(stats["min_confidence"], confidence)
            stats["max_confidence"] = max(stats["max_confidence"], confidence)
        
        for vtype, stats in vehicle_stats.items():
            if stats["count"] > 0:
                stats["average_confidence"] = round(stats["total_confidence"] / stats["count"], 4)
                stats["min_confidence"] = round(stats["min_confidence"], 4)
                stats["max_confidence"] = round(stats["max_confidence"], 4)
            else:
                stats["average_confidence"] = 0.0
            
            del stats["total_confidence"]
        
        return vehicle_stats
    
    def _calculate_quality_metrics(self, confidence_scores: list) -> dict:
        """Calcula métricas de qualidade baseadas na confiança."""
        total = len(confidence_scores)
        if total == 0:
            return {
                "high_quality_rate": 0.0,
                "reliable_rate": 0.0,
                "needs_review_rate": 0.0
            }
        
        high_quality = sum(1 for score in confidence_scores if score >= 0.7)
        reliable = sum(1 for score in confidence_scores if score >= 0.5)
        needs_review = sum(1 for score in confidence_scores if score < 0.3)
        
        return {
            "high_quality_rate": round((high_quality / total) * 100, 2),
            "reliable_rate": round((reliable / total) * 100, 2),
            "needs_review_rate": round((needs_review / total) * 100, 2)
        }
    
    def _process_vehicle_activity_data(self, raw_data: list, group_by: str) -> dict:
        """
        Processa dados brutos para formato de gráfico.
        
        Args:
            raw_data: Dados brutos do aggregation
            group_by: Tipo de agrupamento
        
        Returns:
            Dados formatados para front-end
        """
        periods = {}
        vehicle_types = set()
        
        for item in raw_data:
            vehicle_type = item["_id"]["vehicle_type"]
            time_data = item["_id"]["time_period"]
            
            if group_by == "hour":
                period_key = f"{time_data['hour']:02d}:00"
            elif group_by == "month":
                period_key = f"{time_data['year']}-{time_data['month']:02d}"
            else:  
                period_key = f"{time_data['year']}-{time_data['month']:02d}-{time_data['day']:02d}"
            
            if period_key not in periods:
                periods[period_key] = {
                    "total_detections": 0,
                    "by_vehicle_type": {},
                    "siren_usage": {},
                    "avg_confidence": {}
                }
            
            periods[period_key]["by_vehicle_type"][vehicle_type] = item["count"]
            periods[period_key]["siren_usage"][vehicle_type] = item["siren_on_count"]
            periods[period_key]["avg_confidence"][vehicle_type] = round(item["avg_confidence"], 4)
            periods[period_key]["total_detections"] += item["count"]
            
            vehicle_types.add(vehicle_type)
        
        return {
            "group_by": group_by,
            "vehicle_types": sorted(list(vehicle_types)),
            "periods": periods,
            "summary": {
                "total_vehicle_types": len(vehicle_types),
                "total_periods": len(periods),
                "total_detections": sum(period["total_detections"] for period in periods.values())
            }
        }


report_service = ReportService()