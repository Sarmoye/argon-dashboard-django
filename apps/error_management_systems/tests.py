#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import glob
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from io import BytesIO
import warnings
warnings.filterwarnings('ignore')

# Configuration des répertoires
CIS_ERROR_REPORT_OUTPUT_DIR = "/srv/itsea_files/cis_error_report_files"
ECW_ERROR_REPORT_OUTPUT_DIR = "/srv/itsea_files/ecw_error_report_files"
ECW_ERROR_REPORT_OUTPUT_DIR2 = "/srv/itsea_files/ecw_error_report_files_second"
IRM_ERROR_REPORT_OUTPUT_DIR = "/srv/itsea_files/irm_error_report_files"

# Configuration email par système
EMAIL_CONFIG = {
    'smtp_server': '10.77.152.66',
    'smtp_port': 25,
    'from_email': 'noreply.errormonitor@mtn.com',
    'cis_recipients': ['Sarmoye.AmitoureHaidara@mtn.com'],
    'irm_recipients': ['Sarmoye.AmitoureHaidara@mtn.com'],
    'ecw_recipients': ['Sarmoye.AmitoureHaidara@mtn.com'],
    'summary_recipients': ['Sarmoye.AmitoureHaidara@mtn.com']
}

def get_files_by_date_range(directory, days=7):
    """Récupère les fichiers CSV des N derniers jours"""
    try:
        csv_files = glob.glob(os.path.join(directory, "*.csv"))
        if not csv_files:
            return []
        
        # Filtrer les fichiers des 7 derniers jours
        now = datetime.now()
        recent_files = []
        
        for file_path in csv_files:
            file_time = datetime.fromtimestamp(os.path.getctime(file_path))
            if (now - file_time).days <= days:
                recent_files.append((file_path, file_time))
        
        # Trier par date (plus récent d'abord)
        recent_files.sort(key=lambda x: x[1], reverse=True)
        return [f[0] for f in recent_files]
        
    except Exception as e:
        print(f"Erreur récupération fichiers: {e}")
        return []

def get_latest_csv_file(directory):
    """Récupère le fichier CSV le plus récent"""
    try:
        csv_files = glob.glob(os.path.join(directory, "*.csv"))
        if not csv_files:
            return None
        return max(csv_files, key=os.path.getctime)
    except Exception as e:
        print(f"Erreur: {e}")
        return None

def read_csv_data(file_path, system_name=None):
    """Lit et traite les données CSV"""
    try:
        if system_name in ["CIS", "IRM"]:
            headers = ['Domain', 'Service Type', 'Service Name', 'Error Count', 'Error Reason']
        else:
            headers = ['Domain', 'Service Type', 'Service Name', 'Error Count']

        skip_rows = 1 if system_name == "IRM" else 0
        df = pd.read_csv(file_path, header=None, names=headers, skiprows=skip_rows)
        
        if 'Error Count' in df.columns:
            df['Error Count'] = pd.to_numeric(df['Error Count'], errors='coerce').fillna(0)
        
        return df
    except Exception as e:
        print(f"Erreur lecture CSV: {e}")
        return None

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
from typing import Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

def analyze_historical_trends(directory: str, system_name: str, days: int = 7) -> Optional[Dict]:
    """
    Analyse les tendances sur les N derniers jours avec insights avancés et prédictions
    
    Args:
        directory: Chemin du répertoire des fichiers
        system_name: Nom du système à analyser
        days: Nombre de jours d'historique à considérer
    
    Returns:
        Dict contenant les données d'analyse et prédictions avec marges d'erreur
    """
    
    # Récupération des fichiers dans la plage de dates
    files = get_files_by_date_range(directory, days)
    if len(files) < 2:
        print("❌ Données insuffisantes pour l'analyse (moins de 2 fichiers)")
        return None
    
    trends_data = []
    
    # Lecture et traitement de chaque fichier
    for file_path in files:
        try:
            data = read_csv_data(file_path, system_name)
            if data is not None and not data.empty:
                grouped_data = data.groupby('Service Name')['Error Count'].sum().reset_index()
                
                file_date = datetime.fromtimestamp(os.path.getctime(file_path))
                total_errors = grouped_data['Error Count'].sum()
                
                # Calcul des métriques de service
                affected_services_list = grouped_data[grouped_data['Error Count'] > 0]['Service Name'].tolist()
                critical_services_list = grouped_data[grouped_data['Error Count'] >= 10]['Service Name'].tolist()
                
                affected_services_count = len(affected_services_list)
                critical_services_count = len(critical_services_list)
                total_services = len(grouped_data)
                
                # Stockage des données de tendance
                trends_data.append({
                    'date': file_date,
                    'total_errors': total_errors,
                    'affected_services': affected_services_count,
                    'critical_services': critical_services_count,
                    'total_services': total_services,
                    'error_density': total_errors / total_services if total_services > 0 else 0,
                    'reliability_score': ((total_services - affected_services_count) / total_services * 100) if total_services > 0 else 0,
                    'affected_services_list': affected_services_list,
                    'critical_services_list': critical_services_list
                })
        except Exception as e:
            print(f"⚠️ Erreur analyse fichier {file_path}: {e}")
            continue
            
    if not trends_data or len(trends_data) < 2:
        print("❌ Aucune donnée valide trouvée")
        return None
    
    # Création du DataFrame et tri par date
    trends_df = pd.DataFrame(trends_data)
    trends_df = trends_df.sort_values('date')
    
    # Données actuelles (dernier fichier)
    current = trends_df.iloc[-1]
    current_time = current['date']
    
    # Recherche du point de comparaison précédent
    previous = find_previous_comparison_point(trends_df, current_time)
    if previous is None:
        print("❌ Impossible de trouver un point de comparaison valide")
        return None
    
    # Calcul des tendances de base
    error_trend = current['total_errors'] - previous['total_errors']
    affected_trend = current['affected_services'] - previous['affected_services']
    critical_trend = current['critical_services'] - previous['critical_services']
    reliability_trend = current['reliability_score'] - previous['reliability_score']
    
    # Analyse des tendances avancées
    trend_analysis = analyze_advanced_trends(trends_df)
    
    # Prédictions avec marges d'erreur
    predictions = generate_predictions(trends_df, current, error_trend)
    
    # Analyse des patterns saisonniers
    seasonal_patterns = analyze_seasonal_patterns(trends_df)
    
    # Détection d'anomalies
    anomalies = detect_anomalies(trends_df)
    
    return {
        # Données brutes
        'data': trends_df,
        'current_time': current_time,
        'comparison_time': previous['date'],
        
        # Tendance basique
        'current_errors': int(current['total_errors']),
        'previous_errors': int(previous['total_errors']),
        'error_trend': int(error_trend),
        'affected_trend': int(affected_trend),
        'critical_trend': int(critical_trend),
        'reliability_trend': round(reliability_trend, 1),
        'improvement_rate': round((error_trend / previous['total_errors'] * 100) if previous['total_errors'] > 0 else 0, 1),
        
        # Analyse avancée
        **trend_analysis,
        
        # Prédictions
        **predictions,
        
        # Patterns saisonniers
        'seasonal_patterns': seasonal_patterns,
        
        # Anomalies
        'anomalies_detected': anomalies,
        
        # Listes de services
        'current_affected_services_list': current['affected_services_list'],
        'current_critical_services_list': current['critical_services_list'],
        'previous_affected_services_list': previous['affected_services_list'],
        
        # Métadonnées
        'days_analyzed': len(trends_df),
        'analysis_period': f"{trends_df['date'].min().strftime('%Y-%m-%d')} to {trends_df['date'].max().strftime('%Y-%m-%d')}",
        'data_quality_score': calculate_data_quality_score(trends_df)
    }

def find_previous_comparison_point(trends_df: pd.DataFrame, current_time: datetime) -> Optional[pd.Series]:
    """
    Trouve le point de comparaison précédent optimal
    """
    previous_day = current_time - timedelta(days=1)
    time_target = previous_day.replace(
        hour=current_time.hour, 
        minute=current_time.minute, 
        second=0, 
        microsecond=0
    )
    
    # Fenêtre horaire de ±30 minutes
    time_window_start = time_target - timedelta(minutes=30)
    time_window_end = time_target + timedelta(minutes=30)
    
    # Filtrage dans la fenêtre horaire
    previous_files = trends_df[
        (trends_df['date'] >= time_window_start) & 
        (trends_df['date'] <= time_window_end)
    ]
    
    if not previous_files.empty:
        previous_files = previous_files.copy()
        previous_files['time_diff'] = abs((previous_files['date'] - time_target).dt.total_seconds())
        return previous_files.loc[previous_files['time_diff'].idxmin()]
    
    # Fallback: fichiers du jour précédent
    previous_day_files = trends_df[trends_df['date'].dt.date == previous_day.date()]
    if not previous_day_files.empty:
        previous_day_files = previous_day_files.copy()
        previous_day_files['time_diff'] = abs((previous_day_files['date'] - time_target).dt.total_seconds())
        return previous_day_files.loc[previous_day_files['time_diff'].idxmin()]
    
    # Fallback: dernier fichier disponible avant current_time
    previous_files_all = trends_df[trends_df['date'] < current_time]
    if not previous_files_all.empty:
        return previous_files_all.iloc[-1]
    
    return None

def analyze_advanced_trends(trends_df: pd.DataFrame) -> Dict:
    """
    Analyse les tendances avancées et la volatilité
    """
    result = {}
    
    # Tendance hebdomadaire
    if len(trends_df) >= 4:
        avg_recent = trends_df.tail(3)['total_errors'].mean()
        avg_older = trends_df.head(max(1, len(trends_df) - 3))['total_errors'].mean()
        result['week_trend'] = avg_recent - avg_older
        result['week_trend_percentage'] = round((result['week_trend'] / avg_older * 100) if avg_older > 0 else 0, 1)
    else:
        result['week_trend'] = 0
        result['week_trend_percentage'] = 0
    
    # Volatilité et stabilité
    volatility = trends_df['total_errors'].std()
    result['volatility'] = round(volatility, 2)
    
    if volatility < 5:
        result['stability_trend'] = "STABLE"
    elif volatility < 15:
        result['stability_trend'] = "MODERATE"
    else:
        result['stability_trend'] = "HIGH_VOLATILITY"
    
    # Momentum
    result['momentum'] = calculate_momentum(trends_df)
    
    # Métriques supplémentaires
    result['avg_error_density'] = round(trends_df['error_density'].mean(), 2)
    result['peak_errors'] = int(trends_df['total_errors'].max())
    result['best_day_errors'] = int(trends_df['total_errors'].min())
    result['error_reduction_potential'] = result['peak_errors'] - result['best_day_errors']
    
    return result

def calculate_momentum(trends_df: pd.DataFrame) -> str:
    """
    Calcule le momentum des erreurs
    """
    if len(trends_df) < 3:
        return "INSUFFICIENT_DATA"
    
    # Utilise une régression linéaire simple pour le momentum
    X = np.arange(len(trends_df)).reshape(-1, 1)
    y = trends_df['total_errors'].values
    
    try:
        slope = np.polyfit(range(len(trends_df)), y, 1)[0]
        if slope > 2:
            return "ACCELERATING"
        elif slope < -2:
            return "DECELERATING"
        else:
            return "NEUTRAL"
    except:
        return "NEUTRAL"

def generate_predictions(trends_df: pd.DataFrame, current: pd.Series, error_trend: float) -> Dict:
    """
    Génère des prédictions avec marges d'erreur
    """
    predictions = {}
    
    # Méthode 1: Trend simple
    simple_pred = max(0, current['total_errors'] + error_trend)
    
    # Méthode 2: Moyenne mobile
    if len(trends_df) >= 3:
        moving_avg = trends_df['total_errors'].rolling(window=3).mean().iloc[-1]
        ma_pred = max(0, moving_avg + error_trend)
    else:
        ma_pred = simple_pred
    
    # Méthode 3: Régression linéaire
    if len(trends_df) >= 5:
        try:
            X = np.arange(len(trends_df)).reshape(-1, 1)
            y = trends_df['total_errors'].values
            model = np.polyfit(range(len(trends_df)), y, 1)
            regression_pred = max(0, np.polyval(model, len(trends_df)))
        except:
            regression_pred = simple_pred
    else:
        regression_pred = simple_pred
    
    # Prédiction consensus (moyenne pondérée)
    weights = {
        'simple': 0.3 if len(trends_df) < 3 else 0.2,
        'moving_avg': 0.4 if len(trends_df) >= 3 else 0,
        'regression': 0.4 if len(trends_df) >= 5 else 0.3
    }
    
    total_weight = weights['simple'] + weights['moving_avg'] + weights['regression']
    consensus_pred = (
        weights['simple'] * simple_pred +
        weights['moving_avg'] * ma_pred +
        weights['regression'] * regression_pred
    ) / total_weight
    
    # Calcul de la marge d'erreur
    error_margin = calculate_error_margin(trends_df, consensus_pred)
    
    # Niveau de confiance
    if len(trends_df) >= 7:
        confidence = "HIGH"
        confidence_level = 85
    elif len(trends_df) >= 4:
        confidence = "MEDIUM"
        confidence_level = 70
    else:
        confidence = "LOW"
        confidence_level = 55
    
    predictions.update({
        'predicted_errors_simple': int(simple_pred),
        'predicted_errors_moving_avg': int(ma_pred),
        'predicted_errors_regression': int(regression_pred),
        'predicted_errors_consensus': int(consensus_pred),
        'prediction_confidence': confidence,
        'confidence_level': confidence_level,
        'error_margin_lower': int(max(0, consensus_pred - error_margin)),
        'error_margin_upper': int(consensus_pred + error_margin),
        'error_margin_range': int(error_margin),
        'prediction_accuracy_estimate': f"±{int(error_margin)} erreurs",
        'recommended_action': get_recommendation(consensus_pred, current['total_errors'], error_margin)
    })
    
    return predictions

