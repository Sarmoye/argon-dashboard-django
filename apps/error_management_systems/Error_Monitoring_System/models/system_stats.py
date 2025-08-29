from dataclasses import dataclass, field
from typing import List, Dict, Any
from datetime import datetime

@dataclass
class SystemStats:
    """Classe pour stocker les statistiques d'un système"""
    system_name: str
    total_errors: int = 0
    total_services: int = 0
    affected_services: int = 0
    health_percentage: float = 0.0
    critical_services: int = 0
    avg_errors: float = 0.0
    top_error_service: str = 'N/A'
    status: str = 'NO_DATA'
    stability_index: float = 0.0
    risk_level: str = 'UNKNOWN'
    business_impact: str = 'UNKNOWN'
    uptime_percentage: float = 0.0
    sla_status: str = 'UNKNOWN'
    error_density: float = 0.0
    critical_ratio: float = 0.0
    error_trend: int = 0
    improvement_rate: float = 0.0
    week_trend: float = 0.0
    days_analyzed: int = 0
    trend_status: str = 'STABLE'
    volatility: float = 0.0
    momentum: str = 'NEUTRAL'
    predicted_errors: int = 0
    prediction_confidence: str = 'LOW'
    reliability_trend: float = 0.0
    stability_trend: str = 'STABLE'
    affected_services_list: List[str] = field(default_factory=list)
    critical_services_list: List[str] = field(default_factory=list)
    error_distribution: Dict[str, int] = field(default_factory=dict)
    comparison_time_info: str = ""
    
    @classmethod
    def from_data(cls, system_name: str, data, trends_data=None):
        """Crée des statistiques à partir des données brutes"""
        # Implémentation de calculate_enhanced_stats adaptée
        stats = cls(system_name)
        
        if data is None or data.empty:
            if trends_data:
                stats.error_trend = trends_data.get('error_trend', 0)
                stats.improvement_rate = trends_data.get('improvement_rate', 0)
                stats.trend_status = 'NO_DATA'
                stats.predicted_errors = trends_data.get('predicted_errors', 0)
                stats.volatility = trends_data.get('volatility', 0)
            return stats
        
        # Calcul des statistiques (code adapté de calculate_enhanced_stats)
        grouped_data = data.groupby('Service Name')['Error Count'].sum().reset_index()
        
        stats.total_errors = int(grouped_data['Error Count'].sum())
        stats.total_services = len(grouped_data)
        
        # Récupérer les listes de services
        stats.affected_services_list = grouped_data[grouped_data['Error Count'] > 0]['Service Name'].tolist()
        stats.critical_services_list = grouped_data[grouped_data['Error Count'] >= 10]['Service Name'].tolist()
        
        stats.affected_services = len(stats.affected_services_list)
        stats.critical_services = len(stats.critical_services_list)
        
        stats.health_percentage = round(((stats.total_services - stats.affected_services) / stats.total_services) * 100, 1) if stats.total_services > 0 else 0
        stats.avg_errors = round(stats.total_errors / stats.total_services, 2) if stats.total_services > 0 else 0

        # Service le plus impacté
        if stats.total_errors > 0:
            max_idx = grouped_data['Error Count'].idxmax()
            stats.top_error_service = grouped_data.loc[max_idx, 'Service Name']

        # Ajouter les données de tendance si disponibles
        if trends_data:
            stats.error_trend = trends_data.get('error_trend', 0)
            stats.improvement_rate = trends_data.get('improvement_rate', 0)
            stats.week_trend = trends_data.get('week_trend', 0)
            stats.days_analyzed = trends_data.get('days_analyzed', 0)
            stats.trend_status = 'IMPROVING' if stats.error_trend < 0 else 'DEGRADING' if stats.error_trend > 0 else 'STABLE'
            stats.volatility = trends_data.get('volatility', 0)
            stats.momentum = trends_data.get('momentum', 'NEUTRAL')
            stats.predicted_errors = trends_data.get('predicted_errors', 0)
            stats.prediction_confidence = trends_data.get('prediction_confidence', 'LOW')
            stats.reliability_trend = trends_data.get('reliability_trend', 0)
            stats.stability_trend = trends_data.get('stability_trend', 'STABLE')
            stats.comparison_time_info = trends_data.get('comparison_time_info', "")
            
            # S'assurer que les listes de tendances sont passées si elles existent
            if 'current_affected_services_list' in trends_data:
                stats.affected_services_list = trends_data['current_affected_services_list']
            if 'current_critical_services_list' in trends_data:
                stats.critical_services_list = trends_data['current_critical_services_list']

        return stats