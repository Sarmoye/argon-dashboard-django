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
import tempfile
import base64
from io import BytesIO

# Configuration des répertoires
CIS_ERROR_REPORT_OUTPUT_DIR = "/srv/itsea_files/cis_error_report_files"
ECW_ERROR_REPORT_OUTPUT_DIR = "/srv/itsea_files/ecw_error_report_files"
ECW_ERROR_REPORT_OUTPUT_DIR2 = "/srv/itsea_files/ecw_error_report_files_second"
IRM_ERROR_REPORT_OUTPUT_DIR = "/srv/itsea_files/irm_error_report_files"

# Configuration email par système
EMAIL_CONFIG = {
    'smtp_server': '10.77.152.66',  # Adresse IP de votre serveur SMTP
    'smtp_port': 25,
    'from_email': 'Sarmoye.AmitoureHaidara@mtn.com',
    
    # Destinataires par système
    'cis_recipients': [
        'Sarmoye.AmitoureHaidara@mtn.com',
        'Sarmoye.AmitoureHaidara@mtn.com'
    ],
    
    'irm_recipients': [
        'Sarmoye.AmitoureHaidara@mtn.com',
        'Sarmoye.AmitoureHaidara@mtn.com'
    ],
    
    'ecw_recipients': [
        'Sarmoye.AmitoureHaidara@mtn.com',
        'Sarmoye.AmitoureHaidara@mtn.com'
    ],
    
    # Destinataires pour le rapport de synthèse
    'summary_recipients': [
        'Sarmoye.AmitoureHaidara@mtn.com',
        'Sarmoye.AmitoureHaidara@mtn.com',
        'Sarmoye.AmitoureHaidara@mtn.com'
    ]
}

def get_latest_csv_file(directory):
    """Récupère le fichier CSV le plus récent d'un répertoire"""
    try:
        csv_files = glob.glob(os.path.join(directory, "*.csv"))
        if not csv_files:
            print(f"Aucun fichier CSV trouvé dans {directory}")
            return None
        
        latest_file = max(csv_files, key=os.path.getctime)
        print(f"Fichier le plus récent trouvé: {latest_file}")
        return latest_file
    except Exception as e:
        print(f"Erreur lors de la recherche du fichier dans {directory}: {e}")
        return None

def get_matching_csv_file(directory, reference_filename):
    """Récupère un fichier CSV avec le même nom qu'un fichier de référence"""
    try:
        base_name = os.path.splitext(os.path.basename(reference_filename))[0]
        matching_file = os.path.join(directory, f"{base_name}.csv")
        
        if os.path.exists(matching_file):
            print(f"Fichier correspondant trouvé: {matching_file}")
            return matching_file
        else:
            print(f"Aucun fichier correspondant trouvé pour {base_name} dans {directory}")
            return None
    except Exception as e:
        print(f"Erreur lors de la recherche du fichier correspondant: {e}")
        return None

def read_csv_data(file_path):
    """Lit les données d'un fichier CSV"""
    try:
        df = pd.read_csv(file_path)
        # Nettoyer les en-têtes (supprimer les espaces)
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        print(f"Erreur lors de la lecture du fichier {file_path}: {e}")
        return None

def create_html_table(df, title):
    """Crée un tableau HTML à partir d'un DataFrame"""
    html = f"""
    <h3 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;">{title}</h3>
    <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; font-family: Arial, sans-serif; width: 100%; margin-bottom: 20px;">
        <thead style="background-color: #3498db; color: white;">
    """
    
    # En-têtes
    html += "<tr>"
    for col in df.columns:
        html += f"<th style='text-align: left; padding: 12px; font-weight: bold;'>{col}</th>"
    html += "</tr></thead><tbody>"
    
    # Données avec alternance de couleurs
    for i, (_, row) in enumerate(df.iterrows()):
        bg_color = "#f8f9fa" if i % 2 == 0 else "#ffffff"
        html += f"<tr style='background-color: {bg_color};'>"
        for value in row:
            html += f"<td style='padding: 10px; border-bottom: 1px solid #dee2e6;'>{value}</td>"
        html += "</tr>"
    
    html += "</tbody></table>"
    return html