def calculate_error_margin(trends_df: pd.DataFrame, prediction: float) -> float:
    """
    Calcule la marge d'erreur des prédictions basée sur l'historique
    """
    if len(trends_df) < 3:
        return prediction * 0.3  # Marge conservatrice si peu de données
    
    # Calcul de l'erreur absolue moyenne des prédictions passées
    actual_errors = trends_df['total_errors'].values
    mae_values = []
    
    for i in range(2, len(actual_errors)):
        # Prédiction basée sur la tendance précédente
        predicted = actual_errors[i-1] + (actual_errors[i-1] - actual_errors[i-2])
        mae_values.append(abs(predicted - actual_errors[i]))
    
    if mae_values:
        avg_mae = np.mean(mae_values)
        # Ajoute un buffer basé sur la volatilité
        volatility_factor = trends_df['total_errors'].std() * 0.5
        return avg_mae + volatility_factor
    else:
        return prediction * 0.25

def analyze_seasonal_patterns(trends_df: pd.DataFrame) -> Dict:
    """
    Analyse les patterns saisonniers (quotidiens, hebdomadaires)
    """
    patterns = {
        'daily_pattern': {},
        'weekly_pattern': {},
        'peak_hours': [],
        'quiet_hours': []
    }
    
    if len(trends_df) < 7:
        patterns['data_sufficiency'] = "INSUFFICIENT_FOR_SEASONAL_ANALYSIS"
        return patterns
    
    # Analyse par heure de la journée
    trends_df['hour'] = trends_df['date'].dt.hour
    hourly_pattern = trends_df.groupby('hour')['total_errors'].mean()
    
    if not hourly_pattern.empty:
        patterns['daily_pattern'] = {
            'peak_hour': hourly_pattern.idxmax(),
            'peak_errors': int(hourly_pattern.max()),
            'quiet_hour': hourly_pattern.idxmin(),
            'quiet_errors': int(hourly_pattern.min())
        }
    
    # Analyse par jour de la semaine
    trends_df['weekday'] = trends_df['date'].dt.day_name()
    weekday_pattern = trends_df.groupby('weekday')['total_errors'].mean()
    
    if not weekday_pattern.empty:
        patterns['weekly_pattern'] = weekday_pattern.to_dict()
    
    patterns['data_sufficiency'] = "SUFFICIENT"
    return patterns

def detect_anomalies(trends_df: pd.DataFrame) -> List[Dict]:
    """
    Détecte les anomalies dans les données historiques
    """
    anomalies = []
    
    if len(trends_df) < 5:
        return anomalies
    
    # Détection basée sur l'écart interquartile
    Q1 = trends_df['total_errors'].quantile(0.25)
    Q3 = trends_df['total_errors'].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    
    for idx, row in trends_df.iterrows():
        if row['total_errors'] < lower_bound or row['total_errors'] > upper_bound:
            anomalies.append({
                'date': row['date'],
                'errors': int(row['total_errors']),
                'type': 'LOW' if row['total_errors'] < lower_bound else 'HIGH',
                'deviation': round((row['total_errors'] - trends_df['total_errors'].mean()) / trends_df['total_errors'].std(), 2)
            })
    
    return anomalies

def calculate_data_quality_score(trends_df: pd.DataFrame) -> float:
    """
    Calcule un score de qualité des données (0-100)
    """
    if len(trends_df) < 2:
        return 0
    
    # Facteurs de qualité
    completeness = 1.0  # Tous les fichiers ont été lus avec succès
    consistency = 1 - (trends_df['total_services'].std() / trends_df['total_services'].mean()) if trends_df['total_services'].mean() > 0 else 0.8
    timeliness = min(1.0, len(trends_df) / 7)  # Basé sur le nombre de jours de données
    
    return round((completeness * 0.4 + consistency * 0.3 + timeliness * 0.3) * 100, 1)

def get_recommendation(predicted_errors: float, current_errors: float, error_margin: float) -> str:
    """
    Génère une recommandation basée sur les prédictions
    """
    if predicted_errors > current_errors + error_margin:
        return "INCREASE_MONITORING"
    elif predicted_errors < current_errors - error_margin:
        return "MAINTAIN_CURRENT"
    else:
        return "NO_SIGNIFICANT_CHANGE"

def calculate_enhanced_stats(data, system_name, trends_data=None):
    """Calcule des statistiques avancées avec insights professionnels et prédictions"""
    base_stats = {
        'total_errors': 0, 'total_services': 0, 'affected_services': 0,
        'health_percentage': 0, 'critical_services': 0, 'avg_errors': 0,
        'top_error_service': 'N/A', 'status': 'NO_DATA',
        'stability_index': 0, 'risk_level': 'UNKNOWN', 'business_impact': 'UNKNOWN',
        'affected_services_list': [],
        'critical_services_list': [],
        'predicted_errors_consensus': 0,
        'error_margin_range': 0,
        'prediction_accuracy': 'N/A',
        'confidence_level': 0,
        'recommended_action': 'NO_DATA'
    }

    if data is None or data.empty:
        if trends_data:
            # Mise à jour avec les nouvelles données de tendance
            base_stats.update({
                'error_trend': trends_data.get('error_trend', 0),
                'improvement_rate': trends_data.get('improvement_rate', 0),
                'trend_status': 'NO_DATA',
                'predicted_errors_consensus': trends_data.get('predicted_errors_consensus', 0),
                'error_margin_lower': trends_data.get('error_margin_lower', 0),
                'error_margin_upper': trends_data.get('error_margin_upper', 0),
                'error_margin_range': trends_data.get('error_margin_range', 0),
                'prediction_accuracy': trends_data.get('prediction_accuracy_estimate', 'N/A'),
                'confidence_level': trends_data.get('confidence_level', 0),
                'recommended_action': trends_data.get('recommended_action', 'NO_DATA'),
                'volatility': trends_data.get('volatility', 0),
                'week_trend': trends_data.get('week_trend', 0),
                'momentum': trends_data.get('momentum', 'NEUTRAL'),
                'stability_trend': trends_data.get('stability_trend', 'STABLE')
            })
        return base_stats

    grouped_data = data.groupby('Service Name')['Error Count'].sum().reset_index()

    # Statistiques de base
    total_errors = int(grouped_data['Error Count'].sum())
    total_services = len(grouped_data)
    
    # Récupérer les listes de services
    affected_services_list = grouped_data[grouped_data['Error Count'] > 0]['Service Name'].tolist()
    critical_services_list = grouped_data[grouped_data['Error Count'] >= 10]['Service Name'].tolist()
    
    affected_services_count = len(affected_services_list)
    critical_services_count = len(critical_services_list)
    
    health_percentage = round(((total_services - affected_services_count) / total_services) * 100, 1) if total_services > 0 else 0
    avg_errors = round(total_errors / total_services, 2) if total_services > 0 else 0

    # Service le plus impacté
    top_service = 'N/A'
    if total_errors > 0:
        max_idx = grouped_data['Error Count'].idxmax()
        top_service = grouped_data.loc[max_idx, 'Service Name']

    # Calcul de l'index de stabilité (0-100)
    health_weight = health_percentage * 0.4
    error_density = total_errors / total_services if total_services > 0 else 0
    density_score = max(0, 100 - (error_density * 10)) * 0.3
    critical_penalty = max(0, 100 - (critical_services_count / total_services * 200)) * 0.3 if total_services > 0 else 100
    stability_index = round(health_weight + density_score + critical_penalty, 1)

    # Évaluation des risques
    critical_ratio = critical_services_count / total_services if total_services > 0 else 0
    if critical_ratio > 0.3 or error_density > 10:
        risk_level = 'HIGH'
        business_impact = 'SEVERE'
    elif critical_ratio > 0.1 or error_density > 5:
        risk_level = 'MEDIUM'
        business_impact = 'MODERATE'
    else:
        risk_level = 'LOW'
        business_impact = 'MINIMAL'

    # Statut global amélioré
    if total_errors == 0:
        status = 'HEALTHY'
    elif critical_services_count > 0 or stability_index < 50:
        status = 'CRITICAL'
    elif stability_index < 70:
        status = 'WARNING'
    else:
        status = 'HEALTHY'

    # Métriques avancées
    error_distribution = {
        'zero_errors': int((grouped_data['Error Count'] == 0).sum()),
        'low_errors': int((grouped_data['Error Count'].between(1, 5)).sum()),
        'medium_errors': int((grouped_data['Error Count'].between(6, 10)).sum()),
        'high_errors': int((grouped_data['Error Count'] > 10).sum())
    }

    # SLA et métriques de performance
    uptime_percentage = round(((total_services - affected_services_count) / total_services) * 100, 2) if total_services > 0 else 0
    sla_status = 'MEETING' if uptime_percentage >= 99.5 else 'AT_RISK' if uptime_percentage >= 95 else 'BREACH'

    stats = {
        'total_errors': total_errors,
        'total_services': total_services,
        'affected_services': affected_services_count,
        'health_percentage': health_percentage,
        'critical_services': critical_services_count,
        'avg_errors': avg_errors,
        'top_error_service': top_service,
        'status': status,
        'stability_index': stability_index,
        'risk_level': risk_level,
        'business_impact': business_impact,
        'error_distribution': error_distribution,
        'uptime_percentage': uptime_percentage,
        'sla_status': sla_status,
        'error_density': round(error_density, 3),
        'critical_ratio': round(critical_ratio * 100, 1),
        'affected_services_list': affected_services_list,
        'critical_services_list': critical_services_list,
        'predicted_errors_consensus': 0,
        'error_margin_range': 0,
        'prediction_accuracy': 'N/A',
        'confidence_level': 0,
        'recommended_action': 'NO_DATA'
    }

    # Ajouter les données de tendance si disponibles
    if trends_data:
        trend_status = 'IMPROVING' if trends_data.get('error_trend', 0) < 0 else 'DEGRADING' if trends_data.get('error_trend', 0) > 0 else 'STABLE'
        
        # Mise à jour avec les nouvelles métriques de prédiction
        stats.update({
            'error_trend': trends_data.get('error_trend', 0),
            'improvement_rate': trends_data.get('improvement_rate', 0),
            'week_trend': trends_data.get('week_trend', 0),
            'days_analyzed': trends_data.get('days_analyzed', 0),
            'trend_status': trend_status,
            'volatility': trends_data.get('volatility', 0),
            'momentum': trends_data.get('momentum', 'NEUTRAL'),
            'reliability_trend': trends_data.get('reliability_trend', 0),
            'stability_trend': trends_data.get('stability_trend', 'STABLE'),
            'predicted_errors_consensus': trends_data.get('predicted_errors_consensus', 0),
            'error_margin_lower': trends_data.get('error_margin_lower', 0),
            'error_margin_upper': trends_data.get('error_margin_upper', 0),
            'error_margin_range': trends_data.get('error_margin_range', 0),
            'prediction_accuracy': trends_data.get('prediction_accuracy_estimate', 'N/A'),
            'confidence_level': trends_data.get('confidence_level', 0),
            'recommended_action': trends_data.get('recommended_action', 'NO_DATA'),
            'predicted_errors_simple': trends_data.get('predicted_errors_simple', 0),
            'predicted_errors_moving_avg': trends_data.get('predicted_errors_moving_avg', 0),
            'predicted_errors_regression': trends_data.get('predicted_errors_regression', 0),
            'prediction_confidence': trends_data.get('prediction_confidence', 'LOW')
        })

        # S'assurer que les listes de tendances sont passées si elles existent
        if 'current_affected_services_list' in trends_data:
            stats['affected_services_list'] = trends_data['current_affected_services_list']
        if 'current_critical_services_list' in trends_data:
            stats['critical_services_list'] = trends_data['current_critical_services_list']

    return stats

