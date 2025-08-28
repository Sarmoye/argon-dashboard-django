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

# Configuration email (inchangée)
# Configuration email par système
EMAIL_CONFIG = {
    'smtp_server': '10.77.152.66',  # Adresse IP de votre serveur SMTP
    'smtp_port': 25,
    'from_email': 'noreply.errormonitor@mtn.com',
    
    # Destinataires par système
    'cis_recipients': [
        'Sarmoye.AmitoureHaidara@mtn.com',
        
    ],
    
    'irm_recipients': [
        'Sarmoye.AmitoureHaidara@mtn.com',
        
    ],
    
    'ecw_recipients': [
        'Sarmoye.AmitoureHaidara@mtn.com',
        
    ],
    
    # Destinataires pour le rapport de synthèse
    'summary_recipients': [
        'Sarmoye.AmitoureHaidara@mtn.com',
    ]
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

def create_trend_chart(trends_data, system_name):
    """Crée un graphique de tendance sur 7 jours"""
    if not trends_data or trends_data['data'].empty:
        return None
    
    try:
        df = trends_data['data']
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
        colors_map = {'CIS': '#e74c3c', 'IRM': '#f39c12', 'ECW': '#27ae60'}
        color = colors_map.get(system_name, '#3498db')
        
        # Graphique 1: Evolution des erreurs totales
        dates = [d.strftime('%m/%d') for d in df['date']]
        ax1.plot(dates, df['total_errors'], marker='o', linewidth=3, markersize=8, 
                color=color, markerfacecolor='white', markeredgewidth=2)
        ax1.fill_between(dates, df['total_errors'], alpha=0.3, color=color)
        
        ax1.set_title(f'{system_name} - Error Trend Analysis (7 Days)', 
                     fontsize=16, fontweight='bold', pad=20)
        ax1.set_ylabel('Total Errors', fontsize=12, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        
        # Ajouter les valeurs sur les points
        for i, (date, errors) in enumerate(zip(dates, df['total_errors'])):
            ax1.annotate(f'{int(errors)}', (i, errors), textcoords="offset points", 
                        xytext=(0,10), ha='center', fontweight='bold')
        
        # Graphique 2: Services affectés et critiques
        x_pos = range(len(dates))
        width = 0.35
        
        ax2.bar([x - width/2 for x in x_pos], df['affected_services'], width,
               label='Affected Services', color='#f39c12', alpha=0.8)
        ax2.bar([x + width/2 for x in x_pos], df['critical_services'], width,
               label='Critical Services', color='#e74c3c', alpha=0.8)
        
        ax2.set_title('Services Impact Trend', fontsize=14, fontweight='bold')
        ax2.set_ylabel('Number of Services', fontsize=12, fontweight='bold')
        ax2.set_xlabel('Date', fontsize=12, fontweight='bold')
        ax2.set_xticks(x_pos)
        ax2.set_xticklabels(dates)
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight', facecolor='white')
        buffer.seek(0)
        chart_data = buffer.getvalue()
        buffer.close()
        plt.close()
        
        return chart_data
        
    except Exception as e:
        print(f"Erreur graphique tendance: {e}")
        plt.close()
        return None

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from collections import Counter
import os

def calculate_enhanced_stats(data, system_name, trends_data=None):
    """Calcule des statistiques avancées avec analyse de tendance pour rapport professionnel"""
    base_stats = {
        'total_errors': 0, 'total_services': 0, 'affected_services': 0,
        'health_percentage': 0, 'critical_services': 0, 'avg_errors': 0,
        'top_error_service': 'N/A', 'status': 'NO_DATA',
        # Nouvelles métriques professionnelles
        'error_density': 0, 'reliability_score': 100, 'mtbf_hours': 0,
        'sla_compliance': 100, 'risk_level': 'LOW', 'alert_priority': 'INFO'
    }
    
    if data is None or data.empty:
        if trends_data:
            base_stats.update(trends_data)
        return base_stats
    
    # Statistiques de base améliorées
    total_errors = int(data['Error Count'].sum())
    total_services = len(data)
    affected_services = int((data['Error Count'] > 0).sum())
    critical_services = int((data['Error Count'] >= 10).sum())
    warning_services = int(((data['Error Count'] >= 5) & (data['Error Count'] < 10)).sum())
    healthy_services = total_services - affected_services
    
    # Métriques de qualité professionnelles
    health_percentage = round((healthy_services / total_services) * 100, 1) if total_services > 0 else 100
    availability_percentage = round(((total_services - critical_services) / total_services) * 100, 1) if total_services > 0 else 100
    error_density = round(total_errors / total_services, 2) if total_services > 0 else 0
    reliability_score = max(0, round(100 - (error_density * 5), 1))
    
    # Distribution des erreurs (Percentiles pour identifier les outliers)
    error_percentiles = {
        'p50': data['Error Count'].quantile(0.5),
        'p75': data['Error Count'].quantile(0.75),
        'p90': data['Error Count'].quantile(0.9),
        'p95': data['Error Count'].quantile(0.95),
        'p99': data['Error Count'].quantile(0.99)
    }
    
    # Services critiques détaillés
    high_impact_services = data[data['Error Count'] >= 10].nlargest(5, 'Error Count')
    top_5_errors = []
    if not high_impact_services.empty:
        for _, service in high_impact_services.iterrows():
            top_5_errors.append({
                'service': service['Service Name'],
                'errors': int(service['Error Count']),
                'impact_level': 'CRITICAL' if service['Error Count'] >= 20 else 'HIGH'
            })
    
    # Service le plus impacté avec contexte
    top_service_details = {'name': 'N/A', 'errors': 0, 'percentage': 0}
    if total_errors > 0:
        max_idx = data['Error Count'].idxmax()
        top_service_name = data.loc[max_idx, 'Service Name']
        top_service_errors = int(data.loc[max_idx, 'Error Count'])
        top_service_details = {
            'name': top_service_name,
            'errors': top_service_errors,
            'percentage': round((top_service_errors / total_errors) * 100, 1)
        }
    
    # Évaluation du risque et priorité
    risk_level, alert_priority, sla_compliance = calculate_risk_assessment(
        critical_services, total_services, error_density, health_percentage
    )
    
    # Statut global amélioré
    status = determine_system_status(critical_services, warning_services, health_percentage)
    
    # MTBF estimation (Mean Time Between Failures)
    mtbf_hours = estimate_mtbf(affected_services, total_services)
    
    stats = {
        # Métriques de base
        'total_errors': total_errors,
        'total_services': total_services,
        'affected_services': affected_services,
        'healthy_services': healthy_services,
        'critical_services': critical_services,
        'warning_services': warning_services,
        
        # Métriques de qualité
        'health_percentage': health_percentage,
        'availability_percentage': availability_percentage,
        'reliability_score': reliability_score,
        'sla_compliance': sla_compliance,
        'error_density': error_density,
        'avg_errors': round(total_errors / total_services, 2) if total_services > 0 else 0,
        
        # Distribution et analyse
        'error_percentiles': error_percentiles,
        'top_service_details': top_service_details,
        'top_5_critical_services': top_5_errors,
        
        # Évaluation des risques
        'risk_level': risk_level,
        'alert_priority': alert_priority,
        'status': status,
        'mtbf_hours': mtbf_hours,
        
        # Métriques de concentration
        'error_concentration_ratio': calculate_error_concentration(data),
        'service_stability_index': calculate_stability_index(data),
    }
    
    # Ajouter les données de tendance si disponibles
    if trends_data:
        stats.update(trends_data)
        # Calculer des métriques de tendance supplémentaires
        stats.update(calculate_trend_insights(trends_data, stats))
    
    return stats

def analyze_historical_trends(directory, system_name, days=7):
    """Analyse avancée des tendances avec métriques professionnelles"""
    files = get_files_by_date_range(directory, days)
    if len(files) < 2:
        return None
    
    trends_data = []
    
    for file_path in files:
        try:
            data = read_csv_data(file_path, system_name)
            if data is not None:
                file_date = datetime.fromtimestamp(os.path.getctime(file_path))
                total_errors = data['Error Count'].sum()
                affected_services = (data['Error Count'] > 0).sum()
                critical_services = (data['Error Count'] >= 10).sum()
                warning_services = ((data['Error Count'] >= 5) & (data['Error Count'] < 10)).sum()
                
                # Métriques supplémentaires
                error_density = total_errors / len(data) if len(data) > 0 else 0
                health_percentage = ((len(data) - affected_services) / len(data) * 100) if len(data) > 0 else 100
                
                trends_data.append({
                    'date': file_date,
                    'total_errors': total_errors,
                    'affected_services': affected_services,
                    'critical_services': critical_services,
                    'warning_services': warning_services,
                    'total_services': len(data),
                    'error_density': error_density,
                    'health_percentage': health_percentage
                })
        except Exception as e:
            print(f"Erreur analyse fichier {file_path}: {e}")
            continue
    
    if not trends_data:
        return None
    
    # Convertir en DataFrame et trier par date
    trends_df = pd.DataFrame(trends_data)
    trends_df = trends_df.sort_values('date')
    
    # Analyses de tendance avancées
    if len(trends_df) >= 2:
        current = trends_df.iloc[-1]
        previous = trends_df.iloc[-2]
        
        # Tendances de base
        error_trend = current['total_errors'] - previous['total_errors']
        affected_trend = current['affected_services'] - previous['affected_services']
        critical_trend = current['critical_services'] - previous['critical_services']
        health_trend = current['health_percentage'] - previous['health_percentage']
        
        # Analyses statistiques avancées
        error_volatility = calculate_volatility(trends_df['total_errors'])
        trend_strength = calculate_trend_strength(trends_df)
        regression_analysis = perform_regression_analysis(trends_df)
        
        # Prédictions basiques
        next_day_prediction = predict_next_day_errors(trends_df)
        
        # Tendance sur période complète
        if len(trends_df) >= 4:
            period_start = trends_df.head(2)['total_errors'].mean()
            period_end = trends_df.tail(2)['total_errors'].mean()
            period_trend = period_end - period_start
        else:
            period_trend = error_trend
        
        # Calcul du taux d'amélioration/dégradation
        improvement_rate = 0
        if previous['total_errors'] > 0:
            improvement_rate = round((error_trend / previous['total_errors'] * 100), 1)
        
        # Détection d'anomalies
        anomaly_score = detect_anomalies(trends_df)
        
        return {
            # Données brutes
            'data': trends_df,
            'days_analyzed': len(trends_df),
            
            # Tendances de base
            'current_errors': int(current['total_errors']),
            'previous_errors': int(previous['total_errors']),
            'error_trend': int(error_trend),
            'affected_trend': int(affected_trend),
            'critical_trend': int(critical_trend),
            'health_trend': round(health_trend, 1),
            'period_trend': round(period_trend, 1),
            
            # Métriques de performance
            'improvement_rate': improvement_rate,
            'error_volatility': round(error_volatility, 2),
            'trend_strength': trend_strength,
            'stability_score': round(100 - error_volatility * 10, 1),
            
            # Analyses avancées
            'regression_slope': round(regression_analysis['slope'], 3),
            'trend_reliability': regression_analysis['r_squared'],
            'anomaly_score': round(anomaly_score, 2),
            
            # Prédictions
            'predicted_next_day_errors': int(next_day_prediction),
            'trend_direction': 'IMPROVING' if error_trend < -2 else 'DEGRADING' if error_trend > 2 else 'STABLE',
            'trend_confidence': calculate_trend_confidence(trends_df),
            
            # Alertes de tendance
            'trend_alerts': generate_trend_alerts(trends_df, current, previous),
        }
    
    return None

def calculate_risk_assessment(critical_services, total_services, error_density, health_percentage):
    """Évalue le niveau de risque et la priorité d'alerte"""
    critical_ratio = critical_services / total_services if total_services > 0 else 0
    
    # Calcul du score de risque composite
    risk_score = (critical_ratio * 40) + (error_density * 20) + ((100 - health_percentage) * 0.4)
    
    # Détermination du niveau de risque
    if risk_score >= 30 or critical_ratio >= 0.2:
        risk_level = 'CRITICAL'
        alert_priority = 'URGENT'
        sla_compliance = max(0, 100 - risk_score * 2)
    elif risk_score >= 15 or critical_ratio >= 0.1:
        risk_level = 'HIGH'
        alert_priority = 'HIGH'
        sla_compliance = max(80, 100 - risk_score * 1.5)
    elif risk_score >= 5 or critical_ratio >= 0.05:
        risk_level = 'MEDIUM'
        alert_priority = 'MEDIUM'
        sla_compliance = max(90, 100 - risk_score)
    else:
        risk_level = 'LOW'
        alert_priority = 'INFO'
        sla_compliance = min(100, 100 - risk_score * 0.5)
    
    return risk_level, alert_priority, round(sla_compliance, 1)

def determine_system_status(critical_services, warning_services, health_percentage):
    """Détermine le statut système avec plus de granularité"""
    if critical_services > 0:
        if critical_services >= 5:
            return 'CRITICAL'
        else:
            return 'DEGRADED'
    elif warning_services > 0:
        if health_percentage < 80:
            return 'WARNING'
        else:
            return 'MINOR_ISSUES'
    elif health_percentage >= 95:
        return 'OPTIMAL'
    elif health_percentage >= 90:
        return 'HEALTHY'
    else:
        return 'STABLE'

def calculate_error_concentration(data):
    """Calcule le ratio de concentration des erreurs (Gini-like)"""
    if data.empty or data['Error Count'].sum() == 0:
        return 0
    
    errors = data['Error Count'].sort_values(ascending=False)
    total_errors = errors.sum()
    
    # Top 20% des services concentrent combien % des erreurs ?
    top_20_percent = max(1, int(len(errors) * 0.2))
    concentration = errors.head(top_20_percent).sum() / total_errors
    
    return round(concentration * 100, 1)

def calculate_stability_index(data):
    """Index de stabilité basé sur la variance des erreurs"""
    if data.empty:
        return 100
    
    error_variance = data['Error Count'].var()
    mean_errors = data['Error Count'].mean()
    
    if mean_errors == 0:
        return 100
    
    cv = error_variance / (mean_errors ** 2)  # Coefficient de variation squared
    stability_index = max(0, 100 - cv * 10)
    
    return round(stability_index, 1)

def estimate_mtbf(affected_services, total_services):
    """Estime le MTBF en heures (approximation)"""
    if affected_services == 0:
        return 720  # 30 jours si aucun service affecté
    
    failure_rate = affected_services / total_services
    mtbf = 24 / failure_rate if failure_rate > 0 else 720
    
    return round(min(mtbf, 720), 1)  # Cap à 30 jours

def calculate_volatility(error_series):
    """Calcule la volatilité des erreurs (écart-type normalisé)"""
    if len(error_series) < 2:
        return 0
    
    mean_errors = error_series.mean()
    if mean_errors == 0:
        return 0
    
    return error_series.std() / mean_errors

def calculate_trend_strength(trends_df):
    """Calcule la force de la tendance"""
    if len(trends_df) < 3:
        return 'INSUFFICIENT_DATA'
    
    errors = trends_df['total_errors'].values
    x = np.arange(len(errors))
    
    correlation = np.corrcoef(x, errors)[0, 1]
    abs_correlation = abs(correlation)
    
    if abs_correlation >= 0.8:
        return 'STRONG'
    elif abs_correlation >= 0.5:
        return 'MODERATE'
    elif abs_correlation >= 0.3:
        return 'WEAK'
    else:
        return 'NONE'

def perform_regression_analysis(trends_df):
    """Analyse de régression simple"""
    if len(trends_df) < 3:
        return {'slope': 0, 'r_squared': 0}
    
    x = np.arange(len(trends_df))
    y = trends_df['total_errors'].values
    
    slope, intercept = np.polyfit(x, y, 1)
    correlation = np.corrcoef(x, y)[0, 1]
    r_squared = correlation ** 2
    
    return {
        'slope': slope,
        'intercept': intercept,
        'r_squared': r_squared
    }

def predict_next_day_errors(trends_df):
    """Prédiction simple du nombre d'erreurs du lendemain"""
    if len(trends_df) < 2:
        return 0
    
    if len(trends_df) >= 3:
        # Moyenne mobile pondérée
        weights = [0.5, 0.3, 0.2]
        recent_errors = trends_df['total_errors'].tail(3).values
        if len(recent_errors) == 3:
            prediction = sum(w * e for w, e in zip(weights, reversed(recent_errors)))
        else:
            prediction = trends_df['total_errors'].iloc[-1]
    else:
        # Tendance simple
        current = trends_df['total_errors'].iloc[-1]
        previous = trends_df['total_errors'].iloc[-2]
        trend = current - previous
        prediction = max(0, current + trend * 0.5)  # Atténuation de la tendance
    
    return max(0, prediction)

def detect_anomalies(trends_df):
    """Détecte les anomalies dans les données (score Z modifié)"""
    if len(trends_df) < 4:
        return 0
    
    errors = trends_df['total_errors']
    median = errors.median()
    mad = np.median(np.abs(errors - median))  # Median Absolute Deviation
    
    if mad == 0:
        return 0
    
    # Score Z modifié pour le dernier point
    last_error = errors.iloc[-1]
    modified_z_score = 0.6745 * (last_error - median) / mad
    
    return abs(modified_z_score)

def calculate_trend_confidence(trends_df):
    """Calcule la confiance dans la tendance détectée"""
    if len(trends_df) < 3:
        return 'LOW'
    
    regression = perform_regression_analysis(trends_df)
    r_squared = regression['r_squared']
    volatility = calculate_volatility(trends_df['total_errors'])
    
    confidence_score = r_squared * (1 - min(volatility, 1))
    
    if confidence_score >= 0.7:
        return 'HIGH'
    elif confidence_score >= 0.4:
        return 'MEDIUM'
    else:
        return 'LOW'

def generate_trend_alerts(trends_df, current, previous):
    """Génère des alertes basées sur l'analyse des tendances"""
    alerts = []
    
    error_change = current['total_errors'] - previous['total_errors']
    critical_change = current['critical_services'] - previous['critical_services']
    health_change = current['health_percentage'] - previous['health_percentage']
    
    # Alertes de dégradation
    if error_change > 10:
        alerts.append({
            'type': 'ERROR_SPIKE',
            'severity': 'HIGH',
            'message': f"Augmentation significative des erreurs: +{error_change}"
        })
    
    if critical_change > 0:
        alerts.append({
            'type': 'CRITICAL_INCREASE',
            'severity': 'CRITICAL',
            'message': f"Nouveaux services critiques détectés: +{critical_change}"
        })
    
    if health_change < -10:
        alerts.append({
            'type': 'HEALTH_DEGRADATION',
            'severity': 'HIGH',
            'message': f"Dégradation de la santé système: {health_change:.1f}%"
        })
    
    # Alertes d'amélioration
    if error_change < -5 and previous['total_errors'] > 0:
        alerts.append({
            'type': 'IMPROVEMENT',
            'severity': 'INFO',
            'message': f"Amélioration détectée: -{abs(error_change)} erreurs"
        })
    
    return alerts

def calculate_trend_insights(trends_data, current_stats):
    """Calcule des insights supplémentaires basés sur les tendances"""
    insights = {}
    
    if 'error_trend' in trends_data:
        error_trend = trends_data['error_trend']
        current_errors = current_stats['total_errors']
        
        # Projection sur 7 jours
        if error_trend != 0:
            projected_errors = max(0, current_errors + (error_trend * 7))
            insights['weekly_projection'] = int(projected_errors)
            insights['projection_change'] = round(((projected_errors - current_errors) / current_errors * 100) if current_errors > 0 else 0, 1)
        
        # Évaluation de la trajectoire
        if error_trend < -2:
            insights['trajectory'] = 'IMPROVING_FAST'
        elif error_trend < 0:
            insights['trajectory'] = 'IMPROVING_SLOW'
        elif error_trend == 0:
            insights['trajectory'] = 'STABLE'
        elif error_trend <= 2:
            insights['trajectory'] = 'DEGRADING_SLOW'
        else:
            insights['trajectory'] = 'DEGRADING_FAST'
    
    return insights

#
# Generates a professional, enhanced HTML report with trend analysis and explanatory text.
#
from datetime import datetime

import pandas as pd
from datetime import datetime
import numpy as np

def create_professional_system_html_with_trends(system_name, data, stats, date_str, trends_data=None):
    """
    Creates a professional, multi-section HTML report enriched with detailed
    trend analysis, performance metrics, and strategic recommendations.

    Args:
        system_name (str): The name of the system.
        data (pd.DataFrame): The raw service data.
        stats (dict): The enhanced statistics dictionary.
        date_str (str): The current date string for the report.
        trends_data (dict, optional): The dictionary containing trend analysis data.

    Returns:
        str: A single string containing the complete HTML document.
    """
    
    # -------------------
    # Configuration Data
    # -------------------
    status_colors = {
        'OPTIMAL': ('#2ecc71', '✅ OPTIMAL'),
        'HEALTHY': ('#27ae60', '✅ HEALTHY'),
        'STABLE': ('#3498db', '➡️ STABLE'),
        'MINOR_ISSUES': ('#f1c40f', '⚠️ MINOR ISSUES'),
        'WARNING': ('#e67e22', '⚠️ WARNING'),
        'DEGRADED': ('#d35400', '⚠️ DEGRADED'),
        'CRITICAL': ('#e74c3c', '🔴 CRITICAL'),
        'NO_DATA': ('#95a5a6', '⚪ NO DATA')
    }
    
    risk_colors = {
        'LOW': '#2ecc71',
        'MEDIUM': '#f1c40f',
        'HIGH': '#e67e22',
        'CRITICAL': '#e74c3c'
    }
    
    # Get status color and text based on the stats dictionary
    status_color, status_text = status_colors.get(stats['status'], status_colors['NO_DATA'])
    
    # -------------------
    # Dynamic Content Generation
    # -------------------
    
    # Trend Analysis Section
    trend_section = ""
    # Check if trend data exists and an error trend is present
    if trends_data and 'error_trend' in stats:
        # Determine the color and text for the trend status
        trend_direction = stats.get('trend_direction', 'STABLE')
        trend_arrow = '⬇️' if trend_direction == 'IMPROVING' else '⬆️' if trend_direction == 'DEGRADING' else '➡️'
        trend_class = 'trend-improving' if trend_direction == 'IMPROVING' else 'trend-degrading' if trend_direction == 'DEGRADING' else 'trend-stable'
        
        # Trend alerts
        alerts_html = ""
        if 'trend_alerts' in stats and stats['trend_alerts']:
            for alert in stats['trend_alerts']:
                alert_icon = "🚨" if alert['severity'] in ['HIGH', 'CRITICAL'] else "💡"
                alerts_html += f"<li>{alert_icon} {alert['message']}</li>"
        
        trend_section = f"""
        <div class="card {trend_class} trend-section">
            <h3 class="card-title">{trend_arrow} TREND ANALYSIS (Last {stats.get('days_analyzed', 'N/A')} days)</h3>
            <div class="stats-grid-small">
                <div><strong>Errors:</strong> {stats.get('error_trend', 'N/A'):+d}</div>
                <div><strong>Services:</strong> {stats.get('affected_trend', 'N/A'):+d}</div>
                <div><strong>Health %:</strong> {stats.get('health_trend', 'N/A'):+.1f}%</div>
                <div><strong>Volatility:</strong> {stats.get('error_volatility', 'N/A'):.2f}</div>
                <div><strong>Slope:</strong> {stats.get('regression_slope', 'N/A'):.2f}</div>
                <div><strong>Prediction:</strong> {stats.get('predicted_next_day_errors', 'N/A')} errors</div>
            </div>
            {'<h4 style="margin-top:20px;">Trend Alerts:</h4><ul>' + alerts_html + '</ul>' if alerts_html else ''}
        </div>
        """
        
    # Top Critical Services Section
    top_services_html = ""
    if stats.get('top_5_critical_services'):
        items_html = ""
        for item in stats['top_5_critical_services']:
            items_html += f"<li><strong>{item['service']}</strong>: {item['errors']} errors <small>({item['impact_level']})</small></li>"
        
        top_services_html = f"""
        <div class="card">
            <h3 class="card-title">🚨 Top 5 Critical Services</h3>
            <ul class="clean-list">{items_html}</ul>
        </div>
        """
        
    # Strategic Recommendations Section
    recommendations_html = ""
    if stats.get('status') != 'NO_DATA':
        rec_list = []
        risk_level = stats.get('risk_level', 'LOW')
        concentration_ratio = stats.get('error_concentration_ratio', 0)
        
        if risk_level in ['CRITICAL', 'HIGH']:
            rec_list.append(f"<strong>Immediate Action:</strong> The system's risk level is <span class='risk-tag' style='background-color:{risk_colors[risk_level]};'>{risk_level}</span>. Prioritize the investigation and resolution of critical services to prevent major incidents.")
        
        if stats.get('trend_direction') == 'DEGRADING':
            rec_list.append(f"<strong>Proactive Monitoring:</strong> The trend is <span class='risk-tag' style='background-color:{risk_colors['HIGH']};'>DEGRADING</span>. An increase of {stats.get('error_trend', 0)} errors was observed. Investigate the root cause of this decline to stabilize the system.")
        
        if concentration_ratio >= 50:
            rec_list.append(f"<strong>Targeted Intervention:</strong> Errors are highly concentrated. The top 20% of services are responsible for {concentration_ratio}% of all errors. Focus your efforts on these high-impact services for maximum efficiency.")
        
        if not rec_list:
            rec_list.append("<strong>Maintain Vigilance:</strong> The system is in a stable or improving state. Continue proactive monitoring and review the latest changes to maintain this positive trajectory.")
            
        rec_items = "".join([f"<li>👉 {rec}</li>" for rec in rec_list])
        
        recommendations_html = f"""
        <div class="card recommendations">
            <h3 class="card-title">🎯 Strategic Insights & Action Plan</h3>
            <ul class="clean-list">{rec_items}</ul>
        </div>
        """

    # -------------------
    # Final HTML Assembly
    # -------------------
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
            body {{ font-family: 'Inter', sans-serif; margin: 0; background: #f0f2f5; color: #333; line-height: 1.6; }}
            .container {{ max-width: 1200px; margin: 20px auto; background: white; border-radius: 15px; box-shadow: 0 8px 20px rgba(0,0,0,0.1); overflow: hidden; }}
            .header {{ background: linear-gradient(135deg, #2c3e50, #34495e); color: white; padding: 50px 20px; text-align: center; }}
            .header h1 {{ font-size: 2.8rem; margin: 0 0 10px; font-weight: 700; }}
            .status-badge {{ background: {status_color}; color: white; padding: 12px 25px; border-radius: 25px; font-weight: 600; margin-top: 15px; display: inline-block; box-shadow: 0 4px 8px rgba(0,0,0,0.2); }}
            .content {{ padding: 30px; }}
            .card {{ background: #ffffff; padding: 25px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); margin-bottom: 25px; border: 1px solid #e0e0e0; }}
            .card-title {{ font-size: 1.5rem; font-weight: 600; color: #2c3e50; margin-top: 0; margin-bottom: 20px; border-bottom: 2px solid #e0e0e0; padding-bottom: 10px; }}
            .stats-grid, .stats-grid-small {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }}
            .stats-grid-small {{ grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); }}
            .stat-card {{ text-align: center; background: #f7f9fc; padding: 20px; border-radius: 10px; border: 1px solid #e0e0e0; }}
            .stat-number {{ font-size: 2.2rem; font-weight: 700; color: #2c3e50; margin-bottom: 5px; }}
            .stat-label {{ font-size: 0.9rem; color: #7f8c8d; text-transform: uppercase; letter-spacing: 1px; font-weight: 500; }}
            .danger {{ color: #e74c3c !important; }}
            .success {{ color: #27ae60 !important; }}
            .warning {{ color: #e67e22 !important; }}
            .info {{ color: #3498db !important; }}
            .clean-list {{ list-style-type: none; margin: 0; padding: 0; }}
            .clean-list li {{ padding: 10px 0; border-bottom: 1px dashed #e0e0e0; }}
            .clean-list li:last-child {{ border-bottom: none; }}
            .recommendations {{ background: #e8f5e9; border-left: 5px solid #4caf50; }}
            .risk-tag {{ display: inline-block; padding: 4px 10px; border-radius: 5px; font-size: 0.8rem; font-weight: 600; color: white; text-transform: uppercase; }}
            .trend-section {{ border-left: 5px solid #3498db; }}
            .trend-improving {{ border-left-color: #27ae60; }}
            .trend-degrading {{ border-left-color: #e74c3c; }}
            @media (max-width: 768px) {{
                .stats-grid, .stats-grid-small {{ grid-template-columns: 1fr; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <!-- Header -->
            <div class="header">
                <h1>System Report - {system_name}</h1>
                <p>Advanced Error Analysis - {date_str}</p>
                <div class="status-badge">{status_text}</div>
            </div>
            
            <div class="content">
                <!-- Executive Summary -->
                <div class="card">
                    <h3 class="card-title">📝 Executive Summary</h3>
                    <p>
                        This report provides a comprehensive overview of the current state and performance trends for the <strong>{system_name}</strong> system.
                        It includes key metrics, an assessment of reliability, and strategic recommendations to help maintain or improve system health.
                    </p>
                </div>

                <!-- Key Performance Indicators (KPIs) -->
                <div class="card">
                    <h3 class="card-title">📊 Key Performance Indicators</h3>
                    <div class="stats-grid">
                        <div class="stat-card">
                            <div class="stat-number danger">{stats.get('total_errors', 'N/A')}</div>
                            <div class="stat-label">Total Errors</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">{stats.get('total_services', 'N/A')}</div>
                            <div class="stat-label">Total Services</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number warning">{stats.get('affected_services', 'N/A')}</div>
                            <div class="stat-label">Affected Services</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number success">{stats.get('health_percentage', 'N/A')}%</div>
                            <div class="stat-label">Health Rate</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number danger">{stats.get('critical_services', 'N/A')}</div>
                            <div class="stat-label">Critical Services</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number info">{stats.get('avg_errors', 'N/A'):.2f}</div>
                            <div class="stat-label">Avg Errors/Service</div>
                        </div>
                    </div>
                </div>

                <!-- Performance & Reliability Metrics -->
                <div class="card">
                    <h3 class="card-title">🚀 Performance & Reliability Metrics</h3>
                    <div class="stats-grid">
                        <div class="stat-card">
                            <div class="stat-number">{stats.get('reliability_score', 'N/A')}</div>
                            <div class="stat-label">Reliability Score</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">{stats.get('sla_compliance', 'N/A')}%</div>
                            <div class="stat-label">SLA Compliance</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">{stats.get('mtbf_hours', 'N/A')}h</div>
                            <div class="stat-label">MTBF (Est.)</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">{stats.get('error_concentration_ratio', 'N/A')}%</div>
                            <div class="stat-label">Error Concentration</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number" style="color: {risk_colors.get(stats.get('risk_level', 'LOW'))};">{stats.get('risk_level', 'N/A')}</div>
                            <div class="stat-label">Risk Level</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">{stats.get('alert_priority', 'N/A')}</div>
                            <div class="stat-label">Alert Priority</div>
                        </div>
                    </div>
                </div>

                <!-- Trend Analysis -->
                {trend_section}
                
                <!-- Top Critical Services -->
                {top_services_html}

                <!-- Strategic Recommendations -->
                {recommendations_html}
            </div>
            
            <!-- Footer -->
            <div class="header">
                <p style="font-size: 1rem; margin: 0;"><strong>Enhanced System Monitoring</strong></p>
                <p style="font-size: 0.8rem; margin: 5px 0 0;">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
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
                    trend_chart = create_trend_chart(trends_data, system_name)
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
    """Enhanced version of the executive summary with trends"""
    # Global calculations
    total_errors = sum(stats.get('total_errors', 0) for stats in all_stats.values())
    total_services = sum(stats.get('total_services', 0) for stats in all_stats.values())
    improving_systems = sum(1 for stats in all_stats.values() if stats.get('error_trend', 0) < 0)
    degrading_systems = sum(1 for stats in all_stats.values() if stats.get('error_trend', 0) > 0)
    
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
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: 'Segoe UI', sans-serif; margin: 0; background: #f5f7fa; }}
            .container {{ max-width: 1400px; margin: 20px auto; background: white; border-radius: 15px; box-shadow: 0 15px 35px rgba(0,0,0,0.1); }}
            .header {{ background: linear-gradient(135deg, #1e3c72, #2a5298); color: black; padding: 50px; text-align: center; }}
            .header h1 {{ font-size: 3rem; margin: 0 0 15px; font-weight: 700; }}
            .global-status {{ padding: 15px 30px; border-radius: 25px; font-weight: 700; margin-top: 20px; display: inline-block; }}
            .content {{ padding: 50px; }}
            .trend-summary {{ background: linear-gradient(135deg, #667eea, #764ba2); color: black; padding: 30px; border-radius: 12px; margin: 30px 0; }}
            .systems-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 25px; margin: 30px 0; }}
            .system-card {{ background: white; border-radius: 12px; padding: 25px; box-shadow: 0 8px 20px rgba(0,0,0,0.08); }}
            .system-name {{ font-size: 1.3rem; font-weight: 700; margin-bottom: 15px; }}
            .trend-indicator {{ font-size: 1.1rem; margin: 10px 0; padding: 8px 15px; border-radius: 20px; display: inline-block; }}
            .improving {{ background: #d4edda; color: #155724; }}
            .degrading {{ background: #f8d7da; color: #721c24; }}
            .stable {{ background: #d1ecf1; color: #0c5460; }}
            .danger {{ color: #e74c3c; }}
            .success {{ color: #27ae60; }}
            .warning {{ color: #f39c12; }}
            .footer {{ background: #2c3e50; color: white; padding: 30px; text-align: center; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📊 Executive Dashboard with Trends</h1>
                <p style="font-size: 1.2rem; opacity: 0.9;">All Systems Performance & Evolution Analysis</p>
                <p>{date_str}</p>
                <div class="global-status {global_class}">{global_status}</div>
            </div>
            
            <div class="content">
                <div class="trend-summary">
                    <h3 style="margin: 0 0 20px 0; font-size: 1.5rem;">📈 Global Trend Analysis</h3>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px;">
                        <div style="text-align: center;">
                            <div style="font-size: 2rem; font-weight: bold;">{improving_systems}</div>
                            <div>Systems Improving</div>
                        </div>
                        <div style="text-align: center;">
                            <div style="font-size: 2rem; font-weight: bold;">{degrading_systems}</div>
                            <div>Systems Degrading</div>
                        </div>
                        <div style="text-align: center;">
                            <div style="font-size: 2rem; font-weight: bold;">{total_errors}</div>
                            <div>Total Current Errors</div>
                        </div>
                        <div style="text-align: center;">
                            <div style="font-size: 2rem; font-weight: bold;">{total_services}</div>
                            <div>Total Services Monitored</div>
                        </div>
                    </div>
                </div>
                
                <h2 style="color: #2c3e50; margin: 40px 0 25px; font-size: 1.8rem;">🖥️ Systems Performance Dashboard</h2>
                <div class="systems-grid">
    """
    
    # Adding system cards with trends
    for system_name, stats in all_stats.items():
        error_trend = stats.get('error_trend', 0)
        trend_class = 'improving' if error_trend < 0 else 'degrading' if error_trend > 0 else 'stable'
        trend_text = f'📈 -{abs(error_trend)} errors' if error_trend < 0 else f'📉 +{error_trend} errors' if error_trend > 0 else '➡️ No change'
        
        html += f"""
                    <div class="system-card">
                        <h3 class="system-name">{system_name} System</h3>
                        <div class="trend-indicator {trend_class}">
                            {trend_text} vs yesterday
                        </div>
                        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; margin: 15px 0;">
                            <div style="text-align: center; padding: 10px; background: #f8f9fa; border-radius: 8px;">
                                <div style="font-size: 1.4rem; font-weight: bold; color: {'#e74c3c' if stats.get('total_errors', 0) > 0 else '#27ae60'};">{stats.get('total_errors', 0)}</div>
                                <div style="font-size: 0.9rem; color: #666;">Current Errors</div>
                            </div>
                            <div style="text-align: center; padding: 10px; background: #f8f9fa; border-radius: 8px;">
                                <div style="font-size: 1.4rem; font-weight: bold;">{stats.get('health_percentage', 0):.1f}%</div>
                                <div style="font-size: 0.9rem; color: #666;">Health Rate</div>
                            </div>
                        </div>
                        <div style="margin-top: 15px; font-size: 0.9rem; color: #666;">
                            <div>Critical Services: <span style="font-weight: bold; color: {'#e74c3c' if stats.get('critical_services', 0) > 0 else '#27ae60'};">{stats.get('critical_services', 0)}</span></div>
                            <div>Most Impacted: <span style="font-weight: bold;">{stats.get('top_error_service', 'N/A')}</span></div>
                            {f'<div>Weekly Trend: <span style="font-weight: bold;">{stats.get("improvement_rate", 0):+.1f}%</span></div>' if 'improvement_rate' in stats else ''}
                        </div>
                    </div>
        """
    
    html += f"""
                </div>
                
                <div style="background: linear-gradient(135deg, #ff7675, #fd79a8); color: black; padding: 35px; border-radius: 12px; margin: 40px 0;">
                    <h3 style="font-size: 1.5rem; margin-bottom: 20px;">🎯 Strategic Recommendations</h3>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 25px;">
                        <div>
                            <h4>⚡ Immediate Actions:</h4>
                            <ul style="margin: 0; padding-left: 20px;">
                                {'<li>Investigate degrading systems immediately</li>' if degrading_systems > 0 else '<li>Maintain current monitoring practices</li>'}
                                {'<li>Replicate improvement strategies across systems</li>' if improving_systems > 0 else '<li>Review error prevention measures</li>'}
                                <li>Focus on critical services requiring attention</li>
                            </ul>
                        </div>
                        <div>
                            <h4>📊 Strategic Insights:</h4>
                            <ul style="margin: 0; padding-left: 20px;">
                                <li>Track daily trends to identify patterns</li>
                                <li>Implement predictive maintenance where possible</li>
                                <li>Document successful improvement strategies</li>
                                <li>Plan capacity upgrades for consistently problematic services</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="footer">
                <p><strong>🚀 Advanced MTN Systems Monitoring</strong></p>
                <p>📈 Trend Analysis • 📊 Performance Tracking • ⚡ Real-time Insights</p>
                <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Next Analysis: {(datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')}</p>
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