def create_error_count_chart(df, title, system_name):
    """Crée un graphique des erreurs par service"""
    try:
        plt.figure(figsize=(14, 8))
        
        # Grouper par Service Name et sommer Error Count
        if 'Service Name' in df.columns and 'Error Count' in df.columns:
            grouped_data = df.groupby('Service Name')['Error Count'].sum().sort_values(ascending=False)
            
            # Limiter à 15 services pour la lisibilité
            if len(grouped_data) > 15:
                grouped_data = grouped_data.head(15)
        else:
            print(f"Colonnes manquantes pour {title}")
            return None
        
        # Définir les couleurs par système
        colors = {
            'CIS': '#e74c3c',
            'IRM': '#f39c12', 
            'ECW': '#27ae60'
        }
        color = colors.get(system_name, '#3498db')
        
        # Créer le graphique
        ax = grouped_data.plot(kind='bar', color=color, alpha=0.8, edgecolor='black', linewidth=0.5)
        plt.title(f'{title} - Error Count per Service Name', fontsize=16, fontweight='bold', pad=20)
        plt.xlabel('Service Name', fontsize=14, fontweight='bold')
        plt.ylabel('Error Count', fontsize=14, fontweight='bold')
        plt.xticks(rotation=45, ha='right', fontsize=10)
        plt.yticks(fontsize=10)
        
        # Ajouter une grille pour la lisibilité
        plt.grid(axis='y', alpha=0.3, linestyle='--')
        
        # Ajouter les valeurs sur les barres
        for i, v in enumerate(grouped_data.values):
            ax.text(i, v + max(grouped_data.values) * 0.01, str(int(v)), 
                   ha='center', va='bottom', fontweight='bold', fontsize=9)
        
        plt.tight_layout()
        
        # Sauvegarder en base64 pour l'email
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight', facecolor='white')
        buffer.seek(0)
        chart_data = buffer.getvalue()
        buffer.close()
        plt.close()
        
        return chart_data
    except Exception as e:
        print(f"Erreur lors de la création du graphique pour {title}: {e}")
        plt.close()
        return None

def create_summary_chart(systems_data):
    """Crée un graphique de synthèse pour tous les systèmes"""
    try:
        plt.figure(figsize=(16, 10))
        
        # Préparer les données pour le graphique de synthèse
        summary_data = {}
        colors = {'CIS': '#e74c3c', 'IRM': '#f39c12', 'ECW': '#27ae60'}
        
        for system_name, data in systems_data.items():
            if data is not None and not data.empty:
                if 'Service Name' in data.columns and 'Error Count' in data.columns:
                    total_errors = data['Error Count'].sum()
                    summary_data[system_name] = total_errors
        
        if not summary_data:
            return None
        
        # Créer le graphique en barres
        systems = list(summary_data.keys())
        error_counts = list(summary_data.values())
        bar_colors = [colors.get(system, '#3498db') for system in systems]
        
        bars = plt.bar(systems, error_counts, color=bar_colors, alpha=0.8, edgecolor='black', linewidth=1)
        
        plt.title('Error Count Summary - All Systems', fontsize=18, fontweight='bold', pad=20)
        plt.xlabel('Systems', fontsize=14, fontweight='bold')
        plt.ylabel('Total Error Count', fontsize=14, fontweight='bold')
        plt.grid(axis='y', alpha=0.3, linestyle='--')
        
        # Ajouter les valeurs sur les barres
        for bar, count in zip(bars, error_counts):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(error_counts) * 0.01,
                    str(int(count)), ha='center', va='bottom', fontweight='bold', fontsize=12)
        
        plt.tight_layout()
        
        # Sauvegarder
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight', facecolor='white')
        buffer.seek(0)
        chart_data = buffer.getvalue()
        buffer.close()
        plt.close()
        
        return chart_data
    except Exception as e:
        print(f"Erreur lors de la création du graphique de synthèse: {e}")
        plt.close()
        return None

def send_email_with_reports(from_email, to_emails, subject, html_body, chart_images, attachment_file=None):
    """Envoie un email avec les rapports, graphiques et pièces jointes"""
    try:
        msg = MIMEMultipart('related')
        msg['From'] = from_email
        msg['To'] = ', '.join(to_emails)
        msg['Subject'] = subject
        
        # Corps du message HTML
        msg_html = MIMEMultipart('alternative')
        msg.attach(msg_html)
        
        # Ajouter les images des graphiques au HTML
        html_with_images = html_body
        for i, chart_data in enumerate(chart_images):
            if chart_data:
                cid = f"chart{i}"
                html_with_images += f'<div style="text-align: center; margin: 20px 0;"><img src="cid:{cid}" style="max-width: 100%; height: auto; border: 1px solid #ddd; border-radius: 8px;"></div>'
                
                # Attacher l'image
                img = MIMEImage(chart_data)
                img.add_header('Content-ID', f'<{cid}>')
                msg.attach(img)
        
        html_part = MIMEText(html_with_images, 'html')
        msg_html.attach(html_part)
        
        # Attacher le fichier CSV si fourni
        if attachment_file and os.path.exists(attachment_file):
            with open(attachment_file, 'rb') as f:
                csv_attachment = MIMEApplication(f.read(), _subtype='csv')
                filename = os.path.basename(attachment_file)
                csv_attachment.add_header('Content-Disposition', f'attachment; filename="{filename}"')
                msg.attach(csv_attachment)
        
        # Envoyer l'email
        server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'])
        server.sendmail(from_email, to_emails, msg.as_string())
        server.quit()
        
        print(f'E-mail envoyé avec succès à: {", ".join(to_emails)}')
        return True
        
    except Exception as e:
        print(f'Erreur lors de l\'envoi de l\'e-mail à {", ".join(to_emails)}: {e}')
        return False

