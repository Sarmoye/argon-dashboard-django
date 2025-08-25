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
import tempfile
from io import BytesIO

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
    
    'cis_recipients': [
        'Sarmoye.AmitoureHaidara@mtn.com',
    ],
    
    'irm_recipients': [
        'Sarmoye.AmitoureHaidara@mtn.com',
    ],
    
    'ecw_recipients': [
        'Sarmoye.AmitoureHaidara@mtn.com',
    ],
    
    'summary_recipients': [
        'Sarmoye.AmitoureHaidara@mtn.com',
    ]
}

# --- Helper Functions (Updated or New) ---

def get_latest_csv_file(directory):
    """Retrieves the most recent CSV file from a directory."""
    try:
        csv_files = glob.glob(os.path.join(directory, "*.csv"))
        if not csv_files:
            print(f"No CSV files found in {directory}")
            return None
        
        latest_file = max(csv_files, key=os.path.getctime)
        print(f"Latest file found: {latest_file}")
        return latest_file
    except Exception as e:
        print(f"Error while searching for file in {directory}: {e}")
        return None

def get_matching_csv_file(directory, reference_filename):
    """Retrieves a CSV file with the same name as a reference file."""
    try:
        base_name = os.path.splitext(os.path.basename(reference_filename))[0]
        matching_file = os.path.join(directory, f"{base_name}.csv")
        
        if os.path.exists(matching_file):
            print(f"Matching file found: {matching_file}")
            return matching_file
        else:
            print(f"No matching file found for {base_name} in {directory}")
            return None
    except Exception as e:
        print(f"Error while searching for the matching file: {e}")
        return None

def read_csv_data(file_path, system_name=None):
    """Reads data from a CSV file and adds appropriate headers."""
    try:
        if system_name == "CIS" or system_name == "IRM":
            expected_headers = ['Domain', 'Service Type', 'Service Name', 'Error Count', 'Error Reason']
        elif system_name == "ECW":
            expected_headers = ['Domain', 'Service Type', 'Service Name', 'Error Count']
        else:
            expected_headers = None

        skip_rows = 1 if system_name == "IRM" else 0
        
        df = pd.read_csv(file_path, header=None, names=expected_headers, skiprows=skip_rows)
        
        df.columns = df.columns.str.strip()
        
        print(f"CSV file read for {system_name}.")
        return df
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return None

def create_html_table(df, title):
    """Creates a modern, minimalist HTML table."""
    if df.empty:
        return f'<p style="text-align: center; color: #7f8c8d;">No data to display for {title}.</p>'

    html = f"""
    <div style="margin: 30px 0;">
        <h3 style="color: #1a1a1a; font-weight: 600; font-size: 18px; margin-bottom: 20px; letter-spacing: -0.5px;">{title}</h3>
        <div style="overflow-x: auto; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); border: 1px solid #e5e7eb;">
            <table style="width: 100%; border-collapse: collapse; font-family: 'Inter', sans-serif; background-color: white;">
                <thead>
                    <tr style="background-color: #f8fafc; border-bottom: 1px solid #e5e7eb;">
    """
    
    for col in df.columns:
        html += f"""
                        <th style="
                            padding: 16px 20px; 
                            text-align: left; 
                            font-weight: 600; 
                            font-size: 13px; 
                            color: #374151; 
                            text-transform: uppercase; 
                            letter-spacing: 0.5px;
                            white-space: nowrap;
                        ">{col}</th>
        """
    
    html += """
                    </tr>
                </thead>
                <tbody>
    """
    
    for i, (_, row) in enumerate(df.iterrows()):
        hover_effect = "onmouseover=\"this.style.backgroundColor='#f1f5f9'\" onmouseout=\"this.style.backgroundColor='white'\""
        html += f'<tr style="border-bottom: 1px solid #f1f5f9; transition: background-color 0.2s ease;" {hover_effect}>'
        
        for j, value in enumerate(row):
            if df.columns[j] == 'Error Count' and pd.notna(value):
                try:
                    error_count = int(float(value))
                    cell_style = f"""
                        padding: 12px 20px; 
                        font-size: 14px; 
                        color: {'#dc2626' if error_count > 0 else '#16a34a'}; 
                        font-weight: 600;
                        vertical-align: top;
                    """
                except (ValueError, TypeError):
                    cell_style = "padding: 12px 20px; font-size: 14px; color: #6b7280; vertical-align: top;"
            else:
                cell_style = "padding: 12px 20px; font-size: 14px; color: #6b7280; vertical-align: top;"
            
            display_value = value if pd.notna(value) and str(value).strip() != '' else '-'
            
            html += f'<td style="{cell_style}">{display_value}</td>'
        
        html += "</tr>"
    
    html += """
                </tbody>
            </table>
        </div>
    </div>
    """
    return html

