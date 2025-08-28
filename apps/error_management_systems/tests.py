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
import logging
import traceback
import sys

# Configure logging
def setup_logging():
    """Configure comprehensive logging for the application"""
    # Create logs directory if it doesn't exist
    log_dir = "/var/log/error_monitor"
    os.makedirs(log_dir, exist_ok=True)
    
    # Generate log filename with timestamp
    log_filename = f"error_monitor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    log_filepath = os.path.join(log_dir, log_filename)
    
    # Create logger
    logger = logging.getLogger('ErrorMonitor')
    logger.setLevel(logging.DEBUG)
    
    # Remove any existing handlers
    logger.handlers.clear()
    
    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s - %(message)s'
    )
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # File handler (logs everything)
    file_handler = logging.FileHandler(log_filepath, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)
    
    # Console handler (only warnings and above)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Log startup information
    logger.info("=" * 60)
    logger.info("Error Monitoring System Started")
    logger.info("=" * 60)
    logger.info(f"Log file: {log_filepath}")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Working directory: {os.getcwd()}")
    
    return logger, log_filepath

# Initialize logging
logger, log_filepath = setup_logging()

# Suppress warnings
warnings.filterwarnings('ignore')

# Configuration des répertoires
CIS_ERROR_REPORT_OUTPUT_DIR = "/srv/itsea_files/cis_error_report_files"
ECW_ERROR_REPORT_OUTPUT_DIR = "/srv/itsea_files/ecw_error_report_files"
ECW_ERROR_REPORT_OUTPUT_DIR2 = "/srv/itsea_files/ecw_error_report_files_second"
IRM_ERROR_REPORT_OUTPUT_DIR = "/srv/itsea_files/irm_error_report_files"

# Verify directories exist
for dir_path in [CIS_ERROR_REPORT_OUTPUT_DIR, ECW_ERROR_REPORT_OUTPUT_DIR, 
                 ECW_ERROR_REPORT_OUTPUT_DIR2, IRM_ERROR_REPORT_OUTPUT_DIR]:
    if not os.path.exists(dir_path):
        logger.warning(f"Directory does not exist: {dir_path}")
        os.makedirs(dir_path, exist_ok=True)
        logger.info(f"Created directory: {dir_path}")

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

