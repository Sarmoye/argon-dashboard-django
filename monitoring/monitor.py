import requests
import time
from datetime import datetime
import csv

def check_application_status(url, timeout=5):
    """
    Vérifie le statut d'une application via son URL
    Retourne "up" si disponible (code 200-399), "down" sinon
    """
    try:
        response = requests.get(url, timeout=timeout)
        return "up" if 200 <= response.status_code < 400 else "down"
    except (requests.RequestException, ConnectionError):
        return "down"

def save_to_csv(data, filename="/srv/itsea_files/monitoring_files/status_log.csv"):
    """
    Sauvegarde les données dans un fichier CSV
    """
    file_exists = False
    try:
        with open(filename, 'r') as f:
            file_exists = True
    except FileNotFoundError:
        pass
    
    with open(filename, 'a', newline='') as csvfile:
        fieldnames = ['timestamp', 'application', 'url', 'statut']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
        
        for entry in data:
            writer.writerow(entry)

def main():
    # Liste des URLs à vérifier (à personnaliser)
    applications = {
        "Momo Rapports": "http://momo-rapports.mtn.bj",
        "Admin Momo Rapports": "https://admin-momo-rapports.mtn.bj/",
        "Fraud report": "http://10.77.152.70:8042/auth/login",
        "Identity and Access Management": "https://iam.mtn.bj/health"
    }
    
    print(f"Début de la surveillance des applications - {datetime.now()}")
    
    while True:
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
            print(f"{app_name.ljust(15)} | {url.ljust(30)} | {status.upper()}")
        
        # Sauvegarde dans le fichier CSV
        save_to_csv(status_data)
        print(f"\nRésultats sauvegardés dans status_log.csv")

if __name__ == "__main__":
    main()