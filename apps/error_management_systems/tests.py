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
    """Analyse les tendances sur les N derniers jours"""
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
                
                trends_data.append({
                    'date': file_date,
                    'total_errors': total_errors,
                    'affected_services': affected_services,
                    'critical_services': critical_services,
                    'total_services': len(data)
                })
        except Exception as e:
            print(f"Erreur analyse fichier {file_path}: {e}")
            continue
    
    if not trends_data:
        return None
    
    # Convertir en DataFrame et trier par date
    trends_df = pd.DataFrame(trends_data)
    trends_df = trends_df.sort_values('date')
    
    # Calculer les tendances
    if len(trends_df) >= 2:
        current = trends_df.iloc[-1]
        previous = trends_df.iloc[-2]
        
        error_trend = current['total_errors'] - previous['total_errors']
        affected_trend = current['affected_services'] - previous['affected_services']
        critical_trend = current['critical_services'] - previous['critical_services']
        
        # Calculer la tendance sur 7 jours (si assez de données)
        if len(trends_df) >= 4:
            avg_recent = trends_df.tail(3)['total_errors'].mean()
            avg_older = trends_df.head(3)['total_errors'].mean()
            week_trend = avg_recent - avg_older
        else:
            week_trend = error_trend
        
        return {
            'data': trends_df,
            'current_errors': int(current['total_errors']),
            'previous_errors': int(previous['total_errors']),
            'error_trend': int(error_trend),
            'affected_trend': int(affected_trend),
            'critical_trend': int(critical_trend),
            'week_trend': week_trend,
            'improvement_rate': round((error_trend / previous['total_errors'] * 100) if previous['total_errors'] > 0 else 0, 1),
            'days_analyzed': len(trends_df)
        }
    
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

def calculate_enhanced_stats(data, system_name, trends_data=None):
    """Calcule des statistiques avancées avec analyse de tendance"""
    base_stats = {
        'total_errors': 0, 'total_services': 0, 'affected_services': 0,
        'health_percentage': 0, 'critical_services': 0, 'avg_errors': 0,
        'top_error_service': 'N/A', 'status': 'NO_DATA'
    }
    
    if data is None or data.empty:
        if trends_data:
            base_stats.update({
                'error_trend': trends_data.get('error_trend', 0),
                'improvement_rate': trends_data.get('improvement_rate', 0),
                'trend_status': 'NO_DATA'
            })
        return base_stats
    
    # Statistiques de base
    total_errors = int(data['Error Count'].sum())
    total_services = len(data)
    affected_services = int((data['Error Count'] > 0).sum())
    critical_services = int((data['Error Count'] >= 10).sum())
    health_percentage = round(((total_services - affected_services) / total_services) * 100, 1)
    avg_errors = round(total_errors / total_services, 2) if total_services > 0 else 0
    
    # Service le plus impacté
    top_service = 'N/A'
    if total_errors > 0:
        max_idx = data['Error Count'].idxmax()
        top_service = data.loc[max_idx, 'Service Name']
    
    # Statut global
    if total_errors == 0:
        status = 'HEALTHY'
    elif critical_services > 0:
        status = 'CRITICAL'
    else:
        status = 'WARNING'
    
    stats = {
        'total_errors': total_errors,
        'total_services': total_services,
        'affected_services': affected_services,
        'health_percentage': health_percentage,
        'critical_services': critical_services,
        'avg_errors': avg_errors,
        'top_error_service': top_service,
        'status': status
    }
    
    # Ajouter les données de tendance si disponibles
    if trends_data:
        stats.update({
            'error_trend': trends_data.get('error_trend', 0),
            'improvement_rate': trends_data.get('improvement_rate', 0),
            'week_trend': trends_data.get('week_trend', 0),
            'days_analyzed': trends_data.get('days_analyzed', 0),
            'trend_status': 'IMPROVING' if trends_data.get('error_trend', 0) < 0 else 'DEGRADING' if trends_data.get('error_trend', 0) > 0 else 'STABLE'
        })
    
    return stats