def log_function_call(func):
    """Decorator to log function calls with parameters"""
    def wrapper(*args, **kwargs):
        func_name = func.__name__
        logger.debug(f"Calling {func_name} with args: {args}, kwargs: {kwargs}")
        try:
            result = func(*args, **kwargs)
            logger.debug(f"Function {func_name} completed successfully")
            return result
        except Exception as e:
            logger.error(f"Function {func_name} failed with error: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    return wrapper

@log_function_call
def get_files_by_date_range(directory, days=7):
    """Récupère les fichiers CSV des N derniers jours"""
    try:
        logger.info(f"Looking for CSV files in {directory} from the last {days} days")
        csv_files = glob.glob(os.path.join(directory, "*.csv"))
        
        if not csv_files:
            logger.warning(f"No CSV files found in directory: {directory}")
            return []
        
        # Filtrer les fichiers des 7 derniers jours
        now = datetime.now()
        recent_files = []
        
        for file_path in csv_files:
            try:
                file_time = datetime.fromtimestamp(os.path.getctime(file_path))
                if (now - file_time).days <= days:
                    recent_files.append((file_path, file_time))
                    logger.debug(f"Included file: {file_path} (created: {file_time})")
                else:
                    logger.debug(f"Excluded file (too old): {file_path}")
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {e}")
                continue
        
        # Trier par date (plus récent d'abord)
        recent_files.sort(key=lambda x: x[1], reverse=True)
        result = [f[0] for f in recent_files]
        
        logger.info(f"Found {len(result)} recent files in {directory}")
        return result
        
    except Exception as e:
        logger.error(f"Error retrieving files from {directory}: {e}")
        logger.error(traceback.format_exc())
        return []

@log_function_call
def get_latest_csv_file(directory):
    """Récupère le fichier CSV le plus récent"""
    try:
        logger.info(f"Looking for latest CSV file in {directory}")
        csv_files = glob.glob(os.path.join(directory, "*.csv"))
        
        if not csv_files:
            logger.warning(f"No CSV files found in directory: {directory}")
            return None
            
        latest_file = max(csv_files, key=os.path.getctime)
        file_time = datetime.fromtimestamp(os.path.getctime(latest_file))
        
        logger.info(f"Latest file in {directory}: {latest_file} (created: {file_time})")
        return latest_file
        
    except Exception as e:
        logger.error(f"Error finding latest CSV file in {directory}: {e}")
        logger.error(traceback.format_exc())
        return None

@log_function_call
def read_csv_data(file_path, system_name=None):
    """Lit et traite les données CSV"""
    try:
        logger.info(f"Reading CSV data from {file_path} for system {system_name}")
        
        if system_name in ["CIS", "IRM"]:
            headers = ['Domain', 'Service Type', 'Service Name', 'Error Count', 'Error Reason']
        else:
            headers = ['Domain', 'Service Type', 'Service Name', 'Error Count']

        skip_rows = 1 if system_name == "IRM" else 0
        df = pd.read_csv(file_path, header=None, names=headers, skiprows=skip_rows)
        
        logger.info(f"CSV file loaded successfully. Shape: {df.shape}")
        
        if 'Error Count' in df.columns:
            df['Error Count'] = pd.to_numeric(df['Error Count'], errors='coerce').fillna(0)
            logger.debug(f"Error Count column processed. Summary: {df['Error Count'].describe().to_dict()}")
        
        return df
        
    except Exception as e:
        logger.error(f"Error reading CSV file {file_path}: {e}")
        logger.error(traceback.format_exc())
        return None

@log_function_call
def analyze_historical_trends(directory, system_name, days=7):
    """Analyse les tendances sur les N derniers jours"""
    try:
        logger.info(f"Analyzing historical trends for {system_name} in {directory} over {days} days")
        
        files = get_files_by_date_range(directory, days)
        if len(files) < 2:
            logger.warning(f"Not enough files ({len(files)}) for trend analysis in {directory}")
            return None
        
        trends_data = []
        
        for file_path in files:
            try:
                logger.debug(f"Processing file for trends: {file_path}")
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
                    
                    logger.debug(f"File analysis: {total_errors} errors, {affected_services} affected services")
            except Exception as e:
                logger.error(f"Error analyzing file {file_path}: {e}")
                continue
        
        if not trends_data:
            logger.warning("No trend data could be processed")
            return None
        
        # Convertir en DataFrame et trier par date
        trends_df = pd.DataFrame(trends_data)
        trends_df = trends_df.sort_values('date')
        
        logger.info(f"Trend data prepared with {len(trends_df)} data points")
        
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
                logger.debug("7-day trend calculated")
            else:
                week_trend = error_trend
                logger.debug("Using daily trend for weekly trend (not enough data)")
            
            result = {
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
            
            logger.info(f"Trend analysis complete. Error trend: {error_trend}, Improvement rate: {result['improvement_rate']}%")
            return result
        
        logger.warning("Not enough data points for trend calculation")
        return None
        
    except Exception as e:
        logger.error(f"Error in historical trend analysis: {e}")
        logger.error(traceback.format_exc())
        return None

@log_function_call
def create_trend_chart(trends_data, system_name):
    """Crée un graphique de tendance sur 7 jours"""
    if not trends_data or trends_data['data'].empty:
        logger.warning("No data available for trend chart")
        return None
    
    try:
        logger.info(f"Creating trend chart for {system_name}")
        
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
        
        logger.info("Trend chart created successfully")
        return chart_data
        
    except Exception as e:
        logger.error(f"Error creating trend chart: {e}")
        logger.error(traceback.format_exc())
        plt.close()
        return None

@log_function_call
def calculate_enhanced_stats(data, system_name, trends_data=None):
    """Calcule des statistiques avancées avec analyse de tendance"""
    logger.info(f"Calculating enhanced stats for {system_name}")
    
    base_stats = {
        'total_errors': 0, 'total_services': 0, 'affected_services': 0,
        'health_percentage': 0, 'critical_services': 0, 'avg_errors': 0,
        'top_error_service': 'N/A', 'status': 'NO_DATA'
    }
    
    if data is None or data.empty:
        logger.warning(f"No data available for stats calculation for {system_name}")
        if trends_data:
            base_stats.update({
                'error_trend': trends_data.get('error_trend', 0),
                'improvement_rate': trends_data.get('improvement_rate', 0),
                'trend_status': 'NO_DATA'
            })
        return base_stats
    
    try:
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
        
        logger.info(f"Basic stats calculated for {system_name}: {stats}")
        
        # Ajouter les données de tendance si disponibles
        if trends_data:
            stats.update({
                'error_trend': trends_data.get('error_trend', 0),
                'improvement_rate': trends_data.get('improvement_rate', 0),
                'week_trend': trends_data.get('week_trend', 0),
                'days_analyzed': trends_data.get('days_analyzed', 0),
                'trend_status': 'IMPROVING' if trends_data.get('error_trend', 0) < 0 else 'DEGRADING' if trends_data.get('error_trend', 0) > 0 else 'STABLE'
            })
            logger.info(f"Trend stats added for {system_name}")
        
        return stats
        
    except Exception as e:
        logger.error(f"Error calculating enhanced stats for {system_name}: {e}")
        logger.error(traceback.format_exc())
        return base_stats

# [Rest of the functions with similar logging enhancements...]

@log_function_call
def create_professional_system_html_with_trends(system_name, data, stats, date_str, trends_data=None):
    """Creates a professional HTML report enriched with trend analysis and explanatory text."""
    logger.info(f"Creating HTML report for {system_name}")
    # [Function implementation remains the same, just add some debug logging]
    logger.debug(f"Stats for HTML report: {stats}")
    # [Rest of the function...]

@log_function_call
def generate_daily_reports_with_trends():
    """Génère les rapports avec analyse de tendance"""
    logger.info("=" * 60)
    logger.info("GÉNÉRATION DES RAPPORTS AVEC ANALYSE DE TENDANCE")
    logger.info("=" * 60)
    
    date_str = datetime.now().strftime('%Y-%m-%d')
    systems_data = {}
    all_stats = {}
    
    systems_config = [
        ('CIS', CIS_ERROR_REPORT_OUTPUT_DIR, '🔴'),
        ('ECW', ECW_ERROR_REPORT_OUTPUT_DIR, '🟢'),
        ('IRM', IRM_ERROR_REPORT_OUTPUT_DIR, '🟡')
    ]
    
    for system_name, directory, icon in systems_config:
        logger.info(f"Processing {system_name} system from {directory}")
        
        # Données actuelles
        current_file = get_latest_csv_file(directory)
        current_data = None
        trends_data = None
        
        if current_file:
            logger.info(f"Found current file: {current_file}")
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
                        logger.info("Trend chart added to report")
                
                # Envoi du rapport
                recipients_key = f'{system_name.lower()}_recipients'
                trend_indicator = "📈" if stats.get('error_trend', 0) < 0 else "📉" if stats.get('error_trend', 0) > 0 else "➡️"
                
                email_sent = send_email_with_reports(
                    EMAIL_CONFIG['from_email'],
                    EMAIL_CONFIG[recipients_key],
                    f"{icon} {system_name} SYSTEM REPORT {trend_indicator} - {date_str}",
                    html_body,
                    charts
                )
                
                if email_sent:
                    logger.info(f"✓ {system_name} report sent successfully")
                else:
                    logger.error(f"✗ Failed to send {system_name} report")
                
                logger.info(f"   Status: {stats['status']}")
                if 'error_trend' in stats:
                    logger.info(f"   Trend: {stats['error_trend']:+d} errors ({stats['improvement_rate']:+.1f}%)")
            else:
                all_stats[system_name] = calculate_enhanced_stats(None, system_name)
                logger.warning(f"No {system_name} data found")
        else:
            all_stats[system_name] = calculate_enhanced_stats(None, system_name)
            logger.warning(f"No {system_name} file found")
    
    # Rapport de synthèse
    logger.info("Generating executive summary report")
    if all_stats:
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
        
        email_sent = send_email_with_reports(
            EMAIL_CONFIG['from_email'],
            EMAIL_CONFIG['summary_recipients'],
            f"{priority} - EXECUTIVE SUMMARY WITH TRENDS - {date_str}",
            summary_html,
            []
        )
        
        if email_sent:
            logger.info("✓ Executive summary report sent successfully")
        else:
            logger.error("✗ Failed to send executive summary report")
    
    # Résumé final
    logger.info("=" * 60)
    logger.info("RÉSUMÉ AVEC ANALYSE DE TENDANCE:")
    logger.info("=" * 60)
    
    for system, stats in all_stats.items():
        status_icon = {'HEALTHY': '✅', 'WARNING': '⚠️', 'CRITICAL': '🚨', 'NO_DATA': '⚪'}[stats.get('status', 'NO_DATA')]
        trend_icon = '📈' if stats.get('error_trend', 0) < 0 else '📉' if stats.get('error_trend', 0) > 0 else '➡️'
        logger.info(f"   {status_icon} {system}: {stats.get('total_errors', 0)} errors {trend_icon} ({stats.get('error_trend', 0):+d})")
    
    logger.info("✅ REPORTS WITH TREND ANALYSIS GENERATED!")

@log_function_call
def send_email_with_reports(from_email, to_emails, subject, html_body, chart_images, attachment_file=None):
    """Envoie un email avec les rapports et graphiques"""
    try:
        logger.info(f"Sending email with subject: {subject}")
        logger.debug(f"Recipients: {to_emails}")
        logger.debug(f"Number of charts: {len(chart_images)}")
        
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
                logger.debug(f"Added chart {i} to email")
        
        html_part = MIMEText(html_with_images, 'html')
        msg_html.attach(html_part)
        
        # Pièce jointe CSV
        if attachment_file and os.path.exists(attachment_file):
            with open(attachment_file, 'rb') as f:
                csv_attachment = MIMEApplication(f.read(), _subtype='csv')
                filename = os.path.basename(attachment_file)
                csv_attachment.add_header('Content-Disposition', f'attachment; filename="{filename}"')
                msg.attach(csv_attachment)
            logger.debug(f"Added attachment: {attachment_file}")
        
        # Envoi
        logger.info(f"Connecting to SMTP server: {EMAIL_CONFIG['smtp_server']}:{EMAIL_CONFIG['smtp_port']}")
        server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'])
        logger.info("Sending email...")
        server.sendmail(from_email, to_emails, msg.as_string())
        server.quit()
        
        logger.info(f'Email sent successfully to: {", ".join(to_emails)}')
        return True
        
    except Exception as e:
        logger.error(f'Error sending email: {e}')
        logger.error(traceback.format_exc())
        return False

def main():
    """Fonction principale avec analyse de tendance"""
    try:
        logger.info("Starting main execution")
        
        # Configuration matplotlib
        plt.style.use('default')
        sns.set_palette("husl")
        
        # Génération des rapports avec analyse de tendance
        generate_daily_reports_with_trends()
        
        logger.info("Script completed successfully")
        
    except Exception as e:
        logger.critical(f"CRITICAL ERROR: {e}")
        logger.critical(traceback.format_exc())
        logger.critical("Contact the technical team immediately!")

if __name__ == "__main__":
    main()