import numpy as np

def create_trend_chart(directory, trends_data, system_name):
    """Crée un graphique de tendance avancé avec prédictions au style Soft UI."""
    if not trends_data or trends_data['data'].empty:
        return None
    
    try:
        df = trends_data['data']
        
        # --- Soft UI Enhancements ---
        plt.style.use('seaborn-v0_8-whitegrid')
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(18, 14))
        fig.patch.set_facecolor('#f0f2f5')
        
        colors_map = {'CIS': '#e74c3c', 'IRM': '#f39c12', 'ECW': '#27ae60'}
        primary_color = colors_map.get(system_name, '#3498db')
        
        # Helper for common styling
        def apply_soft_ui_to_ax(ax):
            ax.set_facecolor('white')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_color('#cccccc')
            ax.spines['bottom'].set_color('#cccccc')
            ax.tick_params(axis='x', colors='#555555')
            ax.tick_params(axis='y', colors='#555555')
            ax.grid(color='#e0e0e0', linestyle='--', linewidth=0.7, alpha=0.7)

        # Graphique 1: Evolution des erreurs avec prédiction
        dates = [d.strftime('%b %d') for d in df['date']]
        ax1.plot(dates, df['total_errors'], marker='o', linewidth=3, markersize=8, 
                 color=primary_color, markerfacecolor='white', markeredgewidth=2, 
                 markeredgecolor=primary_color, label='Actual Errors')
        ax1.fill_between(dates, df['total_errors'], alpha=0.1, color=primary_color)
        
        # Ajouter la prédiction
        if 'predicted_errors_consensus' in trends_data:
            pred_date = (df['date'].iloc[-1] + timedelta(days=1)).strftime('%b %d')
            all_dates = dates + [pred_date]
            pred_line = list(df['total_errors']) + [trends_data['predicted_errors_consensus']]
            ax1.plot(all_dates[-2:], pred_line[-2:], 'r--', linewidth=2, alpha=0.6, label='Prediction')
            ax1.scatter([pred_date], [trends_data['predicted_errors_consensus']], color='red', s=120, alpha=0.7, zorder=5)
            ax1.text(pred_date, trends_data['predicted_errors_consensus'] * 1.05, 
                     f"{int(trends_data['predicted_errors_consensus'])}", color='red', 
                     ha='center', va='bottom', fontsize=10, fontweight='bold')
        
        ax1.set_title(f'{system_name} - Error Trends & Predictions', 
                      fontsize=16, fontweight='bold', color='#333333', pad=20)
        ax1.set_ylabel('Total Errors', fontsize=12, fontweight='bold', color='#555555')
        ax1.tick_params(axis='x', rotation=30)
        ax1.legend(fontsize=10, frameon=True, shadow=True, fancybox=True, loc='upper left')
        apply_soft_ui_to_ax(ax1)
        
        # Graphique 2: Répartition des erreurs par service
        # Obtenir les données du jour le plus récent
        latest_data = df.iloc[-1]
        
        # Lire le fichier CSV du jour le plus récent pour obtenir la répartition par service
        latest_date = latest_data['date']
        latest_file = None
        
        # Trouver le fichier correspondant à la date la plus récente
        for file_path in get_files_by_date_range(directory, 1):  # On cherche dans les fichiers du dernier jour
            file_date = datetime.fromtimestamp(os.path.getctime(file_path))
            if file_date.date() == latest_date.date():
                latest_file = file_path
                break
        
        if latest_file:
            try:
                # Lire les données du fichier
                data = read_csv_data(latest_file, system_name)
                if data is not None and not data.empty:
                    # Grouper par service et sommer les erreurs
                    service_errors = data.groupby('Service Name')['Error Count'].sum().reset_index()
                    # Trier par nombre d'erreurs décroissant
                    service_errors = service_errors.sort_values('Error Count', ascending=False)
                    
                    # Prendre les 10 services avec le plus d'erreurs (ou moins si moins de 10)
                    top_services = service_errors.head(10)
                    
                    # Créer un graphique à barres horizontales
                    bars = ax2.barh(top_services['Service Name'], top_services['Error Count'], 
                                   color=primary_color, alpha=0.7)
                    
                    # Ajouter les valeurs sur les barres
                    for bar in bars:
                        width = bar.get_width()
                        ax2.text(width + 0.1, bar.get_y() + bar.get_height()/2, 
                                f'{int(width)}', ha='left', va='center', fontsize=9)
                    
                    ax2.set_title(f'Services by Error Count\n({latest_date.strftime("%Y-%m-%d")})', 
                                 fontsize=14, fontweight='bold', color='#333333')
                    ax2.set_xlabel('Error Count', fontsize=12, color='#555555')
                    ax2.set_ylabel('Service Name', fontsize=12, color='#555555')
                    
                    # Inverser l'axe Y pour avoir le service avec le plus d'erreurs en haut
                    ax2.invert_yaxis()
                    
            except Exception as e:
                print(f"Erreur lecture fichier {latest_file}: {e}")
                ax2.text(0.5, 0.5, 'Données non disponibles', ha='center', va='center', 
                        transform=ax2.transAxes, fontsize=12, color='red')
        else:
            ax2.text(0.5, 0.5, 'Fichier non trouvé', ha='center', va='center', 
                    transform=ax2.transAxes, fontsize=12, color='red')
        
        apply_soft_ui_to_ax(ax2)

        # Graphique 3: Densité d'erreurs
        ax3.bar(dates, df['error_density'], color=primary_color, alpha=0.7, width=0.6)
        ax3.set_title('Error Density (Errors/Service)', fontsize=14, fontweight='bold', color='#333333')
        ax3.set_ylabel('Errors per Service', fontsize=12, color='#555555')
        apply_soft_ui_to_ax(ax3)
        ax3.tick_params(axis='x', rotation=30)
        
        # Graphique 4: Score de fiabilité
        ax4.plot(dates, df['reliability_score'], marker='s', linewidth=2.5, markersize=7, 
                 color='#28a745', markerfacecolor='white', markeredgewidth=2, markeredgecolor='#28a745')
        ax4.fill_between(dates, df['reliability_score'], 100, alpha=0.1, color='#28a745')
        ax4.set_title('Reliability Score (%)', fontsize=14, fontweight='bold', color='#333333')
        ax4.set_ylabel('Reliability (%)', fontsize=12, color='#555555')
        ax4.set_ylim(max(0, df['reliability_score'].min() - 10), 100)
        ax4.axhline(y=95, color='#007bff', linestyle='--', alpha=0.7, label='SLA Target', linewidth=1.5)
        ax4.legend(fontsize=10, frameon=True, shadow=True, fancybox=True)
        apply_soft_ui_to_ax(ax4)
        ax4.tick_params(axis='x', rotation=30)
        
        plt.tight_layout(pad=3.0)
        fig.suptitle(f'System Performance Analysis: {system_name}', 
                     fontsize=20, fontweight='bold', color='#222222', y=1.02)
        
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight', facecolor=fig.patch.get_facecolor())
        buffer.seek(0)
        chart_data = buffer.getvalue()
        buffer.close()
        plt.close()
        
        return chart_data
        
    except Exception as e:
        print(f"Erreur graphique tendance: {e}")
        plt.close()
        return None
    
#
# Generates a professional, enhanced HTML report with trend analysis and explanatory text.
#
from datetime import datetime