def create_professional_system_html_with_trends(system_name, data, stats, date_str, trends_data=None):
    """Crée un rapport HTML professionnel avec analyse de tendance"""
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
    
    status_color, status_text = status_colors[stats['status']]
    
    # Analyse de tendance
    trend_section = ""
    if trends_data and 'error_trend' in stats:
        trend_color, trend_text = trend_colors[stats.get('trend_status', 'STABLE')]
        trend_arrow = '⬇️' if stats['error_trend'] < 0 else '⬆️' if stats['error_trend'] > 0 else '➡️'
        
        trend_section = f"""
        <div style="background: linear-gradient(135deg, {trend_color}, {trend_color}aa); color: black; padding: 25px; border-radius: 12px; margin: 20px 0;">
            <h3 style="margin: 0 0 15px 0; font-size: 1.3rem;">{trend_arrow} TREND ANALYSIS (Last {stats.get('days_analyzed', 7)} days)</h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
                <div>
                    <strong>Error Change:</strong> {stats['error_trend']:+d} 
                    <small>({stats['improvement_rate']:+.1f}%)</small>
                </div>
                <div>
                    <strong>Previous Day:</strong> {trends_data.get('previous_errors', 0)} errors
                </div>
                <div>
                    <strong>Current Day:</strong> {stats['total_errors']} errors
                </div>
                <div>
                    <strong>7-Day Trend:</strong> {stats.get('week_trend', 0):+.1f} avg
                </div>
            </div>
        </div>
        """
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: 'Segoe UI', sans-serif; margin: 0; background: #f5f7fa; color: #333; }}
            .container {{ max-width: 1200px; margin: 20px auto; background: white; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); overflow: hidden; }}
            .header {{ background: linear-gradient(135deg, #2c3e50, #34495e); color: black; padding: 40px; text-align: center; }}
            .header h1 {{ font-size: 2.5rem; margin: 0 0 10px; font-weight: 700; }}
            .status-badge {{ background: {status_color}; color: black; padding: 12px 25px; border-radius: 25px; font-weight: 600; margin-top: 15px; display: inline-block; }}
            .content {{ padding: 40px; }}
            .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 30px 0; }}
            .stat-card {{ background: linear-gradient(135deg, #f8f9fa, #e9ecef); padding: 25px; border-radius: 12px; text-align: center; border-left: 4px solid #3498db; }}
            .stat-number {{ font-size: 2.5rem; font-weight: 700; color: #2c3e50; margin-bottom: 8px; }}
            .stat-label {{ font-size: 0.9rem; color: #7f8c8d; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; }}
            .danger {{ color: #e74c3c !important; }}
            .success {{ color: #27ae60 !important; }}
            .warning {{ color: #f39c12 !important; }}
            .recommendations {{ background: linear-gradient(135deg, #74b9ff, #0984e3); color: black; padding: 30px; border-radius: 12px; margin: 30px 0; }}
            .recommendations h3 {{ margin-bottom: 20px; font-size: 1.4rem; }}
            .footer {{ background: #2c3e50; color: white; padding: 25px; text-align: center; }}
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
                {trend_section}
                
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-number {'danger' if stats['total_errors'] > 0 else 'success'}">{stats['total_errors']}</div>
                        <div class="stat-label">Total Errors</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{stats['total_services']}</div>
                        <div class="stat-label">Total Services</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number {'danger' if stats['affected_services'] > 0 else 'success'}">{stats['affected_services']}</div>
                        <div class="stat-label">Affected Services</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number {'success' if stats['health_percentage'] > 80 else 'warning' if stats['health_percentage'] > 60 else 'danger'}">{stats['health_percentage']}%</div>
                        <div class="stat-label">Health Rate</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number {'danger' if stats['critical_services'] > 0 else 'success'}">{stats['critical_services']}</div>
                        <div class="stat-label">Critical Services</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number {'warning' if stats['avg_errors'] > 2 else 'success'}">{stats['avg_errors']}</div>
                        <div class="stat-label">Avg Errors/Service</div>
                    </div>
                </div>
                
                <div class="recommendations">
                    <h3>🎯 Strategic Insights & Action Plan</h3>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px;">
                        <div>
                            <h4>📊 Current Status:</h4>
                            <ul>
                                {'<li>🚨 ' + str(stats["critical_services"]) + ' critical services need immediate attention</li>' if stats.get('critical_services', 0) > 0 else ''}
                                {'<li>⚠️ ' + str(stats["affected_services"]) + ' services showing errors</li>' if stats.get('affected_services', 0) > 0 else ''}
                                {'<li>✅ No errors detected - maintain practices</li>' if stats.get('total_errors', 0) == 0 else ''}
                                <li>📈 Health Score: {stats.get('health_percentage', 0)}%</li>
                            </ul>
                        </div>
                        <div>
                            <h4>📈 Trend Analysis:</h4>
                            <ul>
                                {'<li>✅ Improving: ' + str(abs(stats.get("error_trend", 0))) + ' fewer errors than yesterday</li>' if stats.get('error_trend', 0) < 0 else ''}
                                {'<li>⚠️ Degrading: ' + str(stats.get("error_trend", 0)) + ' more errors than yesterday</li>' if stats.get('error_trend', 0) > 0 else ''}
                                {'<li>➡️ Stable: No change from yesterday</li>' if stats.get('error_trend', 0) == 0 else ''}
                                <li>📊 Weekly trend: {stats.get('improvement_rate', 0):+.1f}%</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="footer">
                <p><strong>Enhanced MTN Monitoring System</strong> | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
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

def create_executive_summary_html_with_trends(systems_data, all_stats, date_str):
    """Version améliorée du résumé exécutif avec tendances"""
    # Calculs globaux
    total_errors = sum(stats.get('total_errors', 0) for stats in all_stats.values())
    total_services = sum(stats.get('total_services', 0) for stats in all_stats.values())
    improving_systems = sum(1 for stats in all_stats.values() if stats.get('error_trend', 0) < 0)
    degrading_systems = sum(1 for stats in all_stats.values() if stats.get('error_trend', 0) > 0)
    
    # Statut global avec tendance
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
    
    # Ajout des cartes système avec tendances
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