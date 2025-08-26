#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import glob
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
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

# Configuration email
EMAIL_CONFIG = {
    'smtp_server': '10.77.152.66',
    'smtp_port': 25,
    'from_email': 'noreply.errormonitor@mtn.com',
    'cis_recipients': ['Sarmoye.AmitoureHaidara@mtn.com'],
    'irm_recipients': ['Sarmoye.AmitoureHaidara@mtn.com'],
    'ecw_recipients': ['Sarmoye.AmitoureHaidara@mtn.com'],
    'summary_recipients': ['Sarmoye.AmitoureHaidara@mtn.com']
}

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

def get_matching_csv_file(directory, reference_filename):
    """Récupère un fichier CSV correspondant"""
    try:
        base_name = os.path.splitext(os.path.basename(reference_filename))[0]
        matching_file = os.path.join(directory, f"{base_name}.csv")
        return matching_file if os.path.exists(matching_file) else None
    except:
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

def calculate_enhanced_stats(data, system_name):
    """Calcule des statistiques avancées"""
    if data is None or data.empty:
        return {
            'total_errors': 0, 'total_services': 0, 'affected_services': 0,
            'health_percentage': 0, 'critical_services': 0, 'avg_errors': 0,
            'top_error_service': 'N/A', 'status': 'NO_DATA'
        }
    
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
    
    return {
        'total_errors': total_errors,
        'total_services': total_services,
        'affected_services': affected_services,
        'health_percentage': health_percentage,
        'critical_services': critical_services,
        'avg_errors': avg_errors,
        'top_error_service': top_service,
        'status': status
    }

def create_enhanced_chart(data, system_name):
    """Crée un graphique professionnel"""
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

def create_summary_chart(systems_stats):
    """Crée un graphique de synthèse comparatif"""
    try:
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(20, 16))
        fig.suptitle('Systems Performance Dashboard', fontsize=24, fontweight='bold', y=0.95)
        
        systems = list(systems_stats.keys())
        colors_map = {'CIS': '#e74c3c', 'IRM': '#f39c12', 'ECW': '#27ae60'}
        colors = [colors_map.get(s, '#3498db') for s in systems]
        
        # 1. Total Errors
        total_errors = [stats['total_errors'] for stats in systems_stats.values()]
        bars1 = ax1.bar(systems, total_errors, color=colors, alpha=0.8)
        ax1.set_title('Total Errors by System', fontsize=16, fontweight='bold')
        ax1.set_ylabel('Total Errors', fontweight='bold')
        ax1.grid(axis='y', alpha=0.3)
        for bar in bars1:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height, f'{int(height)}',
                    ha='center', va='bottom', fontweight='bold')
        
        # 2. Health Rate
        health_rates = [stats['health_percentage'] for stats in systems_stats.values()]
        bars2 = ax2.bar(systems, health_rates, color='#2ecc71', alpha=0.8)
        ax2.set_title('System Health Rate (%)', fontsize=16, fontweight='bold')
        ax2.set_ylabel('Health Rate (%)', fontweight='bold')
        ax2.set_ylim(0, 100)
        ax2.grid(axis='y', alpha=0.3)
        for bar, rate in zip(bars2, health_rates):
            ax2.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 1, f'{rate:.1f}%',
                    ha='center', va='bottom', fontweight='bold')
        
        # 3. Services Affected
        affected = [stats['affected_services'] for stats in systems_stats.values()]
        bars3 = ax3.bar(systems, affected, color='#e74c3c', alpha=0.7)
        ax3.set_title('Affected Services', fontsize=16, fontweight='bold')
        ax3.set_ylabel('Affected Services', fontweight='bold')
        ax3.grid(axis='y', alpha=0.3)
        for bar in bars3:
            height = bar.get_height()
            ax3.text(bar.get_x() + bar.get_width()/2., height, f'{int(height)}',
                    ha='center', va='bottom', fontweight='bold')
        
        # 4. Critical Services
        critical = [stats['critical_services'] for stats in systems_stats.values()]
        bars4 = ax4.bar(systems, critical, color='#8e44ad', alpha=0.8)
        ax4.set_title('Critical Services (10+ errors)', fontsize=16, fontweight='bold')
        ax4.set_ylabel('Critical Services', fontweight='bold')
        ax4.grid(axis='y', alpha=0.3)
        for bar in bars4:
            height = bar.get_height()
            ax4.text(bar.get_x() + bar.get_width()/2., height, f'{int(height)}',
                    ha='center', va='bottom', fontweight='bold')
        
        plt.tight_layout()
        
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight', facecolor='white')
        buffer.seek(0)
        chart_data = buffer.getvalue()
        buffer.close()
        plt.close()
        
        return chart_data
    except Exception as e:
        print(f"Erreur graphique synthèse: {e}")
        plt.close()
        return None