def create_professional_system_html_with_trends(system_name, data, stats, date_str, trends_data=None):
    """Creates a professional HTML report enriched with trend analysis and explanatory text."""
    
    # Define color mappings and text
    status_colors = {
        'HEALTHY': ('#27ae60', '✅ SYSTEM HEALTHY'),
        'WARNING': ('#f39c12', '⚠️ SYSTEM WARNING'),
        'CRITICAL': ('#e74c3c', '🔴 SYSTEM CRITICAL'),
        'NO_DATA': ('#95a5a6', '⚪ NO DATA')
    }

    trend_colors = {
        'IMPROVING': ('#27ae60', '📈 IMPROVING'),
        'DEGRADING': ('#e74c3c', '📉 DEGRADING'),
        'STABLE': ('#3498db', '➡️ STABLE')
    }

    momentum_colors = {
        'ACCELERATING': '#e74c3c',
        'DECELERATING': '#27ae60',
        'NEUTRAL': '#3498db',
        'INSUFFICIENT_DATA': '#95a5a6'
    }

    stability_colors = {
        'HIGH_VOLATILITY': '#e74c3c',
        'MODERATE': '#f39c12',
        'STABLE': '#27ae60',
        'INSUFFICIENT_DATA': '#95a5a6'
    }

    sla_colors = {
        'MEETING': '#27ae60',
        'AT_RISK': '#f39c12',
        'BREACH': '#e74c3c'
    }

    risk_colors = {
        'HIGH': '#e74c3c',
        'MEDIUM': '#f39c12',
        'LOW': '#27ae60'
    }

    # Get status color and text based on the stats dictionary
    status_color, status_text = status_colors.get(stats['status'], status_colors['NO_DATA'])

    # Trend analysis section HTML - Enhanced with all available data
    trend_section = ""
    if trends_data and trends_data.get('days_analyzed', 0) >= 2:
        trend_status = stats.get('trend_status', 'STABLE')
        trend_color, trend_text = trend_colors.get(trend_status, trend_colors['STABLE'])
        trend_arrow = '⬇️' if stats.get('error_trend', 0) < 0 else '⬆️' if stats.get('error_trend', 0) > 0 else '➡️'
        
        # Determine momentum and stability info
        momentum = trends_data.get('momentum', 'INSUFFICIENT_DATA')
        momentum_color = momentum_colors.get(momentum, momentum_colors['INSUFFICIENT_DATA'])
        
        stability = trends_data.get('stability_trend', 'INSUFFICIENT_DATA')
        stability_color = stability_colors.get(stability, stability_colors['INSUFFICIENT_DATA'])
        
        # Prediction section with multiple models
        prediction_consensus = stats.get('predicted_errors_consensus', 0)
        prediction_simple = stats.get('predicted_errors_simple', 0)
        prediction_moving_avg = stats.get('predicted_errors_moving_avg', 0)
        prediction_regression = stats.get('predicted_errors_regression', 0)
        
        error_margin_lower = stats.get('error_margin_lower', 0)
        error_margin_upper = stats.get('error_margin_upper', 0)
        confidence_level = stats.get('confidence_level', 0)
        prediction_accuracy = stats.get('prediction_accuracy', 'N/A')

        # Seasonal patterns and anomalies
        seasonal_info = ""
        if trends_data.get('seasonal_patterns'):
            seasonal_info = f"<div class='trend-item'><strong>Seasonal Patterns:</strong> <span>{len(trends_data['seasonal_patterns'])} pattern(s) detected</span></div>"
        
        anomalies_info = ""
        if trends_data.get('anomalies_detected'):
            anomalies_count = len(trends_data['anomalies_detected'])
            anomalies_info = f"<div class='trend-item'><strong>Anomalies Detected:</strong> <span style='color: #e74c3c;'>{anomalies_count} anomaly/ies</span></div>"

        # Data quality score
        quality_score = trends_data.get('data_quality_score', 0)
        quality_color = '#27ae60' if quality_score > 80 else '#f39c12' if quality_score > 60 else '#e74c3c'

        trend_section = f"""
        <div class="trend-analysis">
            <h3>{trend_arrow} Advanced Trend Analysis (Last days)</h3>
            <div class="analysis-period">
                <p><strong>Analysis Period:</strong> {trends_data.get('analysis_period', 'N/A')}</p>
                <p><strong>Data Quality Score:</strong> <span style="color: {quality_color}; font-weight: bold;">{quality_score}%</span></p>
            </div>
            
            <div class="trend-grid">
                <div class="trend-item"><strong>Current Trend:</strong> <span style="color: {trend_color}; font-weight: bold;">{trend_text}</span></div>
                <div class="trend-item"><strong>Error Change (Day-1):</strong> <span style="color: {trend_color};">{stats.get('error_trend', 0):+d}</span> ({stats.get('improvement_rate', 0):+.1f}%)</div>
                <div class="trend-item"><strong>7-Day Avg Trend:</strong> <span style="color: {trend_color};">{trends_data.get('week_trend', 0):+.1f} avg</span></div>
                <div class="trend-item"><strong>Reliability Trend:</strong> <span style="color: {trend_color};">{stats.get('reliability_trend', 0):+.1f}%</span></div>
                <div class="trend-item"><strong>Momentum:</strong> <span style="color: {momentum_color}; font-weight: bold;">{momentum.replace('_', ' ')}</span></div>
                <div class="trend-item"><strong>Volatility:</strong> <span style="color: {stability_color}; font-weight: bold;">{stability.replace('_', ' ')}</span> ({trends_data.get('volatility', 0):.2f})</div>
                {seasonal_info}
                {anomalies_info}
            </div>

            <div class="prediction-section">
                <h4>🔮 Predictive Analytics</h4>
                <div class="prediction-grid">
                    <div class="prediction-item">
                        <strong>Consensus Prediction:</strong> 
                        <span style="color: {momentum_colors.get(momentum, 'black')}; font-weight: bold;">
                            {prediction_consensus} errors (±{stats.get('error_margin_range', 0)})
                        </span>
                    </div>
                    <div class="prediction-item">
                        <strong>Confidence Interval:</strong> 
                        <span>[{error_margin_lower} - {error_margin_upper}] errors</span>
                    </div>
                    <div class="prediction-item">
                        <strong>Confidence Level:</strong> 
                        <span style="font-weight: bold;">{confidence_level}%</span>
                    </div>
                    <div class="prediction-item">
                        <strong>Model Accuracy:</strong> 
                        <span>{prediction_accuracy}</span>
                    </div>
                </div>
                
                <div class="model-details">
                    <h5>Model Predictions Breakdown:</h5>
                    <ul>
                        <li><strong>Simple Linear:</strong> {prediction_simple} errors</li>
                        <li><strong>Moving Average:</strong> {prediction_moving_avg} errors</li>
                        <li><strong>Regression:</strong> {prediction_regression} errors</li>
                    </ul>
                </div>
            </div>
        </div>
        """
    
    # Enhanced recommendations based on all available data
    recommendation_list = []
    
    # Status-based recommendations
    if stats['status'] == 'CRITICAL':
        recommendation_list.append(f"<li>🚨 <strong>CRITICAL ALERT:</strong> Immediate action required. Investigate the <strong>{stats.get('critical_services', 0)} critical services</strong> with error counts ≥10.</li>")
    if stats['status'] == 'WARNING' and stats['affected_services'] > 0:
        recommendation_list.append(f"<li>⚠️ <strong>WARNING:</strong> System instability detected. Prioritize analysis of <strong>{stats.get('affected_services', 0)} affected services</strong>.</li>")
    
    # Trend-based recommendations
    if stats.get('trend_status') == 'DEGRADING':
        recommendation_list.append(f"<li>📉 <strong>DEGRADING TREND:</strong> Error count increasing by {stats.get('error_trend', 0):+d} since last period. Implement corrective measures immediately.</li>")
    if stats.get('momentum') == 'ACCELERATING':
        recommendation_list.append(f"<li>🔥 <strong>ACCELERATING ISSUES:</strong> Error growth rate is increasing. Swift intervention crucial to prevent critical escalation.</li>")
    
    # Volatility and stability recommendations
    if stats.get('stability_trend') == 'HIGH_VOLATILITY':
        recommendation_list.append(f"<li>📊 <strong>HIGH VOLATILITY:</strong> System showing erratic behavior (volatility: {trends_data.get('volatility', 0):.2f}). Investigate intermittent issues.</li>")
    
    # SLA and business impact recommendations
    if stats.get('sla_status') == 'BREACH':
        recommendation_list.append(f"<li>🔴 <strong>SLA BREACH:</strong> Uptime at {stats.get('uptime_percentage', 0)}%. Immediate escalation to management required.</li>")
    elif stats.get('sla_status') == 'AT_RISK':
        recommendation_list.append(f"<li>🟡 <strong>SLA AT RISK:</strong> Uptime at {stats.get('uptime_percentage', 0)}%. Monitor closely to prevent SLA breach.</li>")
    
    # Risk level recommendations
    if stats.get('risk_level') == 'HIGH':
        recommendation_list.append(f"<li>⚡ <strong>HIGH RISK DETECTED:</strong> Business impact assessed as {stats.get('business_impact', 'UNKNOWN')}. Activate incident response procedures.</li>")
    
    # Predictive recommendations
    if trends_data and stats.get('predicted_errors_consensus', 0) > stats.get('total_errors', 0):
        recommendation_list.append(f"<li>🔮 <strong>PREDICTIVE ALERT:</strong> Models predict {stats.get('predicted_errors_consensus', 0)} errors tomorrow (vs {stats.get('total_errors', 0)} today). Proactive monitoring recommended.</li>")
    
    # Anomaly recommendations
    if trends_data and trends_data.get('anomalies_detected'):
        anomaly_count = len(trends_data['anomalies_detected'])
        recommendation_list.append(f"<li>🔍 <strong>ANOMALIES DETECTED:</strong> {anomaly_count} unusual pattern(s) identified. Review historical data for root cause analysis.</li>")
    
    # Default healthy state recommendation
    if not recommendation_list:
        recommendation_list.append("<li>✅ <strong>SYSTEM HEALTHY:</strong> All indicators within normal ranges. Continue routine monitoring and maintenance for optimal performance.</li>")

    # Add recommended action from trends data if available
    recommended_action = stats.get('recommended_action', 'NO_DATA')
    if recommended_action and recommended_action != 'NO_DATA':
        recommendation_list.append(f"<li>🎯 <strong>RECOMMENDED ACTION:</strong> {recommended_action}</li>")

    recommendation_html = "".join(recommendation_list)

    # Enhanced service lists with error counts
    affected_services_html = "<p>No affected services.</p>"
    if stats.get('affected_services_list'):
        affected_services_html = "<ul>" + "".join([f"<li>{service}</li>" for service in stats['affected_services_list']]) + "</ul>"

    critical_services_html = "<p>No critical services.</p>"
    if stats.get('critical_services_list'):
        critical_services_html = "<ul>" + "".join([f"<li style='color: #e74c3c; font-weight: bold;'>{service} (≥10 errors)</li>" for service in stats['critical_services_list']]) + "</ul>"

    # Error distribution visualization
    error_dist = stats.get('error_distribution', {})
    error_dist_html = ""
    if error_dist:
        error_dist_html = f"""
        <div class="error-distribution">
            <h4>📊 Error Distribution Analysis</h4>
            <div class="distribution-grid">
                <div class="dist-item">
                    <div class="dist-number success">{error_dist.get('zero_errors', 0)}</div>
                    <div class="dist-label">Zero Errors</div>
                </div>
                <div class="dist-item">
                    <div class="dist-number warning">{error_dist.get('low_errors', 0)}</div>
                    <div class="dist-label">Low (1-5)</div>
                </div>
                <div class="dist-item">
                    <div class="dist-number danger">{error_dist.get('medium_errors', 0)}</div>
                    <div class="dist-label">Medium (6-10)</div>
                </div>
                <div class="dist-item">
                    <div class="dist-number danger">{error_dist.get('high_errors', 0)}</div>
                    <div class="dist-label">High (>10)</div>
                </div>
            </div>
        </div>
        """

    # Return the complete HTML document as a single string
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>{system_name} - Advanced System Health Report</title>
        <style>
            body {{ 
                font-family: 'Inter', 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif; 
                margin: 0; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                color: #2d3748;
            }}
            .container {{ 
                max-width: 1400px; 
                margin: 20px auto; 
                background: rgba(255, 255, 255, 0.95); 
                border-radius: 24px; 
                backdrop-filter: blur(20px);
                box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25), 0 0 0 1px rgba(255, 255, 255, 0.1);
                overflow: hidden;
            }}
            .header {{ 
                background: linear-gradient(145deg, rgba(255,255,255,0.1), rgba(255,255,255,0.05)); 
                color: #1a202c; 
                padding: 50px 40px; 
                text-align: center; 
                position: relative;
                overflow: hidden;
            }}
            .header::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.03'%3E%3Cpath d='M30 30c0-11.046-8.954-20-20-20s-20 8.954-20 20 8.954 20 20 20 20-8.954 20-20zM0 0h20v20H0V0zm40 40h20v20H40V40z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E") repeat;
                opacity: 0.1;
            }}
            .header h1 {{ 
                font-size: 2.8rem; 
                margin: 0 0 15px; 
                font-weight: 800; 
                background: linear-gradient(135deg, #667eea, #764ba2);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                position: relative;
                z-index: 1;
            }}
            .header p {{
                position: relative;
                z-index: 1;
                font-size: 1.1rem;
                opacity: 0.9;
            }}
            .status-badge {{ 
                background: {status_color}; 
                color: white; 
                padding: 14px 28px; 
                border-radius: 50px; 
                font-weight: 700; 
                margin-top: 20px; 
                display: inline-block;
                box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.2);
                position: relative;
                z-index: 1;
            }}
            .content {{ 
                padding: 50px; 
                line-height: 1.6; 
            }}
            .intro {{ 
                background: linear-gradient(145deg, #f7fafc, #edf2f7);
                padding: 30px; 
                border-radius: 18px; 
                margin-bottom: 30px;
                box-shadow: 
                    12px 12px 24px #d1d9e6,
                    -12px -12px 24px #ffffff,
                    inset 1px 1px 3px rgba(255,255,255,0.8);
                border: 1px solid rgba(255, 255, 255, 0.3);
            }}
            .intro h2 {{ margin-top: 0; color: #2c3e50; }}
            
            /* Trend Analysis Styles */
            .trend-analysis {{
                background: linear-gradient(145deg, #e8f5e8, #d4f4dd);
                padding: 30px;
                border-radius: 18px;
                margin: 30px 0;
                border-left: 5px solid #27ae60;
            }}
            .analysis-period {{
                background: rgba(255,255,255,0.7);
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 20px;
            }}
            .trend-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 15px;
                margin: 20px 0;
            }}
            .trend-item {{
                background: rgba(255,255,255,0.8);
                padding: 15px;
                border-radius: 8px;
                border-left: 3px solid #3498db;
            }}
            .prediction-section {{
                background: linear-gradient(145deg, #f0f4ff, #e6f0ff);
                padding: 25px;
                border-radius: 12px;
                margin-top: 20px;
                border: 1px solid rgba(52, 152, 219, 0.2);
            }}
            .prediction-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin: 15px 0;
            }}
            .prediction-item {{
                background: rgba(255,255,255,0.8);
                padding: 12px;
                border-radius: 6px;
                border-left: 2px solid #9b59b6;
            }}
            .model-details {{
                margin-top: 20px;
                padding: 15px;
                background: rgba(255,255,255,0.6);
                border-radius: 8px;
            }}
            .model-details ul {{
                margin: 0;
                padding-left: 20px;
            }}
            
            /* Stats Grid Styles */
            .stats-grid {{ 
                display: flex; 
                flex-wrap: wrap;
                gap: 15px; 
                margin: 30px 0; 
                justify-content: space-between;
            }}
            .stat-card {{ 
                background: linear-gradient(135deg, #f8f9fa, #e9ecef); 
                padding: 20px; 
                border-radius: 12px; 
                text-align: center; 
                border-left: 4px solid #3498db; 
                transition: transform 0.2s;
                flex: 1;
                min-width: 150px;
                max-width: 180px;
            }}
            .stat-card:hover {{ transform: translateY(-5px); box-shadow: 0 4px 15px rgba(0,0,0,0.1); }}
            .stat-number {{ font-size: 2rem; font-weight: 700; color: #2c3e50; margin-bottom: 8px; }}
            .stat-label {{ font-size: 0.8rem; color: #7f8c8d; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; }}
            
            /* Advanced Stats Grid */
            .advanced-stats-grid {{ 
                display: flex; 
                flex-wrap: wrap;
                gap: 20px; 
                margin: 30px 0; 
                justify-content: space-between;
            }}
            .advanced-stat-card {{ 
                background: linear-gradient(135deg, #f8f9fa, #e9ecef); 
                padding: 25px; 
                border-radius: 12px; 
                text-align: center; 
                transition: transform 0.2s;
                flex: 1;
                min-width: 180px;
                max-width: 220px;
            }}
            .advanced-stat-card:hover {{ transform: translateY(-5px); box-shadow: 0 4px 15px rgba(0,0,0,0.1); }}
            
            /* Error Distribution Styles */
            .error-distribution {{
                background: linear-gradient(145deg, #fff5f5, #fed7d7);
                padding: 25px;
                border-radius: 12px;
                margin: 20px 0;
                border-left: 4px solid #e53e3e;
            }}
            .distribution-grid {{
                display: flex;
                gap: 20px;
                justify-content: space-around;
                margin-top: 15px;
                flex-wrap: wrap;
            }}
            .dist-item {{
                text-align: center;
                flex: 1;
                min-width: 100px;
            }}
            .dist-number {{
                font-size: 1.8rem;
                font-weight: 700;
                margin-bottom: 5px;
            }}
            .dist-label {{
                font-size: 0.9rem;
                color: #666;
                font-weight: 600;
            }}
            
            /* Color Classes */
            .danger {{ color: #e74c3c !important; }}
            .success {{ color: #27ae60 !important; }}
            .warning {{ color: #f39c12 !important; }}
            .high {{ color: #e74c3c !important; }}
            .medium {{ color: #f39c12 !important; }}
            .low {{ color: #27ae60 !important; }}
            
            /* Recommendations */
            .recommendations {{ 
                background: linear-gradient(135deg, #d4edda, #c3e6cb); 
                color: #155724; 
                padding: 30px; 
                border-radius: 12px; 
                margin: 30px 0; 
                border: 1px solid #c3e6cb; 
            }}
            .recommendations h3 {{ margin-bottom: 20px; font-size: 1.4rem; color: #155724; }}
            .recommendations ul {{ padding-left: 20px; }}
            .recommendations li {{ margin-bottom: 15px; font-weight: 500; line-height: 1.5; }}
            
            /* Service Lists */
            .service-lists-container {{ 
                display: flex; 
                justify-content: space-around; 
                gap: 30px; 
                margin-top: 30px; 
                flex-wrap: wrap;
            }}
            .service-list-card {{ 
                flex: 1; 
                background: #fff; 
                padding: 25px; 
                border-radius: 12px; 
                box-shadow: 0 4px 12px rgba(0,0,0,0.08);
                min-width: 300px;
            }}
            .service-list-card h4 {{ margin-top: 0; border-bottom: 2px solid #ecf0f1; padding-bottom: 10px; }}
            .service-list-card ul {{ list-style-type: none; padding: 0; margin: 0; }}
            .service-list-card li {{ padding: 8px 0; border-bottom: 1px solid #eee; }}
            .service-list-card li:last-child {{ border-bottom: none; }}
            
            /* Footer */
            .footer {{ 
                background: #2c3e50; 
                color: white; 
                padding: 25px; 
                text-align: center; 
            }}
            
            /* Responsive Design */
            @media (max-width: 1200px) {{
                .stats-grid, .advanced-stats-grid {{
                    justify-content: center;
                }}
                .trend-grid, .prediction-grid {{
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                }}
            }}
            
            @media (max-width: 768px) {{
                .stats-grid, .advanced-stats-grid {{
                    flex-direction: column;
                    align-items: center;
                }}
                .stat-card, .advanced-stat-card {{
                    max-width: 300px;
                    width: 100%;
                }}
                .service-lists-container {{
                    flex-direction: column;
                }}
                .distribution-grid {{
                    flex-direction: column;
                    gap: 10px;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>System {system_name}</h1>
                <p>Advanced Error Analysis & Predictive Intelligence Report - {date_str}</p>
                <div class="status-badge">{status_text}</div>
            </div>
            
            <div class="content">
                <div class="intro">
                    <h2>🔎 Executive Summary</h2>
                    <p>
                        This comprehensive report provides an advanced analysis of the errors and incidents on the
                        <strong>{system_name}</strong> system, enhanced with predictive analytics and trend intelligence.
                        The analysis includes historical trends, anomaly detection, seasonal patterns, and machine learning-based
                        predictions to provide actionable insights for system optimization.
                    </p>
                    <p>
                        <strong>Current System Status:</strong> {status_text.split(' ', 1)[1]} | 
                        <strong>Risk Level:</strong> <span class="{stats.get('risk_level', '').lower()}">{stats.get('risk_level', 'N/A')}</span> | 
                        <strong>Business Impact:</strong> {stats.get('business_impact', 'N/A')} |
                        <strong>SLA Status:</strong> <span style="color: {sla_colors.get(stats.get('sla_status', 'MEETING'), '#000')};">{stats.get('sla_status', 'N/A')}</span>
                    </p>
                </div>
                
                {trend_section}

                <h2>📊 Key Performance Indicators</h2>
                <p>
                    Comprehensive metrics providing immediate insight into system health, service availability,
                    and operational efficiency. These indicators form the foundation for strategic decision-making.
                </p>
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-number {'danger' if stats['total_errors'] > 0 else 'success'}">{stats.get('total_errors', 0)}</div>
                        <div class="stat-label">Total Errors</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{stats.get('total_services', 0)}</div>
                        <div class="stat-label">Total Services</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number {'danger' if stats['affected_services'] > 0 else 'success'}">{stats.get('affected_services', 0)}</div>
                        <div class="stat-label">Affected Services</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number {'danger' if stats['critical_services'] > 0 else 'success'}">{stats.get('critical_services', 0)}</div>
                        <div class="stat-label">Critical Services</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number {'warning' if stats['avg_errors'] > 2 else 'success'}">{stats.get('avg_errors', 0)}</div>
                        <div class="stat-label">Avg Errors/Service</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number {'success' if stats['health_percentage'] > 80 else 'warning' if stats['health_percentage'] > 60 else 'danger'}">{stats.get('health_percentage', 0)}%</div>
                        <div class="stat-label">Health Rate</div>
                    </div>
                </div>

                <h2>📈 Advanced Analytics & Intelligence</h2>
                <div class="advanced-stats-grid">
                    <div class="advanced-stat-card" style="border-left: 4px solid #f1c40f;">
                        <div class="stat-number">{stats.get('top_error_service', 'N/A')}</div>
                        <div class="stat-label">Top Error Service</div>
                    </div>
                    <div class="advanced-stat-card" style="border-left: 4px solid {risk_colors.get(stats.get('risk_level', 'LOW'), '#27ae60')};">
                        <div class="stat-number">
                            <span class="{stats.get('risk_level', '').lower()}">{stats.get('risk_level', 'N/A')}</span>
                        </div>
                        <div class="stat-label">Risk Level</div>
                    </div>
                    <div class="advanced-stat-card" style="border-left: 4px solid #2ecc71;">
                        <div class="stat-number {'success' if stats.get('stability_index', 0) > 70 else 'warning' if stats.get('stability_index', 0) > 50 else 'danger'}">{stats.get('stability_index', 0)}</div>
                        <div class="stat-label">Stability Index (0-100)</div>
                    </div>
                    <div class="advanced-stat-card" style="border-left: 4px solid {sla_colors.get(stats.get('sla_status', 'MEETING'), '#27ae60')};">
                        <div class="stat-number {'success' if stats.get('uptime_percentage', 0) >= 99.5 else 'warning' if stats.get('uptime_percentage', 0) >= 95 else 'danger'}">{stats.get('uptime_percentage', 0):.2f}%</div>
                        <div class="stat-label">Uptime Percentage</div>
                    </div>
                    <div class="advanced-stat-card" style="border-left: 4px solid #9b59b6;">
                        <div class="stat-number">{stats.get('error_density', 0):.2f}</div>
                        <div class="stat-label">Error Density</div>
                    </div>
                    <div class="advanced-stat-card" style="border-left: 4px solid #e67e22;">
                        <div class="stat-number {'danger' if stats.get('critical_ratio', 0) > 20 else 'warning' if stats.get('critical_ratio', 0) > 10 else 'success'}">{stats.get('critical_ratio', 0)}%</div>
                        <div class="stat-label">Critical Service Ratio</div>
                    </div>
                </div>

                {error_dist_html}
                
                <h2>📋 Service Impact Analysis</h2>
                <p>
                    Detailed breakdown of affected services with severity classification. This analysis helps prioritize 
                    remediation efforts and resource allocation for maximum impact reduction.
                </p>
                <div class="service-lists-container">
                    <div class="service-list-card">
                        <h4 style="color: #f39c12;">⚠️ Services Affected ({stats.get('affected_services', 0)})</h4>
                        <p><small>Services experiencing at least one error</small></p>
                        {affected_services_html}
                    </div>
                    <div class="service-list-card">
                        <h4 style="color: #e74c3c;">🔴 Critical Services ({stats.get('critical_services', 0)})</h4>
                        <p><small>Services with 10 or more errors requiring immediate attention</small></p>
                        {critical_services_html}
                    </div>
                </div>
                
                <div class="recommendations">
                    <h3>🎯 Strategic Action Plan & Recommendations</h3>
                    <p>
                        Based on comprehensive analysis of current state, historical trends, predictive models, and risk assessment,
                        the following strategic recommendations have been generated to optimize system performance and minimize business impact.
                    </p>
                    <ul>
                        {recommendation_html}
                    </ul>
                    
                    <div style="margin-top: 25px; padding: 20px; background: rgba(255,255,255,0.8); border-radius: 8px;">
                        <h4 style="margin-top: 0; color: #2c3e50;">📊 Decision Support Metrics</h4>
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
                            <div><strong>Business Impact:</strong> <span class="{stats.get('business_impact', '').lower()}">{stats.get('business_impact', 'N/A')}</span></div>
                            <div><strong>Predicted Trend:</strong> <span style="color: {trend_colors.get(stats.get('trend_status', 'STABLE'), '#3498db')[0]};">{stats.get('trend_status', 'N/A')}</span></div>
                            <div><strong>Response Priority:</strong> <span class="{'danger' if stats.get('risk_level') == 'HIGH' else 'warning' if stats.get('risk_level') == 'MEDIUM' else 'success'}">{stats.get('risk_level', 'LOW')} PRIORITY</span></div>
                            <div><strong>Confidence Level:</strong> {stats.get('confidence_level', 0)}%</div>
                        </div>
                    </div>
                </div>
                
                <div style="background: linear-gradient(145deg, #f8f9fa, #e9ecef); padding: 25px; border-radius: 12px; margin: 30px 0;">
                    <h3>📈 Historical Context & Data Quality</h3>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px;">
                        <div>
                            <strong>Analysis Period:</strong><br>
                            <span style="color: #666;">{trends_data.get('analysis_period', 'Current snapshot only') if trends_data else 'Current snapshot only'}</span>
                        </div>
                        <div>
                            <strong>Data Points Analyzed:</strong><br>
                            <span style="color: #666;">{trends_data.get('days_analyzed', 1) if trends_data else 1} data point(s)</span>
                        </div>
                        <div>
                            <strong>Data Quality Score:</strong><br>
                            <span style="color: {quality_color if trends_data else '#95a5a6'};">{trends_data.get('data_quality_score', 'N/A') if trends_data else 'N/A'}{'%' if trends_data and trends_data.get('data_quality_score') else ''}</span>
                        </div>
                        <div>
                            <strong>Report Generation:</strong><br>
                            <span style="color: #666;">{date_str}</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="footer">
                <p><strong>🚀 Enhanced MTN Monitoring System v2.0</strong> | AI-Powered Analytics & Predictive Intelligence</p>
                <p>📧 For urgent issues: Contact monitoring team immediately | 🔔 Automated alerts configured</p>
                <p><small>Report includes: Trend Analysis • Predictive Models • Anomaly Detection • Risk Assessment • Business Impact Analysis</small></p>
            </div>
        </div>
    </body>
    </html>
    """


def generate_daily_reports_with_trends():
    """Génère les rapports avec analyse de tendance"""
    print(f"=== GÉNÉRATION DES RAPPORTS AVEC ANALYSE DE TENDANCE ===")
    print(f"Démarrage: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    date_str = datetime.now().strftime('%Y-%m-%d')
    systems_data = {}
    all_stats = {}
    
    systems_config = [
        ('CIS', CIS_ERROR_REPORT_OUTPUT_DIR, '🔴'),
        ('ECW', ECW_ERROR_REPORT_OUTPUT_DIR, '🟢'),
        ('IRM', IRM_ERROR_REPORT_OUTPUT_DIR, '🟡')
    ]
    
    for system_name, directory, icon in systems_config:
        print(f"\n{icon} Traitement système {system_name}...")
        
        # Données actuelles
        current_file = get_latest_csv_file(directory)
        current_data = None
        trends_data = None
        
        if current_file:
            current_data = read_csv_data(current_file, system_name)
            # Analyse de tendance
            trends_data = analyze_historical_trends(directory, system_name, days=7)
            
            if current_data is not None:
                systems_data[system_name] = current_data
                stats = calculate_enhanced_stats(current_data, system_name, trends_data)
                all_stats[system_name] = stats
                
                # Génération du rapport HTML
                html_body = create_professional_system_html_with_trends(
                    system_name, current_data, stats, date_str, trends_data
                )
                
                # Graphiques
                charts = []
                # Graphique de tendance
                if trends_data:
                    trend_chart = create_trend_chart(directory, trends_data, system_name)
                    if trend_chart:
                        charts.append(trend_chart)
                
                # Envoi du rapport
                recipients_key = f'{system_name.lower()}_recipients'
                trend_indicator = "📈" if stats.get('error_trend', 0) < 0 else "📉" if stats.get('error_trend', 0) > 0 else "➡️"
                
                send_email_with_reports(
                    EMAIL_CONFIG['from_email'],
                    EMAIL_CONFIG[recipients_key],
                    f"{icon} {system_name} SYSTEM REPORT {trend_indicator} - {date_str}",
                    html_body,
                    charts
                )
                
                print(f"   ✓ Rapport {system_name} envoyé")
                print(f"   📊 Statut: {stats['status']}")
                if 'error_trend' in stats:
                    print(f"   📈 Tendance: {stats['error_trend']:+d} erreurs ({stats['improvement_rate']:+.1f}%)")
            else:
                all_stats[system_name] = calculate_enhanced_stats(None, system_name)
                print(f"   ⚠ Aucune donnée {system_name} trouvée")
        else:
            all_stats[system_name] = calculate_enhanced_stats(None, system_name)
            print(f"   ⚠ Fichier {system_name} non trouvé")
    
    # Rapport de synthèse (code existant adapté)
    print("\n📊 Génération du rapport de synthèse...")
    if all_stats:
        # Utilisation des fonctions existantes pour la synthèse
        summary_html = create_executive_summary_html_with_trends(systems_data, all_stats, date_str)
        
        # Déterminer priorité
        critical_count = sum(1 for stats in all_stats.values() if stats.get('status') == 'CRITICAL')
        improving_count = sum(1 for stats in all_stats.values() if stats.get('error_trend', 0) < 0)
        
        if critical_count > 0:
            priority = "🚨 URGENT"
        elif improving_count > 0:
            priority = "📈 IMPROVING"
        else:
            priority = "📊 MONITORING"
        
        send_email_with_reports(
            EMAIL_CONFIG['from_email'],
            EMAIL_CONFIG['summary_recipients'],
            f"{priority} - EXECUTIVE SUMMARY WITH TRENDS - {date_str}",
            summary_html,
            []
        )
        print("   ✓ Rapport de synthèse envoyé")
    
    # Résumé final
    print(f"\n{'='*60}")
    print("📊 RÉSUMÉ AVEC ANALYSE DE TENDANCE:")
    print(f"{'='*60}")
    
    for system, stats in all_stats.items():
        status_icon = {'HEALTHY': '✅', 'WARNING': '⚠️', 'CRITICAL': '🚨', 'NO_DATA': '⚪'}[stats.get('status', 'NO_DATA')]
        trend_icon = '📈' if stats.get('error_trend', 0) < 0 else '📉' if stats.get('error_trend', 0) > 0 else '➡️'
        print(f"   {status_icon} {system}: {stats.get('total_errors', 0)} erreurs {trend_icon} ({stats.get('error_trend', 0):+d})")
    
    print(f"\n✅ RAPPORTS AVEC ANALYSE DE TENDANCE GÉNÉRÉS!")
    print(f"⏰ Terminé: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

#
# Generates an enhanced executive summary HTML report with trend analysis.
#
from datetime import datetime
from datetime import timedelta

def create_executive_summary_html_with_trends(systems_data, all_stats, date_str):
    """Enhanced version of the executive summary with comprehensive trends and predictions"""
    
    # Global calculations
    total_errors = sum(stats.get('total_errors', 0) for stats in all_stats.values())
    total_services_monitored = sum(stats.get('total_services', 0) for stats in all_stats.values())
    improving_systems = sum(1 for stats in all_stats.values() if stats.get('error_trend', 0) < 0)
    degrading_systems = sum(1 for stats in all_stats.values() if stats.get('error_trend', 0) > 0)
    
    total_affected_services = sum(len(stats.get('affected_services_list', [])) for stats in all_stats.values())
    total_critical_services = sum(len(stats.get('critical_services_list', [])) for stats in all_stats.values())
    
    # Nouvelles métriques globales
    avg_stability_index = sum(stats.get('stability_index', 0) for stats in all_stats.values()) / len(all_stats) if all_stats else 0
    avg_confidence_level = sum(stats.get('confidence_level', 0) for stats in all_stats.values()) / len(all_stats) if all_stats else 0
    total_predicted_errors = sum(stats.get('predicted_errors_consensus', 0) for stats in all_stats.values())
    high_risk_systems = sum(1 for stats in all_stats.values() if stats.get('risk_level') == 'HIGH')
    
    # Global status with trend
    if degrading_systems > improving_systems:
        global_status = "📉 SYSTEMS DEGRADING"
        global_class = "warning"
    elif improving_systems > 0:
        global_status = "📈 SYSTEMS IMPROVING"
        global_class = "success"
    else:
        global_status = "➡️ SYSTEMS STABLE"
        global_class = "info"
        
    # --- Collect enhanced lists ---
    # Top 5 degrading services with more details
    all_trends = []
    for system_name, stats in all_stats.items():
        if stats.get('error_trend', 0) > 0:
            degradation_amount = stats.get('error_trend', 0)
            volatility = stats.get('volatility', 0)
            risk_level = stats.get('risk_level', 'UNKNOWN')
            all_trends.append({
                'system': system_name, 
                'errors': degradation_amount,
                'volatility': volatility,
                'risk': risk_level
            })

    top_degrading_systems = sorted(all_trends, key=lambda x: x['errors'], reverse=True)[:5]
    
    top_degrading_html = ""
    if top_degrading_systems:
        top_degrading_html = "<ul>" + "".join([
            f"<li><strong>{d['system']}</strong>: +{d['errors']} errors "
            f"<span style='color: #e53e3e; font-size: 0.8em;'>({d['risk']} RISK)</span>"
            f"<br/><small>Volatility: {d['volatility']:.1f}%</small></li>" 
            for d in top_degrading_systems
        ]) + "</ul>"
    else:
        top_degrading_html = "<p>No degrading systems identified.</p>"
    
    # Systems with high prediction accuracy
    high_accuracy_systems = []
    for system_name, stats in all_stats.items():
        if stats.get('prediction_confidence') == 'HIGH' or stats.get('confidence_level', 0) > 80:
            high_accuracy_systems.append({
                'system': system_name,
                'confidence': stats.get('confidence_level', 0),
                'predicted': stats.get('predicted_errors_consensus', 0),
                'accuracy': stats.get('prediction_accuracy', 'N/A')
            })
    
    high_accuracy_html = ""
    if high_accuracy_systems:
        high_accuracy_html = "<ul>" + "".join([
            f"<li><strong>{s['system']}</strong>: {s['confidence']:.1f}% confidence"
            f"<br/><small>Predicted: {s['predicted']} errors | Accuracy: {s['accuracy']}</small></li>"
            for s in high_accuracy_systems[:5]
        ]) + "</ul>"
    else:
        high_accuracy_html = "<p>Prediction models still learning from data patterns.</p>"
    
    # Global critical services list with enhanced info
    all_critical_services_list = []
    for system_name, stats in all_stats.items():
        for service in stats.get('critical_services_list', []):
            stability = stats.get('stability_index', 0)
            all_critical_services_list.append({
                'system': system_name,
                'service': service,
                'stability': stability
            })

    critical_services_html = ""
    if all_critical_services_list:
        critical_services_html = "<ul>" + "".join([
            f"<li>🚨 <strong>{s['system']}</strong>: {s['service']}"
            f"<br/><small>Stability: {s['stability']:.1f}/100</small></li>"
            for s in all_critical_services_list[:10]
        ]) + "</ul>"
    else:
        critical_services_html = "<p>No critical services found across all systems. Excellent!</p>"

    # Déterminer la couleur de confiance moyenne
    confidence_color = '#38a169' if avg_confidence_level > 80 else '#d69e2e' if avg_confidence_level > 50 else '#e53e3e'
    
    # --- Start HTML Generation ---
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ 
                font-family: 'Inter', 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif; 
                margin: 0; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                color: #2d3748;
            }}
            .container {{ 
                max-width: 1400px; 
                margin: 20px auto; 
                background: rgba(255, 255, 255, 0.95); 
                border-radius: 24px; 
                backdrop-filter: blur(20px);
                box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25), 0 0 0 1px rgba(255, 255, 255, 0.1);
                overflow: hidden;
            }}
            
            .header {{ 
                background: linear-gradient(135deg, rgba(255,255,255,0.1), rgba(255,255,255,0.05)); 
                color: #1a202c; 
                padding: 60px 50px; 
                text-align: center; 
                position: relative;
                overflow: hidden;
            }}
            .header::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.03'%3E%3Cpath d='M30 30c0-11.046-8.954-20-20-20s-20 8.954-20 20 8.954 20 20 20 20-8.954 20-20zM0 0h20v20H0V0zm40 40h20v20H40V40z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E") repeat;
                opacity: 0.1;
            }}
            .header h1 {{ 
                font-size: 3.2rem; 
                margin: 0 0 15px; 
                font-weight: 800; 
                background: linear-gradient(135deg, #667eea, #764ba2);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                position: relative;
                z-index: 1;
            }}
            .header p {{
                position: relative;
                z-index: 1;
            }}
            
            .global-status {{ 
                padding: 16px 32px; 
                border-radius: 50px; 
                font-weight: 700; 
                margin-top: 25px; 
                display: inline-block;
                box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.2);
                position: relative;
                z-index: 1;
            }}
            
            .content {{ 
                padding: 50px; 
            }}
            
            /* Enhanced Trend Summary */
            .trend-summary {{ 
                background: linear-gradient(145deg, #ffffff, #f7fafc);
                border-radius: 20px; 
                padding: 40px; 
                margin: 30px 0;
                box-shadow: 
                    20px 20px 60px #d1d9e6, 
                    -20px -20px 60px #ffffff,
                    inset 2px 2px 5px rgba(255,255,255,0.8),
                    inset -2px -2px 5px rgba(0,0,0,0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
            }}
            .trend-summary h3 {{
                margin: 0 0 30px 0; 
                font-size: 1.8rem;
                font-weight: 700;
                color: #2d3748;
                text-align: center;
                text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.8);
            }}
            
            /* Grid pour les métriques en plusieurs lignes */
            .trend-metrics-grid {{ 
                display: grid;
                grid-template-columns: repeat(5, 1fr);
                gap: 15px; 
                justify-items: center;
            }}
            .trend-metric-card {{ 
                width: 100%;
                text-align: center;
                padding: 20px 15px;
                background: linear-gradient(145deg, #f7fafc, #edf2f7);
                border-radius: 16px;
                box-shadow: 
                    6px 6px 12px #d1d9e6,
                    -6px -6px 12px #ffffff,
                    inset 1px 1px 2px rgba(255,255,255,0.8);
                transition: all 0.3s ease;
                border: 1px solid rgba(255, 255, 255, 0.3);
            }}
            .trend-metric-card:hover {{
                transform: translateY(-3px);
                box-shadow: 
                    8px 8px 16px #d1d9e6,
                    -8px -8px 16px #ffffff,
                    inset 2px 2px 4px rgba(255,255,255,0.9);
            }}
            .trend-metric-number {{
                font-size: 1.8rem; 
                font-weight: 800;
                color: #4a5568;
                text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.8);
                margin-bottom: 8px;
            }}
            .trend-metric-label {{
                font-size: 0.9rem;
                color: #718096;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            
            .systems-grid {{ 
                display: grid; 
                grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); 
                gap: 30px; 
                margin: 40px 0; 
            }}
            .system-card {{ 
                background: linear-gradient(145deg, #ffffff, #f7fafc);
                border-radius: 20px; 
                padding: 30px; 
                box-shadow: 
                    15px 15px 30px #d1d9e6, 
                    -15px -15px 30px #ffffff,
                    inset 1px 1px 3px rgba(255,255,255,0.8);
                transition: all 0.3s ease;
                border: 1px solid rgba(255, 255, 255, 0.2);
                position: relative;
                overflow: hidden;
            }}
            .system-card::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 4px;
                background: linear-gradient(90deg, #667eea, #764ba2);
                border-radius: 20px 20px 0 0;
            }}
            .system-card:hover {{ 
                transform: translateY(-8px); 
                box-shadow: 
                    20px 20px 40px #d1d9e6, 
                    -20px -20px 40px #ffffff,
                    inset 2px 2px 5px rgba(255,255,255,0.9);
            }}
            .system-name {{ 
                font-size: 1.4rem; 
                font-weight: 700; 
                margin-bottom: 20px; 
                color: #2d3748;
                text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.8);
            }}
            .trend-indicator {{ 
                font-size: 1rem; 
                margin: 15px 0; 
                padding: 10px 18px; 
                border-radius: 25px; 
                display: inline-block;
                font-weight: 600;
                box-shadow: inset 2px 2px 5px rgba(0,0,0,0.1), inset -2px -2px 5px rgba(255,255,255,0.8);
            }}
            .improving {{ 
                background: linear-gradient(145deg, #c6f6d5, #9ae6b4); 
                color: #22543d; 
            }}
            .degrading {{ 
                background: linear-gradient(145deg, #fed7d7, #feb2b2); 
                color: #742a2a; 
            }}
            .stable {{ 
                background: linear-gradient(145deg, #bee3f8, #90cdf4); 
                color: #2a4365; 
            }}
            .danger {{ color: #e53e3e; }}
            .success {{ color: #38a169; }}
            .warning {{ color: #d69e2e; }}
            .info {{ 
                color: #2b6cb0; 
                background: linear-gradient(145deg, #bee3f8, #90cdf4);
                box-shadow: inset 2px 2px 5px rgba(0,0,0,0.1), inset -2px -2px 5px rgba(255,255,255,0.8);
            }}
            
            .footer {{ 
                background: linear-gradient(145deg, #2d3748, #1a202c);
                color: black; 
                padding: 40px; 
                text-align: center;
                position: relative;
                overflow: hidden;
            }}
            .footer::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: linear-gradient(45deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
            }}
            .footer p {{
                position: relative;
                z-index: 1;
                text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.3);
            }}
            
            .list-section {{ 
                display: grid; 
                grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); 
                gap: 30px; 
                margin-top: 40px; 
            }}
            .list-card {{ 
                background: linear-gradient(145deg, #f7fafc, #edf2f7);
                padding: 30px; 
                border-radius: 18px; 
                box-shadow: 
                    12px 12px 24px #d1d9e6,
                    -12px -12px 24px #ffffff,
                    inset 1px 1px 3px rgba(255,255,255,0.8);
                border: 1px solid rgba(255, 255, 255, 0.3);
            }}
            .list-card h4 {{ 
                margin-top: 0; 
                color: #2d3748; 
                border-bottom: 2px solid rgba(102, 126, 234, 0.2);
                padding-bottom: 15px;
                text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.8);
                font-weight: 700;
            }}
            .list-card ul {{ 
                list-style-type: none; 
                padding: 0; 
                margin: 0; 
            }}
            .list-card li {{ 
                padding: 12px 0; 
                border-bottom: 1px solid rgba(0,0,0,0.05);
                font-size: 1rem;
                transition: all 0.2s ease;
            }}
            .list-card li:hover {{
                padding-left: 10px;
                color: #667eea;
            }}
            .list-card li:last-child {{ 
                border-bottom: none; 
            }}
            
            .recommendations {{
                background: linear-gradient(145deg, #fff5f5, #fed7d7);
                padding: 40px; 
                border-radius: 20px; 
                margin: 40px 0;
                box-shadow: 
                    15px 15px 30px #d1d9e6,
                    -15px -15px 30px #ffffff,
                    inset 1px 1px 3px rgba(255,255,255,0.8);
                border: 1px solid rgba(255, 255, 255, 0.3);
            }}
            .recommendations h3 {{
                font-size: 1.6rem; 
                margin-bottom: 25px;
                color: #742a2a;
                text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.8);
                font-weight: 700;
            }}
            
            .prediction-section {{
                background: linear-gradient(145deg, #f0fff4, #c6f6d5);
                padding: 40px; 
                border-radius: 20px; 
                margin: 40px 0;
                box-shadow: 
                    15px 15px 30px #d1d9e6,
                    -15px -15px 30px #ffffff,
                    inset 1px 1px 3px rgba(255,255,255,0.8);
                border: 1px solid rgba(255, 255, 255, 0.3);
            }}
            .prediction-section h3 {{
                font-size: 1.6rem; 
                margin-bottom: 25px;
                color: #22543d;
                text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.8);
                font-weight: 700;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📊 Executive Dashboard</h1>
                <p style="font-size: 1.3rem; opacity: 0.9; font-weight: 500;">All Systems Performance & Advanced Analytics</p>
                <p style="font-size: 1.1rem; opacity: 0.8;">{date_str}</p>
                <div class="global-status {global_class}">{global_status}</div>
            </div>
            
            <div class="content">
                <div class="trend-summary">
                    <h3>📈 Global Performance & Predictions Dashboard</h3>
                    <div class="trend-metrics-grid">
                        <div class="trend-metric-card">
                            <div class="trend-metric-number" style="color: #38a169;">{improving_systems}</div>
                            <div class="trend-metric-label">Systems Improving</div>
                        </div>
                        <div class="trend-metric-card">
                            <div class="trend-metric-number" style="color: #e53e3e;">{degrading_systems}</div>
                            <div class="trend-metric-label">Systems Degrading</div>
                        </div>
                        <div class="trend-metric-card">
                            <div class="trend-metric-number" style="color: #d69e2e;">{total_affected_services}</div>
                            <div class="trend-metric-label">Affected Services</div>
                        </div>
                        <div class="trend-metric-card">
                            <div class="trend-metric-number" style="color: #e53e3e;">{total_critical_services}</div>
                            <div class="trend-metric-label">Critical Services</div>
                        </div>
                        <div class="trend-metric-card">
                            <div class="trend-metric-number" style="color: #2b6cb0;">{total_errors}</div>
                            <div class="trend-metric-label">Current Errors</div>
                        </div>
                        <div class="trend-metric-card">
                            <div class="trend-metric-number" style="color: #4a5568;">{total_services_monitored}</div>
                            <div class="trend-metric-label">Services Monitored</div>
                        </div>
                        <div class="trend-metric-card">
                            <div class="trend-metric-number" style="color: #667eea;">{avg_stability_index:.1f}</div>
                            <div class="trend-metric-label">Avg Stability Index</div>
                        </div>
                        <div class="trend-metric-card">
                            <div class="trend-metric-number" style="color: #764ba2;">{avg_confidence_level:.1f}%</div>
                            <div class="trend-metric-label">Prediction Confidence</div>
                        </div>
                        <div class="trend-metric-card">
                            <div class="trend-metric-number" style="color: #e53e3e;">{high_risk_systems}</div>
                            <div class="trend-metric-label">High Risk Systems</div>
                        </div>
                        <div class="trend-metric-card">
                            <div class="trend-metric-number" style="color: #805ad5;">{int(total_predicted_errors)}</div>
                            <div class="trend-metric-label">Predicted Errors (24h)</div>
                        </div>
                    </div>
                </div>
                
                <h2 style="color: #2d3748; margin: 50px 0 30px; font-size: 2rem; font-weight: 700; text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.8);">🖥️ Systems Performance Dashboard</h2>
                <div class="systems-grid">
    """
    
    # Adding enhanced system cards with all new metrics
    for system_name, stats in all_stats.items():
        error_trend = stats.get('error_trend', 0)
        trend_class = 'improving' if error_trend < 0 else 'degrading' if error_trend > 0 else 'stable'
        trend_text = f'📈 -{abs(error_trend)} errors' if error_trend < 0 else f'📉 +{error_trend} errors' if error_trend > 0 else '➡️ No change'
        
        # Déterminer la couleur du statut de risque
        risk_color = {'HIGH': '#e53e3e', 'MEDIUM': '#d69e2e', 'LOW': '#38a169'}.get(stats.get('risk_level', 'UNKNOWN'), '#718096')
        
        # Déterminer l'indicateur de confiance des prédictions
        confidence_level = stats.get('confidence_level', 0)
        confidence_color = '#38a169' if confidence_level > 80 else '#d69e2e' if confidence_level > 50 else '#e53e3e'
        
        html += f"""
                    <div class="system-card">
                        <h3 class="system-name">{system_name} System</h3>
                        <div class="trend-indicator {trend_class}">
                            {trend_text} vs previous period
                        </div>
                        
                        <!-- Métriques principales -->
                        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin: 20px 0;">
                            <div style="text-align: center; padding: 15px; background: linear-gradient(145deg, #edf2f7, #e2e8f0); border-radius: 12px; box-shadow: inset 3px 3px 6px #d1d9e6, inset -3px -3px 6px #ffffff;">
                                <div style="font-size: 1.6rem; font-weight: 800; color: {'#e53e3e' if stats.get('total_errors', 0) > 0 else '#38a169'}; text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.8);">{stats.get('total_errors', 0)}</div>
                                <div style="font-size: 0.8rem; color: #718096; font-weight: 600;">Current Errors</div>
                            </div>
                            <div style="text-align: center; padding: 15px; background: linear-gradient(145deg, #edf2f7, #e2e8f0); border-radius: 12px; box-shadow: inset 3px 3px 6px #d1d9e6, inset -3px -3px 6px #ffffff;">
                                <div style="font-size: 1.6rem; font-weight: 800; color: #4a5568; text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.8);">{stats.get('health_percentage', 0):.1f}%</div>
                                <div style="font-size: 0.8rem; color: #718096; font-weight: 600;">Health Rate</div>
                            </div>
                            <div style="text-align: center; padding: 15px; background: linear-gradient(145deg, #edf2f7, #e2e8f0); border-radius: 12px; box-shadow: inset 3px 3px 6px #d1d9e6, inset -3px -3px 6px #ffffff;">
                                <div style="font-size: 1.6rem; font-weight: 800; color: #667eea; text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.8);">{stats.get('stability_index', 0):.1f}</div>
                                <div style="font-size: 0.8rem; color: #718096; font-weight: 600;">Stability Index</div>
                            </div>
                        </div>
                        
                        <!-- Prédictions et analyse avancée -->
                        <div style="background: linear-gradient(145deg, #f0fff4, #e6fffa); padding: 20px; border-radius: 12px; margin: 20px 0; box-shadow: inset 2px 2px 4px #d1d9e6, inset -2px -2px 4px #ffffff;">
                            <h4 style="margin: 0 0 15px; color: #22543d; font-size: 1.1rem;">🔮 Predictions & Analytics</h4>
                            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px;">
                                <div>
                                    <div style="font-size: 1.2rem; font-weight: 700; color: #805ad5;">{stats.get('predicted_errors_consensus', 0)}</div>
                                    <div style="font-size: 0.8rem; color: #718096;">Predicted Errors (24h)</div>
                                </div>
                                <div>
                                    <div style="font-size: 1.2rem; font-weight: 700; color: {confidence_color};">{stats.get('confidence_level', 0):.1f}%</div>
                                    <div style="font-size: 0.8rem; color: #718096;">Prediction Confidence</div>
                                </div>
                            </div>
                            {f'<div style="margin-top: 10px; font-size: 0.9rem; color: #4a5568;"><strong>Range:</strong> {stats.get("error_margin_lower", 0)} - {stats.get("error_margin_upper", 0)} errors</div>' if stats.get('error_margin_range', 0) > 0 else ''}
                        </div>
                        
                        <!-- Informations détaillées -->
                        <div style="margin-top: 20px; font-size: 0.95rem; color: #4a5568; line-height: 1.6;">
                            <div style="margin-bottom: 8px;">Critical Services: <span style="font-weight: 700; color: {'#e53e3e' if stats.get('critical_services', 0) > 0 else '#38a169'};">{stats.get('critical_services', 0)}</span></div>
                            <div style="margin-bottom: 8px;">Risk Level: <span style="font-weight: 700; color: {risk_color};">{stats.get('risk_level', 'UNKNOWN')}</span></div>
                            <div style="margin-bottom: 8px;">Most Impacted: <span style="font-weight: 700; color: #667eea;">{stats.get('top_error_service', 'N/A')}</span></div>
                            <div style="margin-bottom: 8px;">Volatility: <span style="font-weight: 700; color: #764ba2;">{stats.get('volatility', 0):.1f}%</span></div>
                            <div style="margin-bottom: 8px;">Momentum: <span style="font-weight: 700; color: #4299e1;">{stats.get('momentum', 'NEUTRAL')}</span></div>
                            {f'<div style="margin-bottom: 8px;">Weekly Trend: <span style="font-weight: 700; color: #764ba2;">{stats.get("improvement_rate", 0):+.1f}%</span></div>' if 'improvement_rate' in stats else ''}
                            {f'<div style="margin-bottom: 8px;">SLA Status: <span style="font-weight: 700; color: {"#38a169" if stats.get("sla_status") == "MEETING" else "#d69e2e" if stats.get("sla_status") == "AT_RISK" else "#e53e3e"};">{stats.get("sla_status", "N/A")}</span></div>' if 'sla_status' in stats else ''}
                            {f'<div style="margin-bottom: 8px;">Business Impact: <span style="font-weight: 700; color: {"#38a169" if stats.get("business_impact") == "MINIMAL" else "#d69e2e" if stats.get("business_impact") == "MODERATE" else "#e53e3e"};">{stats.get("business_impact", "UNKNOWN")}</span></div>' if 'business_impact' in stats else ''}
                        </div>
                        
                        <!-- Actions recommandées -->
                        {f'<div style="background: linear-gradient(145deg, #fff5f5, #fed7d7); padding: 15px; border-radius: 10px; margin-top: 20px; box-shadow: inset 1px 1px 2px #d1d9e6, inset -1px -1px 2px #ffffff;"><div style="font-size: 0.9rem; color: #742a2a; font-weight: 600;">💡 Recommended Action:</div><div style="font-size: 0.85rem; color: #4a5568; margin-top: 5px;">{stats.get("recommended_action", "Monitor closely")}</div></div>' if stats.get('recommended_action') and stats.get('recommended_action') != 'NO_DATA' else ''}
                    </div>
        """
    
    html += f"""
                </div>
                
                <!-- Section des prédictions globales -->
                <div class="prediction-section">
                    <h3>🔮 Global Predictions & Advanced Analytics</h3>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 30px;">
                        <div style="background: linear-gradient(145deg, #ffffff, #f7fafc); padding: 25px; border-radius: 16px; box-shadow: inset 3px 3px 6px #d1d9e6, inset -3px -3px 6px #ffffff;">
                            <h4 style="color: #22543d; margin-bottom: 15px; font-size: 1.2rem;">📊 Prediction Summary:</h4>
                            <div style="margin-bottom: 10px;">
                                <span style="font-size: 1.5rem; font-weight: 800; color: #805ad5;">{int(total_predicted_errors)}</span>
                                <span style="color: #718096; font-size: 0.9rem; margin-left: 8px;">Total predicted errors (next 24h)</span>
                            </div>
                            <div style="margin-bottom: 10px;">
                                <span style="font-size: 1.2rem; font-weight: 700; color: {confidence_color};">{avg_confidence_level:.1f}%</span>
                                <span style="color: #718096; font-size: 0.9rem; margin-left: 8px;">Average prediction confidence</span>
                            </div>
                            <div style="margin-bottom: 10px;">
                                <span style="font-size: 1.2rem; font-weight: 700; color: #4299e1;">{len([s for s in all_stats.values() if s.get('prediction_confidence') == 'HIGH'])}</span>
                                <span style="color: #718096; font-size: 0.9rem; margin-left: 8px;">Systems with high prediction accuracy</span>
                            </div>
                        </div>
                        <div style="background: linear-gradient(145deg, #ffffff, #f7fafc); padding: 25px; border-radius: 16px; box-shadow: inset 3px 3px 6px #d1d9e6, inset -3px -3px 6px #ffffff;">
                            <h4 style="color: #22543d; margin-bottom: 15px; font-size: 1.2rem;">⚡ Risk Assessment:</h4>
                            <div style="margin-bottom: 10px;">
                                <span style="font-size: 1.5rem; font-weight: 800; color: #e53e3e;">{high_risk_systems}</span>
                                <span style="color: #718096; font-size: 0.9rem; margin-left: 8px;">High-risk systems requiring attention</span>
                            </div>
                            <div style="margin-bottom: 10px;">
                                <span style="font-size: 1.2rem; font-weight: 700; color: #667eea;">{avg_stability_index:.1f}/100</span>
                                <span style="color: #718096; font-size: 0.9rem; margin-left: 8px;">Global stability index</span>
                            </div>
                            <div style="margin-bottom: 10px;">
                                <span style="font-size: 1.2rem; font-weight: 700; color: #4299e1;">{len([s for s in all_stats.values() if s.get('business_impact') == 'SEVERE'])}</span>
                                <span style="color: #718096; font-size: 0.9rem; margin-left: 8px;">Systems with severe business impact</span>
                            </div>
                        </div>
                    </div>
                </div>
                
                <h2 style="color: #2d3748; margin: 50px 0 30px; font-size: 2rem; font-weight: 700; text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.8);">❗ Actionable Insights & Analytics</h2>
                <div class="list-section">
                    <div class="list-card">
                        <h4 style="color: #e53e3e;">🔻 Top Degrading Systems ({len(top_degrading_systems)})</h4>
                        {top_degrading_html}
                    </div>
                    <div class="list-card">
                        <h4 style="color: #e53e3e;">🚨 Global Critical Services ({len(all_critical_services_list)})</h4>
                        {critical_services_html}
                    </div>
                    <div class="list-card">
                        <h4 style="color: #38a169;">🎯 High Accuracy Predictions ({len(high_accuracy_systems)})</h4>
                        {high_accuracy_html}
                    </div>
                </div>

                <div class="recommendations">
                    <h3>🎯 Strategic Recommendations & Action Plan</h3>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 30px;">
                        <div style="background: linear-gradient(145deg, #ffffff, #f7fafc; padding: 25px; border-radius: 16px; box-shadow: inset 3px 3px 6px #d1d9e6, inset -3px -3px 6px #ffffff;">
                            <h4 style="color: #742a2a; margin-bottom: 15px; font-size: 1.2rem;">⚡ Immediate Actions (Next 4 hours):</h4>
                            <ul style="margin: 0; padding-left: 20px; color: #2d3748;">
                                {'<li style="margin-bottom: 8px;">🔥 Investigate high-risk degrading systems immediately</li>' if degrading_systems > 0 and high_risk_systems > 0 else ''}
                                {'<li style="margin-bottom: 8px;">📊 Analyze systems with severe business impact</li>' if len([s for s in all_stats.values() if s.get('business_impact') == 'SEVERE']) > 0 else ''}
                                {'<li style="margin-bottom: 8px;">🔍 Review critical services requiring attention</li>' if total_critical_services > 0 else ''}
                                {'<li style="margin-bottom: 8px;">✅ Maintain current monitoring practices</li>' if degrading_systems == 0 and high_risk_systems == 0 else ''}
                                <li style="margin-bottom: 8px;">📈 Monitor prediction accuracy for model improvement</li>
                            </ul>
                        </div>
                        <div style="background: linear-gradient(145deg, #ffffff, #f7fafc); padding: 25px; border-radius: 16px; box-shadow: inset 3px 3px 6px #d1d9e6, inset -3px -3px 6px #ffffff;">
                            <h4 style="color: #742a2a; margin-bottom: 15px; font-size: 1.2rem;">📊 Strategic Insights (Next 24-48 hours):</h4>
                            <ul style="margin: 0; padding-left: 20px; color: #2d3748;">
                                {'<li style="margin-bottom: 8px;">🔄 Replicate improvement strategies from successful systems</li>' if improving_systems > 0 else ''}
                                <li style="margin-bottom: 8px;">🤖 Leverage high-confidence predictions for proactive maintenance</li>
                                <li style="margin-bottom: 8px;">📋 Document patterns in volatility and momentum changes</li>
                                <li style="margin-bottom: 8px;">🎯 Focus resources on systems with highest business impact</li>
                                {'<li style="margin-bottom: 8px;">⚖️ Balance prediction model parameters for better accuracy</li>' if avg_confidence_level < 70 else ''}
                            </ul>
                        </div>
                        <div style="background: linear-gradient(145deg, #ffffff, #f7fafc); padding: 25px; border-radius: 16px; box-shadow: inset 3px 3px 6px #d1d9e6, inset -3px -3px 6px #ffffff;">
                            <h4 style="color: #742a2a; margin-bottom: 15px; font-size: 1.2rem;">🔮 Predictive Actions (Next Week):</h4>
                            <ul style="margin: 0; padding-left: 20px; color: #2d3748;">
                                <li style="margin-bottom: 8px;">📈 Plan capacity upgrades based on error trend predictions</li>
                                <li style="margin-bottom: 8px;">🔧 Implement predictive maintenance for volatile systems</li>
                                <li style="margin-bottom: 8px;">📊 Enhance monitoring for systems with low stability indices</li>
                                <li style="margin-bottom: 8px;">🎛️ Adjust SLA thresholds based on prediction margins</li>
                                <li style="margin-bottom: 8px;">📚 Train teams on new prediction insights and patterns</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="footer">
                <p style="font-size: 1.2rem; font-weight: 700; margin-bottom: 10px;"><strong>🚀 Advanced MTN Systems Monitoring</strong></p>
                <p style="font-size: 1rem; margin-bottom: 10px;">📈 Trend Analysis • 🔮 Predictive Analytics • 📊 Performance Tracking • ⚡ Real-time Insights</p>
                <p style="font-size: 0.9rem; opacity: 0.9;">Generated: {date_str} | Next Analysis: Tomorrow | Prediction Model: v2.0</p>
                <p style="font-size: 0.8rem; opacity: 0.8; margin-top: 15px;">
                    Global Confidence: {avg_confidence_level:.1f}% | Total Predictions: {int(total_predicted_errors)} errors | 
                    Risk Assessment: {high_risk_systems} high-risk systems detected
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html

# Fonctions utilitaires existantes (inchangées)
def get_matching_csv_file(directory, reference_filename):
    """Récupère un fichier CSV correspondant"""
    try:
        base_name = os.path.splitext(os.path.basename(reference_filename))[0]
        matching_file = os.path.join(directory, f"{base_name}.csv")
        return matching_file if os.path.exists(matching_file) else None
    except:
        return None

def create_enhanced_chart(data, system_name):
    """Crée un graphique professionnel (fonction existante)"""
    try:
        if data is None or data.empty:
            return None
            
        plt.figure(figsize=(16, 10))
        colors_map = {'CIS': '#e74c3c', 'IRM': '#f39c12', 'ECW': '#27ae60'}
        color = colors_map.get(system_name, '#3498db')
        
        # Top 15 services par erreurs
        service_errors = data.groupby('Service Name')['Error Count'].sum().sort_values(ascending=False).head(15)
        
        if service_errors.empty:
            plt.close()
            return None
        
        bars = plt.bar(range(len(service_errors)), service_errors.values, 
                      color=color, alpha=0.8, edgecolor='black', linewidth=0.7)
        
        plt.title(f'{system_name} - Error Analysis (Top 15 Services)', 
                 fontsize=20, fontweight='bold', pad=25)
        plt.xlabel('Services', fontsize=14, fontweight='bold')
        plt.ylabel('Error Count', fontsize=14, fontweight='bold')
        
        plt.xticks(range(len(service_errors)), service_errors.index, 
                  rotation=45, ha='right', fontsize=11)
        plt.grid(axis='y', alpha=0.3, linestyle='--')
        
        # Valeurs sur les barres
        for i, (bar, value) in enumerate(zip(bars, service_errors.values)):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(service_errors.values) * 0.01,
                   str(int(value)), ha='center', va='bottom', fontweight='bold', fontsize=10)
        
        plt.tight_layout()
        
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight', facecolor='white')
        buffer.seek(0)
        chart_data = buffer.getvalue()
        buffer.close()
        plt.close()
        
        return chart_data
    except Exception as e:
        print(f"Erreur graphique: {e}")
        plt.close()
        return None

def send_email_with_reports(from_email, to_emails, subject, html_body, chart_images, attachment_file=None):
    """Envoie un email avec les rapports et graphiques (fonction existante)"""
    try:
        msg = MIMEMultipart('related')
        msg['From'] = from_email
        msg['To'] = ', '.join(to_emails)
        msg['Subject'] = subject
        
        # Corps HTML
        msg_html = MIMEMultipart('alternative')
        msg.attach(msg_html)
        
        # Ajouter les graphiques
        html_with_images = html_body
        for i, chart_data in enumerate(chart_images):
            if chart_data:
                cid = f"chart{i}"
                html_with_images += f'<div style="text-align: center; margin: 20px 0;"><img src="cid:{cid}" style="max-width: 100%; height: auto; border-radius: 8px;"></div>'
                
                img = MIMEImage(chart_data)
                img.add_header('Content-ID', f'<{cid}>')
                msg.attach(img)
        
        html_part = MIMEText(html_with_images, 'html')
        msg_html.attach(html_part)
        
        # Pièce jointe CSV
        if attachment_file and os.path.exists(attachment_file):
            with open(attachment_file, 'rb') as f:
                csv_attachment = MIMEApplication(f.read(), _subtype='csv')
                filename = os.path.basename(attachment_file)
                csv_attachment.add_header('Content-Disposition', f'attachment; filename="{filename}"')
                msg.attach(csv_attachment)
        
        # Envoi
        server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'])
        server.sendmail(from_email, to_emails, msg.as_string())
        server.quit()
        
        print(f'Email envoyé avec succès à: {", ".join(to_emails)}')
        return True
        
    except Exception as e:
        print(f'Erreur envoi email: {e}')
        return False

def main():
    """Fonction principale avec analyse de tendance"""
    try:
        # Configuration matplotlib
        plt.style.use('default')
        sns.set_palette("husl")
        
        # Génération des rapports avec analyse de tendance
        generate_daily_reports_with_trends()
        
    except Exception as e:
        print(f"❌ ERREUR CRITIQUE: {e}")
        print("Contactez l'équipe technique immédiatement!")

if __name__ == "__main__":
    main()