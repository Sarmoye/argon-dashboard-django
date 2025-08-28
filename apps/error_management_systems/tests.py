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
    
    current = trends_df.iloc[-1]
    previous = trends_df.iloc[-2]
    
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
        trend_yesterday = trends_df.iloc[-2]['total_errors'] - trends_df.iloc[-3]['total_errors']
        if error_trend > trend_yesterday + 2:
            momentum = "ACCELERATING"
        elif error_trend < trend_yesterday - 2:
            momentum = "DECELERATING"
    
    predicted_errors = max(0, current['total_errors'] + error_trend)
    prediction_confidence = "HIGH" if len(trends_df) >= 5 else "MEDIUM" if len(trends_df) >= 3 else "LOW"

    # Ajout des listes de services dans le dictionnaire de retour
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
        'current_critical_services_list': current['critical_services_list']
    }

def create_trend_chart(trends_data, system_name):
    """Crée un graphique de tendance avancé avec prédictions"""
    if not trends_data or trends_data['data'].empty:
        return None
    
    try:
        df = trends_data['data']
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        colors_map = {'CIS': '#e74c3c', 'IRM': '#f39c12', 'ECW': '#27ae60'}
        color = colors_map.get(system_name, '#3498db')
        
        # Graphique 1: Evolution des erreurs avec prédiction
        dates = [d.strftime('%m/%d') for d in df['date']]
        ax1.plot(dates, df['total_errors'], marker='o', linewidth=3, markersize=8, 
                color=color, markerfacecolor='white', markeredgewidth=2, label='Erreurs réelles')
        ax1.fill_between(dates, df['total_errors'], alpha=0.3, color=color)
        
        # Ajouter la prédiction
        if 'predicted_errors' in trends_data:
            pred_date = (df['date'].iloc[-1] + timedelta(days=1)).strftime('%m/%d')
            all_dates = dates + [pred_date]
            pred_line = list(df['total_errors']) + [trends_data['predicted_errors']]
            ax1.plot(all_dates[-2:], pred_line[-2:], 'r--', linewidth=2, alpha=0.7, label='Prédiction')
            ax1.scatter([pred_date], [trends_data['predicted_errors']], color='red', s=100, alpha=0.7)
        
        ax1.set_title(f'{system_name} - Analyse des Tendances & Prédictions', 
                     fontsize=14, fontweight='bold', pad=15)
        ax1.set_ylabel('Erreurs Totales', fontsize=11, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        
        # Graphique 2: Score de fiabilité
        ax2.plot(dates, df['reliability_score'], marker='s', linewidth=2, markersize=6, 
                color='#27ae60', markerfacecolor='white', markeredgewidth=2)
        ax2.fill_between(dates, df['reliability_score'], 95, alpha=0.2, color='green', label='Zone SLA')
        ax2.fill_between(dates, df['reliability_score'], 0, alpha=0.3, color='orange')
        ax2.set_title('Score de Fiabilité (%)', fontsize=12, fontweight='bold')
        ax2.set_ylabel('Fiabilité (%)', fontsize=10)
        ax2.set_ylim(0, 100)
        ax2.grid(True, alpha=0.3)
        ax2.axhline(y=95, color='green', linestyle='--', alpha=0.7, label='SLA Target')
        ax2.legend()
        
        # Graphique 3: Densité d'erreurs
        ax3.bar(dates, df['error_density'], color=color, alpha=0.7)
        ax3.set_title('Densité d\'Erreurs (Erreurs/Service)', fontsize=12, fontweight='bold')
        ax3.set_ylabel('Erreurs par Service', fontsize=10)
        ax3.grid(True, alpha=0.3)
        
        # Graphique 4: Services impactés
        x_pos = range(len(dates))
        width = 0.35
        
        ax4.bar([x - width/2 for x in x_pos], df['affected_services'], width,
               label='Services Affectés', color='#f39c12', alpha=0.8)
        ax4.bar([x + width/2 for x in x_pos], df['critical_services'], width,
               label='Services Critiques', color='#e74c3c', alpha=0.8)
        
        ax4.set_title('Impact sur les Services', fontsize=12, fontweight='bold')
        ax4.set_ylabel('Nombre de Services', fontsize=10)
        ax4.set_xlabel('Date', fontsize=10)
        ax4.set_xticks(x_pos)
        ax4.set_xticklabels(dates)
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        
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
        <div style="background: linear-gradient(135deg, #eaf4fd, #d1e7fd); color: #1f3a5f; padding: 25px; border-radius: 12px; margin: 20px 0; border: 1px solid #cce5ff;">
            <h3 style="margin: 0 0 15px 0; font-size: 1.3rem; color: #004085;">{trend_arrow} Trend Analysis (Last days)</h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
                <div><strong>Current Trend:</strong> <span style="color: {trend_color}; font-weight: bold;">{trend_text}</span></div>
                <div><strong>Error Change (D-1):</strong> <span style="color: {trend_color};">{stats.get('error_trend', 0):+d}</span> ({stats.get('improvement_rate', 0):+.1f}%)</div>
                <div><strong>7-Day Avg Trend:</strong> <span style="color: {trend_color};">{trends_data.get('week_trend', 0):+.1f} avg</span></div>
                <div><strong>Momentum:</strong> <span style="color: {momentum_color}; font-weight: bold;">{momentum.replace('_', ' ')}</span></div>
                <div><strong>Volatility:</strong> <span style="color: {stability_color}; font-weight: bold;">{stability.replace('_', ' ')}</span></div>
                <div><strong>Predicted Errors:</strong> <span style="color: {momentum_colors.get(momentum, 'black')};">{prediction_text}</span></div>
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
            body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 0; background: #f5f7fa; color: #333; }}
            .container {{ max-width: 1200px; margin: 20px auto; background: white; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); overflow: hidden; }}
            .header {{ background: linear-gradient(135deg, #2c3e50, #34495e); color: black; padding: 40px; text-align: center; }}
            .header h1 {{ font-size: 2.5rem; margin: 0 0 10px; font-weight: 700; }}
            .status-badge {{ background: {status_color}; color: black; padding: 12px 25px; border-radius: 25px; font-weight: 600; margin-top: 15px; display: inline-block; }}
            .content {{ padding: 40px; line-height: 1.6; }}
            .intro {{ background: #ecf0f1; padding: 20px; border-radius: 12px; margin-bottom: 25px; border: 1px solid #dfe6e9; }}
            .intro h2 {{ margin-top: 0; color: #2c3e50; }}
            .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 30px 0; }}
            .stat-card {{ background: linear-gradient(135deg, #f8f9fa, #e9ecef); padding: 25px; border-radius: 12px; text-align: center; border-left: 4px solid #3498db; transition: transform 0.2s; }}
            .stat-card:hover {{ transform: translateY(-5px); box-shadow: 0 4px 15px rgba(0,0,0,0.1); }}
            .stat-number {{ font-size: 2.5rem; font-weight: 700; color: #2c3e50; margin-bottom: 8px; }}
            .stat-label {{ font-size: 0.9rem; color: #7f8c8d; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; }}
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
                <div class="stats-grid">
                    <div class="stat-card" style="border-left-color: #2ecc71;">
                        <div class="stat-number {'success' if stats.get('stability_index', 0) > 70 else 'warning' if stats.get('stability_index', 0) > 50 else 'danger'}">{stats.get('stability_index', 0)}</div>
                        <div class="stat-label">Stability Index (0-100)</div>
                    </div>
                    <div class="stat-card" style="border-left-color: #e67e22;">
                        <div class="stat-number">
                            <span class="{stats.get('risk_level', '').lower()}">{stats.get('risk_level', 'N/A')}</span>
                        </div>
                        <div class="stat-label">Risk Level</div>
                    </div>
                    <div class="stat-card" style="border-left-color: #f1c40f;">
                        <div class="stat-number">{stats.get('top_error_service', 'N/A')}</div>
                        <div class="stat-label">Top Error Service</div>
                    </div>
                    <div class="stat-card" style="border-left-color: #34495e;">
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