def create_professional_system_html(system_name, data, stats, date_str):
    """Crée un rapport HTML professionnel pour un système"""
    status_colors = {
        'HEALTHY': ('#27ae60', '✅ SYSTEM HEALTHY'),
        'WARNING': ('#f39c12', '⚠️ SYSTEM WARNING'), 
        'CRITICAL': ('#e74c3c', '🔴 SYSTEM CRITICAL'),
        'NO_DATA': ('#95a5a6', '⚪ NO DATA')
    }
    
    status_color, status_text = status_colors[stats['status']]
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: 'Segoe UI', sans-serif; margin: 0; background: #f5f7fa; color: #333; }}
            .container {{ max-width: 1200px; margin: 20px auto; background: white; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); overflow: hidden; }}
            .header {{ background: linear-gradient(135deg, #2c3e50, #34495e); color: white; padding: 40px; text-align: center; }}
            .header h1 {{ font-size: 2.5rem; margin: 0 0 10px; font-weight: 700; }}
            .status-badge {{ background: {status_color}; color: white; padding: 12px 25px; border-radius: 25px; font-weight: 600; margin-top: 15px; display: inline-block; }}
            .content {{ padding: 40px; }}
            .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 30px 0; }}
            .stat-card {{ background: linear-gradient(135deg, #f8f9fa, #e9ecef); padding: 25px; border-radius: 12px; text-align: center; border-left: 4px solid #3498db; }}
            .stat-number {{ font-size: 2.5rem; font-weight: 700; color: #2c3e50; margin-bottom: 8px; }}
            .stat-label {{ font-size: 0.9rem; color: #7f8c8d; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; }}
            .danger {{ color: #e74c3c !important; }}
            .success {{ color: #27ae60 !important; }}
            .warning {{ color: #f39c12 !important; }}
            .table-section {{ background: white; border-radius: 12px; margin: 30px 0; box-shadow: 0 5px 15px rgba(0,0,0,0.05); }}
            .table-title {{ background: #34495e; color: white; padding: 20px; font-size: 1.2rem; font-weight: 600; margin: 0; }}
            .table {{ width: 100%; border-collapse: collapse; }}
            .table th {{ background: #2c3e50; color: white; padding: 15px; text-align: left; font-weight: 600; }}
            .table td {{ padding: 12px 15px; border-bottom: 1px solid #ecf0f1; }}
            .table tbody tr:hover {{ background: #f8f9fa; }}
            .table .success {{ background: #d4edda; color: #155724; font-weight: 600; }}
            .table .warning {{ background: #fff3cd; color: #856404; font-weight: 600; }}
            .table .danger {{ background: #f8d7da; color: #721c24; font-weight: 600; }}
            .recommendations {{ background: linear-gradient(135deg, #74b9ff, #0984e3); color: white; padding: 30px; border-radius: 12px; margin: 30px 0; }}
            .recommendations h3 {{ margin-bottom: 20px; font-size: 1.4rem; }}
            .recommendations ul {{ margin-left: 20px; }}
            .footer {{ background: #2c3e50; color: white; padding: 25px; text-align: center; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>System {system_name}</h1>
                <p>Error Analysis Report - {date_str}</p>
                <div class="status-badge">{status_text}</div>
            </div>
            
            <div class="content">
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
                
                {create_detailed_table(data, f"{system_name} - Detailed Analysis") if data is not None and not data.empty else '<div style="text-align: center; padding: 40px; color: #7f8c8d;"><h3>No data available</h3></div>'}
                
                <div class="recommendations">
                    <h3>🎯 Key Insights & Recommendations</h3>
                    <ul>
                        {'<li>🚨 Critical: ' + str(stats["critical_services"]) + ' services need immediate attention</li>' if stats['critical_services'] > 0 else ''}
                        {'<li>⚠️ Monitor: ' + str(stats["affected_services"]) + ' services showing errors</li>' if stats['affected_services'] > 0 and stats['critical_services'] == 0 else ''}
                        {'<li>✅ Excellent: No errors detected - maintain current practices</li>' if stats['total_errors'] == 0 else ''}
                        <li>📊 Health Score: {stats['health_percentage']}% {'(Above target)' if stats['health_percentage'] > 85 else '(Needs improvement)' if stats['health_percentage'] < 70 else '(Acceptable)'}</li>
                        {'<li>🎯 Focus on: ' + stats["top_error_service"] + ' (highest error count)</li>' if stats['top_error_service'] != 'N/A' else ''}
                    </ul>
                </div>
            </div>
            
            <div class="footer">
                <p><strong>Automated Monitoring System</strong> | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
        </div>
    </body>
    </html>
    """

def create_executive_summary_html(systems_data, all_stats, date_str):
    """Crée un rapport de synthèse exécutif"""
    total_errors = sum(stats['total_errors'] for stats in all_stats.values())
    total_services = sum(stats['total_services'] for stats in all_stats.values())
    critical_systems = sum(1 for stats in all_stats.values() if stats['critical_services'] > 0)
    healthy_systems = sum(1 for stats in all_stats.values() if stats['total_errors'] == 0)
    
    # Statut global
    if critical_systems > 0:
        global_status = "🔴 CRITICAL ISSUES DETECTED"
        global_class = "danger"
    elif total_errors > 0:
        global_status = "⚠️ MONITORING REQUIRED"
        global_class = "warning"
    else:
        global_status = "✅ ALL SYSTEMS HEALTHY"
        global_class = "success"
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: 'Segoe UI', sans-serif; margin: 0; background: #f5f7fa; }}
            .container {{ max-width: 1400px; margin: 20px auto; background: white; border-radius: 15px; box-shadow: 0 15px 35px rgba(0,0,0,0.1); }}
            .header {{ background: linear-gradient(135deg, #1e3c72, #2a5298); color: white; padding: 50px; text-align: center; }}
            .header h1 {{ font-size: 3rem; margin: 0 0 15px; font-weight: 700; }}
            .global-status {{ padding: 15px 30px; border-radius: 25px; font-weight: 700; margin-top: 20px; display: inline-block; }}
            .content {{ padding: 50px; }}
            .overview-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 25px; margin: 40px 0; }}
            .overview-card {{ background: linear-gradient(135deg, #f8f9fa, #e9ecef); padding: 30px; border-radius: 15px; text-align: center; transition: transform 0.3s; }}
            .overview-card:hover {{ transform: translateY(-5px); box-shadow: 0 15px 30px rgba(0,0,0,0.1); }}
            .overview-number {{ font-size: 3rem; font-weight: 700; margin-bottom: 10px; }}
            .overview-label {{ font-size: 1rem; color: #7f8c8d; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; }}
            .systems-comparison {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 25px; margin: 40px 0; }}
            .system-card {{ background: white; border-radius: 12px; padding: 25px; box-shadow: 0 8px 20px rgba(0,0,0,0.08); border-left: 5px solid #3498db; }}
            .system-card.cis {{ border-left-color: #e74c3c; }}
            .system-card.irm {{ border-left-color: #f39c12; }}
            .system-card.ecw {{ border-left-color: #27ae60; }}
            .system-name {{ font-size: 1.3rem; font-weight: 700; margin-bottom: 15px; }}
            .system-metrics {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; text-align: center; }}
            .metric {{ padding: 10px; background: #f8f9fa; border-radius: 8px; }}
            .metric-value {{ font-size: 1.4rem; font-weight: 700; display: block; }}
            .metric-label {{ font-size: 0.8rem; color: #7f8c8d; }}
            .danger {{ color: #e74c3c; }}
            .success {{ color: #27ae60; }}
            .warning {{ color: #f39c12; }}
            .recommendations {{ background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 35px; border-radius: 12px; margin: 40px 0; }}
            .footer {{ background: #2c3e50; color: white; padding: 30px; text-align: center; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Executive Summary</h1>
                <p style="font-size: 1.2rem; opacity: 0.9;">All Systems Monitoring Report</p>
                <p>{date_str}</p>
                <div class="global-status {global_class}">{global_status}</div>
            </div>
            
            <div class="content">
                <div class="overview-grid">
                    <div class="overview-card">
                        <div class="overview-number {'danger' if total_errors > 0 else 'success'}">{total_errors}</div>
                        <div class="overview-label">Total Errors</div>
                    </div>
                    <div class="overview-card">
                        <div class="overview-number">{total_services}</div>
                        <div class="overview-label">Total Services</div>
                    </div>
                    <div class="overview-card">
                        <div class="overview-number success">{healthy_systems}</div>
                        <div class="overview-label">Healthy Systems</div>
                    </div>
                    <div class="overview-card">
                        <div class="overview-number {'danger' if critical_systems > 0 else 'success'}">{critical_systems}</div>
                        <div class="overview-label">Critical Systems</div>
                    </div>
                </div>
                
                <h2 style="color: #2c3e50; margin: 40px 0 25px; font-size: 1.8rem;">📊 Systems Comparison</h2>
                <div class="systems-comparison">
    """
    
    for system_name, stats in all_stats.items():
        system_class = system_name.lower()
        html += f"""
                    <div class="system-card {system_class}">
                        <h3 class="system-name">{system_name}</h3>
                        <div class="system-metrics">
                            <div class="metric">
                                <span class="metric-value {'danger' if stats['total_errors'] > 0 else 'success'}">{stats['total_errors']}</span>
                                <span class="metric-label">Errors</span>
                            </div>
                            <div class="metric">
                                <span class="metric-value">{stats['health_percentage']}%</span>
                                <span class="metric-label">Health</span>
                            </div>
                            <div class="metric">
                                <span class="metric-value {'danger' if stats['critical_services'] > 0 else 'success'}">{stats['critical_services']}</span>
                                <span class="metric-label">Critical</span>
                            </div>
                        </div>
                        <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #ecf0f1; font-size: 0.9rem; color: #7f8c8d;">
                            Most impacted: <strong>{stats['top_error_service']}</strong>
                        </div>
                    </div>
        """
    
    # Tableaux détaillés pour chaque système
    for system_name, data in systems_data.items():
        if data is not None and not data.empty:
            html += f"""
                <h2 style="color: #2c3e50; margin: 40px 0 20px; font-size: 1.6rem;">🖥️ {system_name} System Details</h2>
                {create_detailed_table(data, f"{system_name} Complete Report")}
            """
    
    html += f"""
                </div>
                
                <div class="recommendations">
                    <h3 style="font-size: 1.5rem; margin-bottom: 20px;">🎯 Executive Recommendations</h3>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px;">
                        <div>
                            <h4>Immediate Actions:</h4>
                            <ul>
                                {'<li>Address ' + str(critical_systems) + ' critical system(s)</li>' if critical_systems > 0 else '<li>Maintain current monitoring practices</li>'}
                                {'<li>Investigate ' + str(total_errors) + ' total errors</li>' if total_errors > 0 else '<li>Continue preventive maintenance</li>'}
                                <li>Review high-impact services</li>
                            </ul>
                        </div>
                        <div>
                            <h4>Strategic Planning:</h4>
                            <ul>
                                <li>Enhance monitoring for critical services</li>
                                <li>Implement predictive maintenance</li>
                                <li>Review system capacity planning</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="footer">
                <p><strong>MTN Systems Monitoring</strong> | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p>For urgent issues: Contact monitoring team immediately</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html

def create_detailed_table(data, title):
    """Crée un tableau détaillé professionnel"""
    if data is None or data.empty:
        return '<div style="text-align: center; padding: 40px; color: #7f8c8d;"><h3>No data available</h3></div>'
    
    html = f"""
    <div class="table-section">
        <h3 class="table-title">{title}</h3>
        <table class="table">
            <thead><tr>
    """
    
    for col in data.columns:
        html += f"<th>{col}</th>"
    
    html += "</tr></thead><tbody>"
    
    for _, row in data.iterrows():
        html += "<tr>"
        for col, value in row.items():
            if col == 'Error Count' and pd.notna(value):
                try:
                    error_count = int(float(value))
                    cell_class = 'success' if error_count == 0 else 'warning' if error_count <= 5 else 'danger'
                except:
                    cell_class = ''
            else:
                cell_class = ''
            
            display_value = value if pd.notna(value) and str(value).strip() != '' else '-'
            html += f'<td class="{cell_class}">{display_value}</td>'
        
        html += "</tr>"
    
    html += """
        </tbody>
    </table>
    </div>
    """
    
    return html

def send_email_with_reports(from_email, to_emails, subject, html_body, chart_images, attachment_file=None):
    """Envoie un email avec les rapports et graphiques"""
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

def generate_daily_reports():
    """Génère et envoie tous les rapports quotidiens"""
    print(f"=== GÉNÉRATION DES RAPPORTS QUOTIDIENS ===")
    print(f"Démarrage: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    date_str = datetime.now().strftime('%Y-%m-%d')
    systems_data = {}
    all_stats = {}
    
    # === TRAITEMENT CIS ===
    print("\n🔴 Traitement système CIS...")
    cis_file = get_latest_csv_file(CIS_ERROR_REPORT_OUTPUT_DIR)
    if cis_file:
        cis_data = read_csv_data(cis_file, "CIS")
        if cis_data is not None:
            cis_stats = calculate_enhanced_stats(cis_data, "CIS")
            systems_data['CIS'] = cis_data
            all_stats['CIS'] = cis_stats
            
            # Rapport et graphique CIS
            html_body = create_professional_system_html('CIS', cis_data, cis_stats, date_str)
            chart = create_enhanced_chart(cis_data, "CIS")
            charts = [chart] if chart else []
            
            send_email_with_reports(
                EMAIL_CONFIG['from_email'],
                EMAIL_CONFIG['cis_recipients'],
                f"🔴 CIS SYSTEM ERROR REPORT - {date_str}",
                html_body,
                charts
            )
            print(f"   ✓ Rapport CIS envoyé (Statut: {cis_stats['status']})")
        else:
            all_stats['CIS'] = calculate_enhanced_stats(None, "CIS")
            print("   ⚠ Aucune donnée CIS trouvée")
    else:
        all_stats['CIS'] = calculate_enhanced_stats(None, "CIS")
        print("   ⚠ Fichier CIS non trouvé")
    
    # === TRAITEMENT ECW ===
    print("\n🟢 Traitement système ECW...")
    ecw_file = get_latest_csv_file(ECW_ERROR_REPORT_OUTPUT_DIR)
    if ecw_file:
        ecw_data = read_csv_data(ecw_file, "ECW")
        if ecw_data is not None:
            ecw_stats = calculate_enhanced_stats(ecw_data, "ECW")
            systems_data['ECW'] = ecw_data
            all_stats['ECW'] = ecw_stats
            
            # Pièce jointe supplémentaire
            ecw_attachment = get_matching_csv_file(ECW_ERROR_REPORT_OUTPUT_DIR2, ecw_file)
            
            # Rapport et graphique ECW
            html_body = create_professional_system_html('ECW', ecw_data, ecw_stats, date_str)
            chart = create_enhanced_chart(ecw_data, "ECW")
            charts = [chart] if chart else []
            
            send_email_with_reports(
                EMAIL_CONFIG['from_email'],
                EMAIL_CONFIG['ecw_recipients'],
                f"🟢 ECW SYSTEM ERROR REPORT - {date_str}",
                html_body,
                charts,
                ecw_attachment
            )
            print(f"   ✓ Rapport ECW envoyé (Statut: {ecw_stats['status']})")
        else:
            all_stats['ECW'] = calculate_enhanced_stats(None, "ECW")
            print("   ⚠ Aucune donnée ECW trouvée")
    else:
        all_stats['ECW'] = calculate_enhanced_stats(None, "ECW")
        print("   ⚠ Fichier ECW non trouvé")
    
    # === TRAITEMENT IRM ===
    print("\n🟡 Traitement système IRM...")
    irm_file = get_latest_csv_file(IRM_ERROR_REPORT_OUTPUT_DIR)
    if irm_file:
        irm_data = read_csv_data(irm_file, "IRM")
        if irm_data is not None:
            irm_stats = calculate_enhanced_stats(irm_data, "IRM")
            systems_data['IRM'] = irm_data
            all_stats['IRM'] = irm_stats
            
            # Rapport et graphique IRM
            html_body = create_professional_system_html('IRM', irm_data, irm_stats, date_str)
            chart = create_enhanced_chart(irm_data, "IRM")
            charts = [chart] if chart else []
            
            send_email_with_reports(
                EMAIL_CONFIG['from_email'],
                EMAIL_CONFIG['irm_recipients'],
                f"🟡 IRM SYSTEM ERROR REPORT - {date_str}",
                html_body,
                charts
            )
            print(f"   ✓ Rapport IRM envoyé (Statut: {irm_stats['status']})")
        else:
            all_stats['IRM'] = calculate_enhanced_stats(None, "IRM")
            print("   ⚠ Aucune donnée IRM trouvée")
    else:
        all_stats['IRM'] = calculate_enhanced_stats(None, "IRM")
        print("   ⚠ Fichier IRM non trouvé")
    
    # === RAPPORT DE SYNTHÈSE EXÉCUTIF ===
    print("\n📊 Génération du rapport de synthèse exécutif...")
    if all_stats:
        summary_html = create_executive_summary_html(systems_data, all_stats, date_str)
        summary_chart = create_summary_chart(all_stats)
        summary_charts = [summary_chart] if summary_chart else []
        
        # Déterminer le niveau de priorité pour le sujet
        critical_count = sum(1 for stats in all_stats.values() if stats['status'] == 'CRITICAL')
        total_errors = sum(stats['total_errors'] for stats in all_stats.values())
        
        if critical_count > 0:
            priority = "🚨 URGENT"
        elif total_errors > 0:
            priority = "⚠️ ACTION REQUIRED"
        else:
            priority = "✅ ALL CLEAR"
        
        send_email_with_reports(
            EMAIL_CONFIG['from_email'],
            EMAIL_CONFIG['summary_recipients'],
            f"{priority} - EXECUTIVE SUMMARY - ALL SYSTEMS - {date_str}",
            summary_html,
            summary_charts
        )
        print("   ✓ Rapport de synthèse exécutif envoyé")
    
    # === RÉSUMÉ FINAL ===
    print(f"\n{'='*50}")
    print("📈 RÉSUMÉ DE L'EXÉCUTION:")
    print(f"{'='*50}")
    
    total_errors_all = sum(stats['total_errors'] for stats in all_stats.values())
    total_services_all = sum(stats['total_services'] for stats in all_stats.values())
    critical_systems = sum(1 for stats in all_stats.values() if stats['status'] == 'CRITICAL')
    
    print(f"📊 Erreurs totales détectées: {total_errors_all}")
    print(f"🔧 Services monitrés: {total_services_all}")
    print(f"🚨 Systèmes critiques: {critical_systems}")
    print(f"📧 Rapports envoyés: {len(systems_data) + 1}")  # +1 pour le résumé
    
    for system, stats in all_stats.items():
        status_icon = {'HEALTHY': '✅', 'WARNING': '⚠️', 'CRITICAL': '🚨', 'NO_DATA': '⚪'}[stats['status']]
        print(f"   {status_icon} {system}: {stats['total_errors']} erreurs ({stats['status']})")
    
    print(f"\n✅ TOUS LES RAPPORTS GÉNÉRÉS AVEC SUCCÈS!")
    print(f"⏰ Terminé: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}")

def main():
    """Fonction principale"""
    try:
        # Configuration matplotlib
        plt.style.use('default')
        sns.set_palette("husl")
        
        # Génération des rapports
        generate_daily_reports()
        
    except Exception as e:
        print(f"❌ ERREUR CRITIQUE: {e}")
        print("Contactez l'équipe technique immédiatement!")

if __name__ == "__main__":
    main()