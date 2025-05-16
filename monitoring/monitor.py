import requests
import time
from datetime import datetime
import csv
import os
import shutil

def check_application_status(url, timeout=5):
    """
    Vérifie le statut d'une application via son URL
    Retourne "Online" si disponible (code 200-399), "Offline" sinon
    """
    try:
        response = requests.get(url, timeout=timeout)
        return "Online" if 200 <= response.status_code < 400 else "Offline"
    except (requests.RequestException, ConnectionError):
        return "Offline"

def backup_existing_file(filename):
    """
    Fait un backup du fichier existant avec un timestamp
    """
    if os.path.exists(filename):
        # Créer le nom du fichier backup
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base, ext = os.path.splitext(filename)
        backup_filename = f"{base}_{timestamp}{ext}"
        
        # Copier le fichier existant vers le backup
        shutil.copy2(filename, backup_filename)
        print(f"Backup créé: {backup_filename}")

def save_to_csv(data, filename="/srv/itsea_files/monitoring_files/status_log.csv"):
    """
    Sauvegarde les données dans un fichier CSV
    """
    # Vérifier et faire un backup du fichier existant
    backup_existing_file(filename)
    
    # Écrire les nouvelles données
    with open(filename, 'w', newline='') as csvfile:
        fieldnames = ['timestamp', 'application', 'url', 'statut']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for entry in data:
            writer.writerow(entry)

    return filename

def main():
    # Liste des URLs à vérifier
    applications = {
        "Momo Rapports": "https://momo-rapports.mtn.bj",
        "Admin Momo Rapports": "https://admin-momo-rapports.mtn.bj/",
        "Fraud report": "http://10.77.152.70:8042/auth/login",
        "Identity and Access Management": "https://iam.mtn.bj/health"
    }
    
    print(f"Début de la surveillance des applications - {datetime.now()}")
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"\nVérification à {timestamp}")
    print("-" * 50)
        
    status_data = []
        
    for app_name, url in applications.items():
        status = check_application_status(url)
        status_data.append({
            'timestamp': timestamp,
            'application': app_name,
            'url': url,
            'statut': status
        })
        print(f"{app_name.ljust(25)} | {url.ljust(40)} | {status.upper()}")
        
    # Sauvegarde dans le fichier CSV
    filename = save_to_csv(status_data)
    print(f"\nRésultats sauvegardés dans {filename}")

if __name__ == "__main__":
    main()