def create_error_count_chart(df, title, system_name):
    """Creates a bar chart of errors per service."""
    try:
        plt.figure(figsize=(14, 8))
        
        if 'Service Name' not in df.columns or 'Error Count' not in df.columns:
            print(f"Missing columns for {title} chart.")
            return None
            
        grouped_data = df.groupby('Service Name')['Error Count'].sum().sort_values(ascending=False).head(15)
        
        colors = {
            'CIS': '#e74c3c',
            'IRM': '#f39c12',
            'ECW': '#27ae60'
        }
        color = colors.get(system_name, '#3498db')
        
        ax = grouped_data.plot(kind='bar', color=color, alpha=0.8, edgecolor='black', linewidth=0.5)
        plt.title(f'{title} - Top 15 Services by Error Count', fontsize=16, fontweight='bold', pad=20)
        plt.xlabel('Service Name', fontsize=14, fontweight='bold')
        plt.ylabel('Error Count', fontsize=14, fontweight='bold')
        plt.xticks(rotation=45, ha='right', fontsize=10)
        plt.yticks(fontsize=10)
        
        plt.grid(axis='y', alpha=0.3, linestyle='--')
        
        for i, v in enumerate(grouped_data.values):
            ax.text(i, v + max(grouped_data.values) * 0.01, str(int(v)),
                    ha='center', va='bottom', fontweight='bold', fontsize=9)
        
        plt.tight_layout()
        
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight', facecolor='white')
        buffer.seek(0)
        chart_data = buffer.getvalue()
        buffer.close()
        plt.close()
        
        return chart_data
    except Exception as e:
        print(f"Error creating chart for {title}: {e}")
        plt.close()
        return None

def create_summary_chart(systems_data):
    """Creates a summary bar and pie chart for all systems."""
    try:
        summary_data = {system: data['Error Count'].sum() for system, data in systems_data.items() if data is not None and not data.empty and 'Error Count' in data.columns}
        
        if not summary_data:
            return None, None
        
        systems = list(summary_data.keys())
        error_counts = list(summary_data.values())
        colors = ['#e74c3c', '#f39c12', '#27ae60']
        
        # Bar Chart
        plt.figure(figsize=(12, 8))
        plt.bar(systems, error_counts, color=colors, alpha=0.8, edgecolor='black', linewidth=1)
        plt.title('Total Error Count per System', fontsize=18, fontweight='bold', pad=20)
        plt.xlabel('Systems', fontsize=14, fontweight='bold')
        plt.ylabel('Total Error Count', fontsize=14, fontweight='bold')
        plt.grid(axis='y', alpha=0.3, linestyle='--')
        plt.tight_layout()
        
        bar_buffer = BytesIO()
        plt.savefig(bar_buffer, format='png', dpi=300, bbox_inches='tight', facecolor='white')
        bar_buffer.seek(0)
        bar_chart_data = bar_buffer.getvalue()
        plt.close()

        # Pie Chart
        plt.figure(figsize=(10, 10))
        plt.pie(error_counts, labels=systems, autopct='%1.1f%%', startangle=140, colors=colors,
                wedgeprops={'edgecolor': 'black', 'linewidth': 1})
        plt.title('Error Distribution by System', fontsize=18, fontweight='bold', pad=20)
        plt.axis('equal') # Ensures the pie chart is circular.
        plt.tight_layout()

        pie_buffer = BytesIO()
        plt.savefig(pie_buffer, format='png', dpi=300, bbox_inches='tight', facecolor='white')
        pie_buffer.seek(0)
        pie_chart_data = pie_buffer.getvalue()
        plt.close()

        return bar_chart_data, pie_chart_data

    except Exception as e:
        print(f"Error creating summary chart: {e}")
        plt.close()
        return None, None

