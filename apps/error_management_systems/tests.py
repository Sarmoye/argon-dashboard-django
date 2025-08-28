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

def analyze_historical_trends(directory, system_name, days=7):
    """Analyse les tendances sur les N derniers jours avec insights avancés"""
    files = get_files_by_date_range(directory, days)
    if len(files) < 2:
        return None
    
    trends_data = []
    
    for file_path in files:
        try:
            data = read_csv_data(file_path, system_name)
            if data is not None and not data.empty:
                grouped_data = data.groupby('Service Name')['Error Count'].sum().reset_index()
                
                file_date = datetime.fromtimestamp(os.path.getctime(file_path))
                total_errors = grouped_data['Error Count'].sum()
                
                # Récupérer les listes de services
                affected_services_list = grouped_data[grouped_data['Error Count'] > 0]['Service Name'].tolist()
                critical_services_list = grouped_data[grouped_data['Error Count'] >= 10]['Service Name'].tolist()
                
                affected_services_count = len(affected_services_list)
                critical_services_count = len(critical_services_list)
                total_services = len(grouped_data)
                
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
            print(f"Erreur analyse fichier {file_path}: {e}")
            continue
            
    if not trends_data or len(trends_data) < 2:
        return None
    
    trends_df = pd.DataFrame(trends_data)
    trends_df = trends_df.sort_values('date')
    
    # Trouver le fichier le plus récent (current)
    current = trends_df.iloc[-1]
    current_time = current['date']
    
    # Calculer la veille à la même heure avec gestion des minutes négatives
    previous_day = current_time - timedelta(days=1)
    
    # Créer la fenêtre horaire de ±30 minutes de manière sécurisée
    time_target = previous_day.replace(hour=current_time.hour, minute=current_time.minute, second=0, microsecond=0)
    time_window_start = time_target - timedelta(minutes=30)
    time_window_end = time_target + timedelta(minutes=30)
    
    # Filtrer les fichiers dans la fenêtre horaire de la veille
    previous_files = trends_df[
        (trends_df['date'] >= time_window_start) & 
        (trends_df['date'] <= time_window_end)
    ]
    
    if previous_files.empty:
        # Si aucun fichier à la même heure hier, prendre le fichier le plus proche de la veille
        previous_day_files = trends_df[trends_df['date'].dt.date == previous_day.date()]
        if previous_day_files.empty:
            # Si aucun fichier la veille, prendre le précédent disponible
            previous_files_all = trends_df[trends_df['date'] < current_time]
            if previous_files_all.empty:
                return None
            previous = previous_files_all.iloc[-1]
        else:
            # Prendre le fichier le plus proche de l'heure cible
            previous_day_files = previous_day_files.copy()
            previous_day_files['time_diff'] = abs((previous_day_files['date'] - time_target).dt.total_seconds())
            previous = previous_day_files.loc[previous_day_files['time_diff'].idxmin()]
    else:
        # Prendre le fichier le plus proche de l'heure exacte dans la fenêtre
        previous_files = previous_files.copy()
        previous_files['time_diff'] = abs((previous_files['date'] - time_target).dt.total_seconds())
        previous = previous_files.loc[previous_files['time_diff'].idxmin()]

    print(f'CURRENT {current}')
    print(f'PREVIOUS {previous}')
    print(f'Current time: {current_time}')
    print(f'Target time for previous day: {time_target}')
    print(f'Time window: {time_window_start} - {time_window_end}')
    
    error_trend = current['total_errors'] - previous['total_errors']
    affected_trend = current['affected_services'] - previous['affected_services']
    critical_trend = current['critical_services'] - previous['critical_services']
    reliability_trend = current['reliability_score'] - previous['reliability_score']
    
    if len(trends_df) >= 4:
        avg_recent = trends_df.tail(3)['total_errors'].mean()
        avg_older = trends_df.head(3)['total_errors'].mean()
        week_trend = avg_recent - avg_older
        volatility = trends_df['total_errors'].std()
        stability_trend = "STABLE" if volatility < 5 else "MODERATE" if volatility < 15 else "HIGH_VOLATILITY"
    else:
        week_trend = error_trend
        volatility = 0
        stability_trend = "INSUFFICIENT_DATA"
    
    momentum = "NEUTRAL"
    if len(trends_df) >= 3:
        # Pour le momentum, trouver le jour précédent du previous
        previous_time = previous['date']
        day_before_previous = previous_time - timedelta(days=1)
        day_before_files = trends_df[trends_df['date'].dt.date == day_before_previous.date()]
        if not day_before_files.empty:
            # Trouver le fichier le plus proche de la même heure que previous
            target_time_prev = day_before_previous.replace(hour=previous_time.hour, minute=previous_time.minute)
            day_before_files = day_before_files.copy()
            day_before_files['time_diff'] = abs((day_before_files['date'] - target_time_prev).dt.total_seconds())
            day_before = day_before_files.loc[day_before_files['time_diff'].idxmin()]
            
            trend_yesterday = previous['total_errors'] - day_before['total_errors']
            if error_trend > trend_yesterday + 2:
                momentum = "ACCELERATING"
            elif error_trend < trend_yesterday - 2:
                momentum = "DECELERATING"
    
    predicted_errors = max(0, current['total_errors'] + error_trend)
    prediction_confidence = "HIGH" if len(trends_df) >= 5 else "MEDIUM" if len(trends_df) >= 3 else "LOW"

    return {
        'data': trends_df,
        'current_errors': int(current['total_errors']),
        'previous_errors': int(previous['total_errors']),
        'error_trend': int(error_trend),
        'affected_trend': int(affected_trend),
        'critical_trend': int(critical_trend),
        'reliability_trend': round(reliability_trend, 1),
        'week_trend': week_trend,
        'improvement_rate': round((error_trend / previous['total_errors'] * 100) if previous['total_errors'] > 0 else 0, 1),
        'days_analyzed': len(trends_df),
        'volatility': round(volatility, 2),
        'stability_trend': stability_trend,
        'momentum': momentum,
        'predicted_errors': int(predicted_errors),
        'prediction_confidence': prediction_confidence,
        'avg_error_density': round(trends_df['error_density'].mean(), 2),
        'peak_errors': int(trends_df['total_errors'].max()),
        'best_day_errors': int(trends_df['total_errors'].min()),
        'current_affected_services_list': current['affected_services_list'],
        'current_critical_services_list': current['critical_services_list'],
        'comparison_time_info': f"Comparé à {previous['date'].strftime('%Y-%m-%d %H:%M')} (cible: {time_target.strftime('%H:%M')})"
    }

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
        if 'predicted_errors' in trends_data:
            pred_date = (df['date'].iloc[-1] + timedelta(days=1)).strftime('%b %d')
            all_dates = dates + [pred_date]
            pred_line = list(df['total_errors']) + [trends_data['predicted_errors']]
            ax1.plot(all_dates[-2:], pred_line[-2:], 'r--', linewidth=2, alpha=0.6, label='Prediction')
            ax1.scatter([pred_date], [trends_data['predicted_errors']], color='red', s=120, alpha=0.7, zorder=5)
            ax1.text(pred_date, trends_data['predicted_errors'] * 1.05, 
                     f"{int(trends_data['predicted_errors'])}", color='red', 
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
                    
                    ax2.set_title(f'Top 10 Services by Error Count\n({latest_date.strftime("%Y-%m-%d")})', 
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

def calculate_enhanced_stats(data, system_name, trends_data=None):
    """Calcule des statistiques avancées avec insights professionnels"""
    base_stats = {
        'total_errors': 0, 'total_services': 0, 'affected_services': 0,
        'health_percentage': 0, 'critical_services': 0, 'avg_errors': 0,
        'top_error_service': 'N/A', 'status': 'NO_DATA',
        'stability_index': 0, 'risk_level': 'UNKNOWN', 'business_impact': 'UNKNOWN',
        'affected_services_list': [],
        'critical_services_list': []
    }

    if data is None or data.empty:
        if trends_data:
            base_stats.update({
                'error_trend': trends_data.get('error_trend', 0),
                'improvement_rate': trends_data.get('improvement_rate', 0),
                'trend_status': 'NO_DATA',
                'predicted_errors': trends_data.get('predicted_errors', 0),
                'volatility': trends_data.get('volatility', 0)
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
        'critical_services_list': critical_services_list
    }

    # Ajouter les données de tendance si disponibles
    if trends_data:
        trend_status = 'IMPROVING' if trends_data.get('error_trend', 0) < 0 else 'DEGRADING' if trends_data.get('error_trend', 0) > 0 else 'STABLE'
        
        # S'assurer que les listes de tendances sont passées si elles existent
        if 'current_affected_services_list' in trends_data:
            stats['affected_services_list'] = trends_data['current_affected_services_list']
        if 'current_critical_services_list' in trends_data:
            stats['critical_services_list'] = trends_data['current_critical_services_list']

        stats.update({
            'error_trend': trends_data.get('error_trend', 0),
            'improvement_rate': trends_data.get('improvement_rate', 0),
            'week_trend': trends_data.get('week_trend', 0),
            'days_analyzed': trends_data.get('days_analyzed', 0),
            'trend_status': trend_status,
            'volatility': trends_data.get('volatility', 0),
            'momentum': trends_data.get('momentum', 'NEUTRAL'),
            'predicted_errors': trends_data.get('predicted_errors', 0),
            'prediction_confidence': trends_data.get('prediction_confidence', 'LOW'),
            'reliability_trend': trends_data.get('reliability_trend', 0),
            'stability_trend': trends_data.get('stability_trend', 'STABLE')
        })

    return stats

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

    # Get status color and text based on the stats dictionary
    status_color, status_text = status_colors.get(stats['status'], status_colors['NO_DATA'])

    # Trend analysis section HTML
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
        
        prediction_text = f"{stats.get('predicted_errors', 0)} errors ({stats.get('prediction_confidence', 'LOW')} confidence)"

        trend_section = f"""
        <div class="trend-analysis">
            <h3>{trend_arrow} Trend Analysis (Last days)</h3>
            <div class="trend-grid">
                <div class="trend-item"><strong>Current Trend:</strong> <span style="color: {trend_color}; font-weight: bold;">{trend_text}</span></div>
                <div class="trend-item"><strong>Error Change (D-1):</strong> <span style="color: {trend_color};">{stats.get('error_trend', 0):+d}</span> ({stats.get('improvement_rate', 0):+.1f}%)</div>
                <div class="trend-item"><strong>7-Day Avg Trend:</strong> <span style="color: {trend_color};">{trends_data.get('week_trend', 0):+.1f} avg</span></div>
                <div class="trend-item"><strong>Momentum:</strong> <span style="color: {momentum_color}; font-weight: bold;">{momentum.replace('_', ' ')}</span></div>
                <div class="trend-item"><strong>Volatility:</strong> <span style="color: {stability_color}; font-weight: bold;">{stability.replace('_', ' ')}</span></div>
                <div class="trend-item"><strong>Predicted Errors:</strong> <span style="color: {momentum_colors.get(momentum, 'black')};">{prediction_text}</span></div>
            </div>
        </div>
        """
    
    # Determine recommendation text based on status and trends
    recommendation_list = []
    if stats['status'] == 'CRITICAL':
        recommendation_list.append(f"<li>🚨 Immediate action is required. Investigate the <strong>{stats.get('critical_services', 0)} critical services</strong> to identify and resolve the root cause of high error counts.</li>")
    if stats['status'] == 'WARNING' and stats['affected_services'] > 0:
        recommendation_list.append(f"<li>⚠️ The system is showing signs of instability. Prioritize the <strong>{stats.get('affected_services', 0)} affected services</strong> for analysis.</li>")
    if stats.get('trend_status') == 'DEGRADING':
        recommendation_list.append(f"<li>📉 The number of errors is increasing. Analyze the cause of the degradation trend and implement preventative measures.</li>")
    if stats.get('stability_trend') == 'HIGH_VOLATILITY':
        recommendation_list.append(f"<li>📊 The system is highly volatile. Monitor error peaks and investigate services with erratic behavior.</li>")
    if stats.get('momentum') == 'ACCELERATING':
        recommendation_list.append(f"<li>🔥 Error growth is accelerating. A swift intervention is crucial to prevent the situation from becoming critical.</li>")
    if not recommendation_list:
        recommendation_list.append("<li>✅ The system is stable and healthy. Continue to monitor and perform routine maintenance to ensure long-term reliability.</li>")

    recommendation_html = "".join(recommendation_list)

    # HTML for affected and critical service lists
    affected_services_html = "<p>No affected services.</p>"
    if stats.get('affected_services_list'):
        affected_services_html = "<ul>" + "".join([f"<li>{service}</li>" for service in stats['affected_services_list']]) + "</ul>"

    critical_services_html = "<p>No critical services.</p>"
    if stats.get('critical_services_list'):
        critical_services_html = "<ul>" + "".join([f"<li style='color: #e74c3c; font-weight: bold;'>{service}</li>" for service in stats['critical_services_list']]) + "</ul>"

    # Return the complete HTML document as a single string
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>{system_name} - System Health Report</title>
        <style>
            body {{ 
                font-family: 'Inter', 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif; 
                margin: 0; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                color: #2d3748;
            }}
            .container {{ 
                max-width: 1200px; 
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
            
            /* Styles pour les cartes d'indicateurs clés - une seule ligne responsive */
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
            
            /* Styles pour les métriques avancées - une seule ligne responsive */
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
                min-width: 200px;
                max-width: 280px;
            }}
            .advanced-stat-card:hover {{ transform: translateY(-5px); box-shadow: 0 4px 15px rgba(0,0,0,0.1); }}
            
            /* Media queries pour la responsivité */
            @media (max-width: 1200px) {{
                .stats-grid {{
                    justify-content: center;
                }}
                .stat-card {{
                    min-width: 130px;
                    max-width: 160px;
                }}
                .advanced-stats-grid {{
                    justify-content: center;
                }}
                .advanced-stat-card {{
                    min-width: 180px;
                    max-width: 250px;
                }}
            }}
            
            @media (max-width: 768px) {{
                .stats-grid {{
                    flex-direction: column;
                    align-items: center;
                }}
                .stat-card {{
                    max-width: 300px;
                    width: 100%;
                }}
                .advanced-stats-grid {{
                    flex-direction: column;
                    align-items: center;
                }}
                .advanced-stat-card {{
                    max-width: 300px;
                    width: 100%;
                }}
            }}
            
            .danger {{ color: #e74c3c !important; }}
            .success {{ color: #27ae60 !important; }}
            .warning {{ color: #f39c12 !important; }}
            .recommendations {{ background: linear-gradient(135deg, #d4edda, #c3e6cb); color: #155724; padding: 30px; border-radius: 12px; margin: 30px 0; border: 1px solid #c3e6cb; }}
            .recommendations h3 {{ margin-bottom: 20px; font-size: 1.4rem; color: #155724; }}
            .recommendations ul {{ padding-left: 20px; }}
            .recommendations li {{ margin-bottom: 10px; font-weight: 500; }}
            .footer {{ background: #2c3e50; color: white; padding: 25px; text-align: center; }}
            .trend-info {{ font-size: 1.1rem; margin-bottom: 10px; }}
            .service-lists-container {{ display: flex; justify-content: space-around; gap: 30px; margin-top: 30px; }}
            .service-list-card {{ flex: 1; background: #fff; padding: 25px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); }}
            .service-list-card h4 {{ margin-top: 0; border-bottom: 2px solid #ecf0f1; padding-bottom: 10px; }}
            .service-list-card ul {{ list-style-type: none; padding: 0; margin: 0; }}
            .service-list-card li {{ padding: 8px 0; border-bottom: 1px solid #eee; }}
            .service-list-card li:last-child {{ border-bottom: none; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>System {system_name}</h1>
                <p>Advanced Error Analysis Report - {date_str}</p>
                <div class="status-badge">{status_text}</div>
            </div>
            
            <div class="content">
                <div class="intro">
                    <h2>🔎 Report Objective</h2>
                    <p>
                        This report provides a detailed analysis of the errors and incidents encountered on the
                        <strong>{system_name}</strong> system. You will find a summary of the key indicators,
                        the observed trends, as well as recommendations to improve stability
                        and reduce the impact on your services.
                    </p>
                    <p>
                        The objective is to provide you with a clear vision of the system's health status,
                        to facilitate decision-making and the implementation of corrective or preventive actions.
                    </p>
                </div>
                
                {trend_section}

                <h2>📊 Key Indicators</h2>
                <p>
                    The figures below summarize the current state of the system.
                    They allow for a quick identification of the volume of errors, the number of affected services,
                    and the overall health level.
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
                        <div class="stat-number {'success' if stats['health_percentage'] > 80 else 'warning' if stats['health_percentage'] > 60 else 'danger'}">{stats.get('health_percentage', 0)}%</div>
                        <div class="stat-label">Health Rate</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number {'danger' if stats['critical_services'] > 0 else 'success'}">{stats.get('critical_services', 0)}</div>
                        <div class="stat-label">Critical Services</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number {'warning' if stats['avg_errors'] > 2 else 'success'}">{stats.get('avg_errors', 0)}</div>
                        <div class="stat-label">Avg Errors/Service</div>
                    </div>
                </div>

                <h2>📈 Advanced Metrics & Insights</h2>
                <div class="advanced-stats-grid">
                    <div class="advanced-stat-card" style="border-left: 4px solid #2ecc71;">
                        <div class="stat-number {'success' if stats.get('stability_index', 0) > 70 else 'warning' if stats.get('stability_index', 0) > 50 else 'danger'}">{stats.get('stability_index', 0)}</div>
                        <div class="stat-label">Stability Index (0-100)</div>
                    </div>
                    <div class="advanced-stat-card" style="border-left: 4px solid #e67e22;">
                        <div class="stat-number">
                            <span class="{stats.get('risk_level', '').lower()}">{stats.get('risk_level', 'N/A')}</span>
                        </div>
                        <div class="stat-label">Risk Level</div>
                    </div>
                    <div class="advanced-stat-card" style="border-left: 4px solid #f1c40f;">
                        <div class="stat-number">{stats.get('top_error_service', 'N/A')}</div>
                        <div class="stat-label">Top Error Service</div>
                    </div>
                    <div class="advanced-stat-card" style="border-left: 4px solid #34495e;">
                        <div class="stat-number {'danger' if stats.get('sla_status') == 'BREACH' else 'warning' if stats.get('sla_status') == 'AT_RISK' else 'success'}">{stats.get('uptime_percentage', 0)}%</div>
                        <div class="stat-label">Uptime Percentage</div>
                    </div>
                </div>
                
                <h2>📋 Service Details</h2>
                <p>
                    Below are the lists of services currently impacted. These lists provide a quick overview of which services require immediate attention.
                </p>
                <div class="service-lists-container">
                    <div class="service-list-card">
                        <h4 style="color: #f39c12;">Services Affected ({stats.get('affected_services', 0)})</h4>
                        {affected_services_html}
                    </div>
                    <div class="service-list-card">
                        <h4 style="color: #e74c3c;">Critical Services ({stats.get('critical_services', 0)})</h4>
                        {critical_services_html}
                    </div>
                </div>
                
                <div class="recommendations">
                    <h3>🎯 Strategic Insights & Action Plan</h3>
                    <p>
                        Here is an interpretation of the results and actions to consider to improve the situation.
                        Please collaborate with the monitoring team to identify the root causes
                        and implement effective solutions.
                    </p>
                    <ul>
                        {recommendation_html}
                    </ul>
                </div>
            </div>
            
            <div class="footer">
                <p><strong>Enhanced MTN Monitoring System</strong> | Generated: {date_str}</p>
                <p>📧 For urgent issues: Contact monitoring team immediately</p>
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
    """Enhanced version of the executive summary with trends and Soft UI design"""
    
    # Global calculations
    total_errors = sum(stats.get('total_errors', 0) for stats in all_stats.values())
    total_services_monitored = sum(stats.get('total_services', 0) for stats in all_stats.values())
    improving_systems = sum(1 for stats in all_stats.values() if stats.get('error_trend', 0) < 0)
    degrading_systems = sum(1 for stats in all_stats.values() if stats.get('error_trend', 0) > 0)
    
    total_affected_services = sum(len(stats.get('affected_services_list', [])) for stats in all_stats.values())
    total_critical_services = sum(len(stats.get('critical_services_list', [])) for stats in all_stats.values())
    
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
        
    # --- Collect lists for detailed sections ---
    # Top 5 degrading services
    all_trends = []
    for system_name, stats in all_stats.items():
        if stats.get('data') is not None and not stats['data'].empty:
            # Check for error_trend and previous_errors to calculate degradation
            current_errors = stats.get('total_errors', 0)
            previous_errors = stats.get('previous_errors', 0)
            if current_errors > previous_errors:
                degradation_amount = current_errors - previous_errors
                all_trends.append({'system': system_name, 'errors': degradation_amount})

    top_degrading_systems = sorted(all_trends, key=lambda x: x['errors'], reverse=True)[:5]
    
    top_degrading_html = ""
    if top_degrading_systems:
        top_degrading_html = "<ul>" + "".join([f"<li><strong>{d['system']}</strong>: +{d['errors']} errors</li>" for d in top_degrading_systems]) + "</ul>"
    else:
        top_degrading_html = "<p>No degrading systems identified.</p>"
    
    # Global critical services list
    all_critical_services_list = []
    for system_name, stats in all_stats.items():
        for service in stats.get('critical_services_list', []):
            all_critical_services_list.append(f"<strong>{system_name}</strong>: {service}")

    critical_services_html = ""
    if all_critical_services_list:
        critical_services_html = "<ul>" + "".join([f"<li>🚨 {s}</li>" for s in all_critical_services_list]) + "</ul>"
    else:
        critical_services_html = "<p>No critical services found across all systems. Excellent!</p>"

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
            
            /* Soft UI Trend Summary avec cartes en ligne */
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
            
            /* Grid pour les métriques en une ligne responsive */
            .trend-metrics-grid {{ 
                display: flex;
                flex-wrap: wrap;
                gap: 20px; 
                justify-content: space-between;
            }}
            .trend-metric-card {{ 
                flex: 1;
                min-width: 160px;
                max-width: 200px;
                text-align: center;
                padding: 25px 20px;
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
                font-size: 2.2rem; 
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
            
            /* Media queries pour la responsivité */
            @media (max-width: 1200px) {{
                .trend-metrics-grid {{
                    justify-content: center;
                }}
                .trend-metric-card {{
                    min-width: 140px;
                    max-width: 180px;
                }}
            }}
            @media (max-width: 768px) {{
                .trend-metrics-grid {{
                    flex-direction: column;
                    align-items: center;
                }}
                .trend-metric-card {{
                    max-width: 280px;
                    width: 100%;
                }}
            }}
            
            .systems-grid {{ 
                display: grid; 
                grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); 
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
                display: flex; 
                justify-content: space-between; 
                gap: 30px; 
                margin-top: 40px; 
            }}
            .list-card {{ 
                flex: 1; 
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
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📊 Executive Dashboard</h1>
                <p style="font-size: 1.3rem; opacity: 0.9; font-weight: 500;">All Systems Performance & Evolution Analysis</p>
                <p style="font-size: 1.1rem; opacity: 0.8;">{date_str}</p>
                <div class="global-status {global_class}">{global_status}</div>
            </div>
            
            <div class="content">
                <div class="trend-summary">
                    <h3>📈 Global Trend Analysis</h3>
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
                            <div class="trend-metric-label">Total Errors</div>
                        </div>
                        <div class="trend-metric-card">
                            <div class="trend-metric-number" style="color: #4a5568;">{total_services_monitored}</div>
                            <div class="trend-metric-label">Services Monitored</div>
                        </div>
                    </div>
                </div>
                
                <h2 style="color: #2d3748; margin: 50px 0 30px; font-size: 2rem; font-weight: 700; text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.8);">🖥️ Systems Performance Dashboard</h2>
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
                        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin: 20px 0;">
                            <div style="text-align: center; padding: 15px; background: linear-gradient(145deg, #edf2f7, #e2e8f0); border-radius: 12px; box-shadow: inset 3px 3px 6px #d1d9e6, inset -3px -3px 6px #ffffff;">
                                <div style="font-size: 1.6rem; font-weight: 800; color: {'#e53e3e' if stats.get('total_errors', 0) > 0 else '#38a169'}; text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.8);">{stats.get('total_errors', 0)}</div>
                                <div style="font-size: 0.9rem; color: #718096; font-weight: 600;">Current Errors</div>
                            </div>
                            <div style="text-align: center; padding: 15px; background: linear-gradient(145deg, #edf2f7, #e2e8f0); border-radius: 12px; box-shadow: inset 3px 3px 6px #d1d9e6, inset -3px -3px 6px #ffffff;">
                                <div style="font-size: 1.6rem; font-weight: 800; color: #4a5568; text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.8);">{stats.get('health_percentage', 0):.1f}%</div>
                                <div style="font-size: 0.9rem; color: #718096; font-weight: 600;">Health Rate</div>
                            </div>
                        </div>
                        <div style="margin-top: 20px; font-size: 0.95rem; color: #4a5568; line-height: 1.6;">
                            <div style="margin-bottom: 8px;">Critical Services: <span style="font-weight: 700; color: {'#e53e3e' if stats.get('critical_services', 0) > 0 else '#38a169'};">{stats.get('critical_services', 0)}</span></div>
                            <div style="margin-bottom: 8px;">Most Impacted: <span style="font-weight: 700; color: #667eea;">{stats.get('top_error_service', 'N/A')}</span></div>
                            {f'<div>Weekly Trend: <span style="font-weight: 700; color: #764ba2;">{stats.get("improvement_rate", 0):+.1f}%</span></div>' if 'improvement_rate' in stats else ''}
                        </div>
                    </div>
        """
    
    html += f"""
                </div>
                
                <h2 style="color: #2d3748; margin: 50px 0 30px; font-size: 2rem; font-weight: 700; text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.8);">❗ Actionable Insights</h2>
                <div class="list-section">
                    <div class="list-card">
                        <h4 style="color: #e53e3e;">Top 5 Degrading Systems ({len(top_degrading_systems)})</h4>
                        {top_degrading_html}
                    </div>
                    <div class="list-card">
                        <h4 style="color: #e53e3e;">Global Critical Services ({len(all_critical_services_list)})</h4>
                        {critical_services_html}
                    </div>
                </div>

                <div class="recommendations">
                    <h3>🎯 Strategic Recommendations</h3>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 30px;">
                        <div style="background: linear-gradient(145deg, #ffffff, #f7fafc); padding: 25px; border-radius: 16px; box-shadow: inset 3px 3px 6px #d1d9e6, inset -3px -3px 6px #ffffff;">
                            <h4 style="color: #742a2a; margin-bottom: 15px; font-size: 1.2rem;">⚡ Immediate Actions:</h4>
                            <ul style="margin: 0; padding-left: 20px; color: #2d3748;">
                                {'<li style="margin-bottom: 8px;">Investigate degrading systems immediately</li>' if degrading_systems > 0 else '<li style="margin-bottom: 8px;">Maintain current monitoring practices</li>'}
                                {'<li style="margin-bottom: 8px;">Replicate improvement strategies across systems</li>' if improving_systems > 0 else '<li style="margin-bottom: 8px;">Review error prevention measures</li>'}
                                <li style="margin-bottom: 8px;">Focus on critical services requiring attention</li>
                            </ul>
                        </div>
                        <div style="background: linear-gradient(145deg, #ffffff, #f7fafc); padding: 25px; border-radius: 16px; box-shadow: inset 3px 3px 6px #d1d9e6, inset -3px -3px 6px #ffffff;">
                            <h4 style="color: #742a2a; margin-bottom: 15px; font-size: 1.2rem;">📊 Strategic Insights:</h4>
                            <ul style="margin: 0; padding-left: 20px; color: #2d3748;">
                                <li style="margin-bottom: 8px;">Track daily trends to identify patterns</li>
                                <li style="margin-bottom: 8px;">Implement predictive maintenance where possible</li>
                                <li style="margin-bottom: 8px;">Document successful improvement strategies</li>
                                <li style="margin-bottom: 8px;">Plan capacity upgrades for consistently problematic services</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="footer">
                <p style="font-size: 1.2rem; font-weight: 700; margin-bottom: 10px;"><strong>🚀 Advanced MTN Systems Monitoring</strong></p>
                <p style="font-size: 1rem; margin-bottom: 10px;">📈 Trend Analysis • 📊 Performance Tracking • ⚡ Real-time Insights</p>
                <p style="font-size: 0.9rem; opacity: 0.9;">Generated: {date_str} | Next Analysis: Tomorrow</p>
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