def create_system_report_html(system_name, data, date_str):
    """Crée le HTML pour un rapport de système spécifique"""
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background-color: #f5f6fa; }}
            .container {{ max-width: 1200px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 0 20px rgba(0,0,0,0.1); }}
            .header {{ text-align: center; margin-bottom: 30px; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 8px; }}
            .system-badge {{ display: inline-block; background-color: rgba(255,255,255,0.2); padding: 5px 15px; border-radius: 20px; font-size: 14px; margin-top: 10px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Rapport d'erreurs {system_name}</h1>
                <div class="system-badge">Date: {date_str}</div>
            </div>
    """
    
    if data is not None and not data.empty:
        html += create_html_table(data, f"Détail des erreurs - Système {system_name}")
        
        # Statistiques rapides
        total_errors = data['Error Count'].sum() if 'Error Count' in data.columns else 0
        unique_services = data['Service Name'].nunique() if 'Service Name' in data.columns else 0
        
        html += f"""
        <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h4 style="color: #2c3e50; margin-top: 0;">Résumé statistique</h4>
            <div style="display: flex; gap: 30px;">
                <div><strong>Total des erreurs:</strong> {total_errors}</div>
                <div><strong>Services concernés:</strong> {unique_services}</div>
                <div><strong>Dernière mise à jour:</strong> {date_str}</div>
            </div>
        </div>
        """
    else:
        html += f"<p style='text-align: center; color: #7f8c8d; font-size: 16px;'>Aucune donnée disponible pour le système {system_name}</p>"
    
    html += """
        <div style="margin-top: 30px; padding: 15px; background-color: #e8f4f8; border-left: 4px solid #3498db; border-radius: 4px;">
            <p style="margin: 0; color: #2c3e50;"><strong>Note:</strong> Ce rapport est généré automatiquement. Pour toute question, contactez l'équipe de monitoring.</p>
        </div>
        </div>
    </body>
    </html>
    """
    
    return html

def create_summary_report_html(systems_data, date_str):
    """Crée le HTML pour le rapport de synthèse"""
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background-color: #f5f6fa; }}
            .container {{ max-width: 1400px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 0 20px rgba(0,0,0,0.1); }}
            .header {{ text-align: center; margin-bottom: 30px; padding: 20px; background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%); color: white; border-radius: 8px; }}
            .summary-cards {{ display: flex; gap: 20px; margin: 30px 0; flex-wrap: wrap; }}
            .card {{ flex: 1; min-width: 250px; padding: 20px; border-radius: 8px; text-align: center; color: white; }}
            .card-cis {{ background: linear-gradient(135deg, #e74c3c, #c0392b); }}
            .card-irm {{ background: linear-gradient(135deg, #f39c12, #e67e22); }}
            .card-ecw {{ background: linear-gradient(135deg, #27ae60, #229954); }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Rapport de Synthèse - Tous les Systèmes</h1>
                <p>Date: {date_str}</p>
            </div>
            
            <div class="summary-cards">
    """
    
    # Cartes de résumé par système
    for system_name, data in systems_data.items():
        card_class = f"card-{system_name.lower()}"
        if data is not None and not data.empty:
            total_errors = data['Error Count'].sum() if 'Error Count' in data.columns else 0
            unique_services = data['Service Name'].nunique() if 'Service Name' in data.columns else 0
            status = "🔴 Erreurs détectées" if total_errors > 0 else "✅ Aucune erreur"
        else:
            total_errors = 0
            unique_services = 0
            status = "⚪ Pas de données"
        
        html += f"""
                <div class="card {card_class}">
                    <h3>{system_name}</h3>
                    <div style="font-size: 24px; font-weight: bold; margin: 10px 0;">{total_errors}</div>
                    <div>erreurs totales</div>
                    <div style="margin-top: 10px; font-size: 14px;">{unique_services} services concernés</div>
                    <div style="margin-top: 5px; font-size: 12px;">{status}</div>
                </div>
        """
    
    html += """
            </div>
    """
    
    # Tableaux détaillés pour chaque système
    for system_name, data in systems_data.items():
        if data is not None and not data.empty:
            html += f"<h2 style='color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; margin-top: 40px;'>Détail {system_name}</h2>"
            html += create_html_table(data, f"Erreurs {system_name}")
        else:
            html += f"<h2 style='color: #7f8c8d; margin-top: 40px;'>Système {system_name}</h2>"
            html += "<p style='color: #7f8c8d; font-style: italic;'>Aucune donnée disponible</p>"
    
    html += """
            <div style="margin-top: 40px; padding: 20px; background-color: #ecf0f1; border-radius: 8px;">
                <h4 style="color: #2c3e50; margin-top: 0;">Informations importantes</h4>
                <ul style="color: #2c3e50;">
                    <li>Ce rapport consolide les données de tous les systèmes</li>
                    <li>Les graphiques détaillés sont envoyés séparément à chaque équipe</li>
                    <li>En cas d'urgence, contactez l'équipe de monitoring</li>
                </ul>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html

def generate_daily_reports():
    """Génère et envoie tous les rapports quotidiens"""
    print(f"Génération des rapports quotidiens - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    date_str = datetime.now().strftime('%Y-%m-%d')
    systems_data = {}
    
    # 1. Traitement et envoi CIS
    print("\n=== Traitement CIS ===")
    cis_file = get_latest_csv_file(CIS_ERROR_REPORT_OUTPUT_DIR)
    cis_data = None
    if cis_file:
        cis_data = read_csv_data(cis_file)
        if cis_data is not None:
            systems_data['CIS'] = cis_data
            
            # Créer et envoyer le rapport CIS
            html_body = create_system_report_html('CIS', cis_data, date_str)
            chart = create_error_count_chart(cis_data, "CIS", "CIS")
            charts = [chart] if chart else []
            
            send_email_with_reports(
                EMAIL_CONFIG['from_email'],
                EMAIL_CONFIG['cis_recipients'],
                f"Rapport CIS - {date_str}",
                html_body,
                charts
            )
    
    # 2. Traitement et envoi IRM
    print("\n=== Traitement IRM ===")
    irm_file = get_latest_csv_file(IRM_ERROR_REPORT_OUTPUT_DIR)
    irm_data = None
    if irm_file:
        irm_data = read_csv_data(irm_file)
        if irm_data is not None:
            systems_data['IRM'] = irm_data
            
            # Créer et envoyer le rapport IRM
            html_body = create_system_report_html('IRM', irm_data, date_str)
            chart = create_error_count_chart(irm_data, "IRM", "IRM")
            charts = [chart] if chart else []
            
            send_email_with_reports(
                EMAIL_CONFIG['from_email'],
                EMAIL_CONFIG['irm_recipients'],
                f"Rapport IRM - {date_str}",
                html_body,
                charts
            )
    
    # 3. Traitement et envoi ECW
    print("\n=== Traitement ECW ===")
    ecw_file = get_latest_csv_file(ECW_ERROR_REPORT_OUTPUT_DIR)
    ecw_data = None
    ecw_attachment = None
    
    if ecw_file:
        ecw_data = read_csv_data(ecw_file)
        if ecw_data is not None:
            systems_data['ECW'] = ecw_data
            
            # Récupérer le fichier correspondant pour la pièce jointe
            ecw_file2 = get_matching_csv_file(ECW_ERROR_REPORT_OUTPUT_DIR2, ecw_file)
            if ecw_file2:
                ecw_attachment = ecw_file2
            
            # Créer et envoyer le rapport ECW
            html_body = create_system_report_html('ECW', ecw_data, date_str)
            chart = create_error_count_chart(ecw_data, "ECW", "ECW")
            charts = [chart] if chart else []
            
            send_email_with_reports(
                EMAIL_CONFIG['from_email'],
                EMAIL_CONFIG['ecw_recipients'],
                f"Rapport ECW - {date_str}",
                html_body,
                charts,
                ecw_attachment
            )
    
    # 4. Rapport de synthèse
    print("\n=== Génération du rapport de synthèse ===")
    if systems_data:
        summary_html = create_summary_report_html(systems_data, date_str)
        summary_chart = create_summary_chart(systems_data)
        summary_charts = [summary_chart] if summary_chart else []
        
        send_email_with_reports(
            EMAIL_CONFIG['from_email'],
            EMAIL_CONFIG['summary_recipients'],
            f"Rapport de Synthèse - Tous les Systèmes - {date_str}",
            summary_html,
            summary_charts
        )
    
    print("\nTous les rapports ont été traités!")

def main():
    """Fonction principale"""
    try:
        # Configurer matplotlib pour éviter les problèmes d'affichage
        plt.style.use('default')
        sns.set_palette("husl")
        
        # Générer tous les rapports
        generate_daily_reports()
        
    except Exception as e:
        print(f"Erreur dans le programme principal: {e}")

if __name__ == "__main__":
    main()