def send_email_with_reports(from_email, to_emails, subject, html_body, chart_images, attachment_file=None):
    """Sends an email with reports, charts, and attachments."""
    try:
        msg = MIMEMultipart('related')
        msg['From'] = from_email
        msg['To'] = ', '.join(to_emails)
        msg['Subject'] = subject
        
        msg_html = MIMEMultipart('alternative')
        msg.attach(msg_html)
        
        html_with_images = html_body
        for i, chart_data in enumerate(chart_images):
            if chart_data:
                cid = f"chart{i}"
                html_with_images += f'<div style="text-align: center; margin: 20px 0;"><img src="cid:{cid}" style="max-width: 100%; height: auto; border: 1px solid #ddd; border-radius: 8px;"></div>'
                
                img = MIMEImage(chart_data)
                img.add_header('Content-ID', f'<{cid}>')
                msg.attach(img)
        
        html_part = MIMEText(html_with_images, 'html')
        msg_html.attach(html_part)
        
        if attachment_file and os.path.exists(attachment_file):
            with open(attachment_file, 'rb') as f:
                csv_attachment = MIMEApplication(f.read(), _subtype='csv')
                filename = os.path.basename(attachment_file)
                csv_attachment.add_header('Content-Disposition', f'attachment; filename="{filename}"')
                msg.attach(csv_attachment)
        
        server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'])
        server.sendmail(from_email, to_emails, msg.as_string())
        server.quit()
        
        print(f'Email sent successfully to: {", ".join(to_emails)}')
        return True
        
    except Exception as e:
        print(f'Error sending email to {", ".join(to_emails)}: {e}')
        return False

def create_system_report_html(system_name, data, date_str):
    """Creates the HTML for a specific system report."""
    html = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background-color: #f9fafb; line-height: 1.6; }}
            .container {{ max-width: 1200px; margin: 0 auto; background-color: white; border-radius: 16px; box-shadow: 0 10px 25px -3px rgba(0, 0, 0, 0.1); overflow: hidden; }}
            .header {{ text-align: center; padding: 40px 30px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }}
            .header h1 {{ margin: 0 0 10px 0; font-size: 28px; font-weight: 700; letter-spacing: -0.5px; }}
            .system-badge {{ display: inline-block; background-color: rgba(255,255,255,0.2); padding: 8px 16px; border-radius: 50px; font-size: 14px; font-weight: 500; backdrop-filter: blur(10px); }}
            .content {{ padding: 40px; }}
            .stats-container {{ background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%); border-radius: 12px; padding: 24px; margin: 30px 0; border-left: 4px solid #3b82f6; }}
            .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-top: 16px; }}
            .stat-item {{ text-align: center; padding: 16px; background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }}
            .stat-value {{ font-size: 24px; font-weight: 700; color: #1e293b; margin-bottom: 4px; }}
            .stat-label {{ font-size: 12px; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 500; }}
            .info-panel {{ margin-top: 40px; padding: 20px; background-color: #eff6ff; border-left: 4px solid #3b82f6; border-radius: 8px; }}
            .info-panel p {{ margin: 0; color: #1e40af; font-weight: 500; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Errors Report {system_name}</h1>
                <div class="system-badge">{date_str}</div>
            </div>
            <div class="content">
    """
    
    if data is not None and not data.empty:
        html += create_html_table(data, f"Errors Details - System {system_name}")
        
        if 'Error Count' in data.columns:
            data['Error Count'] = pd.to_numeric(data['Error Count'], errors='coerce').fillna(0)
            total_errors = data['Error Count'].sum()
        else:
            total_errors = 0
        
        unique_services = data['Service Name'].nunique() if 'Service Name' in data.columns else 0
        
        most_impacted_service = 'N/A'
        if 'Service Name' in data.columns and 'Error Count' in data.columns and not data.empty:
            most_impacted_service_series = data.groupby('Service Name')['Error Count'].sum().idxmax()
            most_impacted_service = most_impacted_service_series if not pd.isna(most_impacted_service_series) else 'N/A'

        html += f"""
        <div class="stats-container">
            <h4 style="color: #1e293b; margin: 0 0 16px 0; font-weight: 600;">Statistical Report</h4>
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-value" style="color: {'#dc2626' if total_errors > 0 else '#16a34a'};">{int(total_errors)}</div>
                    <div class="stat-label">Total errors</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{unique_services}</div>
                    <div class="stat-label">Relevant Services</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value" style="font-size: 16px; color: #6366f1;">{most_impacted_service}</div>
                    <div class="stat-label">Most impacted service</div>
                </div>
            </div>
        </div>
        """
    else:
        html += f"""
        <div style="text-align: center; padding: 60px 20px; color: #6b7280;">
            <div style="font-size: 48px; margin-bottom: 16px;">📊</div>
            <h3 style="color: #374151; margin-bottom: 8px;">No data available</h3>
            <p style="margin: 0;">No errors detected in the {system_name} system, or data is unavailable.</p>
        </div>
        """
    
    html += """
            <div class="info-panel">
                <p><strong>💡 Important Note :</strong> This report is automatically generated daily. For any questions or urgent issues, please contact the monitoring team.</p>
            </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html

def create_summary_report_html(systems_data, date_str):
    """Creates the HTML for the summary report with a more professional design."""
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background-color: #f5f6fa; }}
            .container {{ max-width: 1400px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 0 20px rgba(0,0,0,0.1); }}
            .header {{ text-align: center; margin-bottom: 30px; padding: 20px; background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%); color: black; border-radius: 8px; }}
            .header h1, .header p {{ margin: 0; color: white; }}
            .summary-cards {{ display: flex; gap: 20px; margin: 30px 0; flex-wrap: wrap; }}
            .card {{ flex: 1; min-width: 250px; padding: 20px; border-radius: 8px; background-color: #ffffff; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08); transition: transform 0.2s, box-shadow 0.2s; display: flex; flex-direction: column; position: relative; overflow: hidden; }}
            .card:hover {{ transform: translateY(-5px); box-shadow: 0 6px 16px rgba(0, 0, 0, 0.12); }}
            .card-status-indicator {{ position: absolute; left: 0; top: 0; bottom: 0; width: 6px; }}
            .card-error .card-status-indicator {{ background-color: #e74c3c; }}
            .card-no_error .card-status-indicator {{ background-color: #2ecc71; }}
            .card-no_data .card-status-indicator {{ background-color: #bdc3c7; }}
            .card-content {{ padding-left: 15px; }}
            .card h3 {{ margin: 0 0 5px; font-size: 1.2em; color: #34495e; }}
            .card-metric {{ margin: 10px 0; display: flex; align-items: baseline; }}
            .metric-value {{ font-size: 2.5em; font-weight: 700; color: #2c3e50; line-height: 1; }}
            .metric-label {{ font-size: 0.9em; color: #7f8c8d; margin-left: 5px; }}
            .card-description {{ margin: 0; font-size: 0.85em; color: #95a5a6; }}
            .card-status-text {{ margin-top: 15px; padding-top: 10px; border-top: 1px solid #f0f0f0; font-size: 0.85em; font-weight: 600; display: flex; align-items: center; justify-content: center; color: #2c3e50; }}
            .status-icon {{ margin-right: 5px; }}
            h2 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; margin-top: 40px; }}
            h4 {{ color: #2c3e50; margin-top: 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Summary Report - All Systems</h1>
                <p>Date: {date_str}</p>
            </div>
            
            <div class="summary-cards">
    """
    
    for system_name, data in systems_data.items():
        if data is not None and not data.empty:
            total_errors = data['Error Count'].sum() if 'Error Count' in data.columns else 0
            unique_services = data['Service Name'].nunique() if 'Service Name' in data.columns else 0
            status_info = "card-error" if total_errors > 0 else "card-no_error"
        else:
            total_errors = 0
            unique_services = 0
            status_info = "card-no_data"

        html += f"""
                <div class="card {status_info}">
                    <div class="card-status-indicator"></div>
                    <div class="card-content">
                        <h3>{system_name}</h3>
                        <div class="card-metric">
                            <span class="metric-value">{int(total_errors)}</span>
                            <span class="metric-label">total errors</span>
                        </div>
                        <p class="card-description">{unique_services} relevant services</p>
                    </div>
                </div>
        """
    
    html += """
            </div>
            
    """
    
    for system_name, data in systems_data.items():
        if data is not None and not data.empty:
            html += f"<h2 style='color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; margin-top: 40px;'>{system_name}</h2>"
            html += create_html_table(data, f"{system_name} Errors")
        else:
            html += f"<h2 style='color: #7f8c8d; margin-top: 40px;'>System {system_name}</h2>"
            html += "<p style='color: #7f8c8d; font-style: italic;'>No data available</p>"
    
    html += """
            <div style="margin-top: 40px; padding: 20px; background-color: #ecf0f1; border-radius: 8px;">
                <h4 style="color: #2c3e50; margin-top: 0;">Important Notes</h4>
                <ul style="color: #2c3e50;">
                    <li>This report consolidates data from all systems</li>
                    <li>Detailed charts are sent separately to each team</li>
                    <li>In case of emergency, contact the monitoring team</li>
                </ul>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html

def generate_daily_reports():
    """Generates and sends all daily reports."""
    print(f"Generating daily reports - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    date_str = datetime.now().strftime('%Y-%m-%d')
    systems_data = {}
    
    # Process and send CIS report
    print("\n=== Processing CIS ===")
    cis_file = get_latest_csv_file(CIS_ERROR_REPORT_OUTPUT_DIR)
    cis_data = None
    if cis_file:
        cis_data = read_csv_data(cis_file, "CIS")
        if cis_data is not None:
            systems_data['CIS'] = cis_data
            
            html_body = create_system_report_html('CIS', cis_data, date_str)
            chart = create_error_count_chart(cis_data, "CIS", "CIS")
            charts = [chart] if chart else []
            
            send_email_with_reports(
                EMAIL_CONFIG['from_email'],
                EMAIL_CONFIG['cis_recipients'],
                f"SYSTEM ERROR REPORT - CIS - {date_str}",
                html_body,
                charts
            )
    
    # Process and send ECW report
    print("\n=== Processing ECW ===")
    ecw_file = get_latest_csv_file(ECW_ERROR_REPORT_OUTPUT_DIR)
    ecw_data = None
    ecw_attachment = None
    
    if ecw_file:
        ecw_data = read_csv_data(ecw_file, "ECW")
        if ecw_data is not None:
            systems_data['ECW'] = ecw_data
            
            ecw_file2 = get_matching_csv_file(ECW_ERROR_REPORT_OUTPUT_DIR2, ecw_file)
            if ecw_file2:
                ecw_attachment = ecw_file2
            
            html_body = create_system_report_html('ECW', ecw_data, date_str)
            chart = create_error_count_chart(ecw_data, "ECW", "ECW")
            charts = [chart] if chart else []
            
            send_email_with_reports(
                EMAIL_CONFIG['from_email'],
                EMAIL_CONFIG['ecw_recipients'],
                f"SYSTEM ERROR REPORT - ECW - {date_str}",
                html_body,
                charts,
                ecw_attachment
            )

    # Process and send IRM report
    print("\n=== Processing IRM ===")
    irm_file = get_latest_csv_file(IRM_ERROR_REPORT_OUTPUT_DIR)
    irm_data = None
    if irm_file:
        irm_data = read_csv_data(irm_file, "IRM")
        if irm_data is not None:
            systems_data['IRM'] = irm_data
            
            html_body = create_system_report_html('IRM', irm_data, date_str)
            chart = create_error_count_chart(irm_data, "IRM", "IRM")
            charts = [chart] if chart else []
            
            send_email_with_reports(
                EMAIL_CONFIG['from_email'],
                EMAIL_CONFIG['irm_recipients'],
                f"SYSTEM ERROR REPORT - IRM - {date_str}",
                html_body,
                charts
            )
    
    # Summary Report
    print("\n=== Generating Summary Report ===")
    if systems_data:
        summary_html = create_summary_report_html(systems_data, date_str)
        bar_chart, pie_chart = create_summary_chart(systems_data)
        summary_charts = [bar_chart, pie_chart]
        
        send_email_with_reports(
            EMAIL_CONFIG['from_email'],
            EMAIL_CONFIG['summary_recipients'],
            f"SYSTEM ERROR REPORT - ALL SYSTEMS - {date_str}",
            summary_html,
            summary_charts
        )
    
    print("\nAll reports have been processed!")

def main():
    """Main function to run the report generation process."""
    try:
        plt.style.use('default')
        sns.set_palette("husl")
        
        generate_daily_reports()
        
    except Exception as e:
        print(f"Error in main program: {e}")

if __name__ == "__main__":
    main()