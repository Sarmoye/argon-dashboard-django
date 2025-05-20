#!/usr/bin/env python3

import requests
import time
from datetime import datetime
import csv
import os
import shutil
import logging
import argparse
import sys
import json
from concurrent.futures import ThreadPoolExecutor
from logging.handlers import RotatingFileHandler

# Configuration des constantes
DEFAULT_CSV_PATH = "/srv/itsea_files/monitoring_files/status_log.csv"
DEFAULT_LOG_PATH = "/var/log/monitoring/monitoring.log"
DEFAULT_CONFIG_PATH = "/etc/monitoring/applications.json"
DEFAULT_TIMEOUT = 5
MAX_WORKERS = 10

class ApplicationMonitor:
    """
    Classe pour surveiller le statut des applications web
    """
    def __init__(self, csv_path=DEFAULT_CSV_PATH, log_path=DEFAULT_LOG_PATH, 
                 config_path=DEFAULT_CONFIG_PATH, timeout=DEFAULT_TIMEOUT):
        self.csv_path = csv_path
        self.log_path = log_path
        self.config_path = config_path
        self.timeout = timeout
        self.applications = {}
        self.logger = None
        
        # Initialiser le logger
        self._setup_logging()
        
        # Charger la configuration des applications
        self._load_config()

    def _setup_logging(self):
        """
        Configure le système de journalisation
        """
        # Créer le dossier de logs s'il n'existe pas
        log_dir = os.path.dirname(self.log_path)
        if not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir)
            except PermissionError:
                print(f"ERREUR: Impossible de créer le dossier de logs {log_dir}. Vérifiez les permissions.")
                sys.exit(1)
        
        # Configurer le logger
        self.logger = logging.getLogger('application_monitor')
        self.logger.setLevel(logging.INFO)
        
        # Handler pour fichier avec rotation
        file_handler = RotatingFileHandler(
            self.log_path, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        
        # Handler pour la console
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Format des logs
        log_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(log_format)
        console_handler.setFormatter(log_format)
        
        # Ajouter les handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        self.logger.info("Système de journalisation initialisé avec succès")

    def _load_config(self):
        """
        Charge la configuration des applications depuis un fichier JSON
        Utilise une configuration par défaut si le fichier n'existe pas
        """
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as config_file:
                    self.applications = json.load(config_file)
                self.logger.info(f"Configuration chargée depuis {self.config_path}")
            else:
                # Configuration par défaut
                self.applications = {
                    "Momo Rapports": "https://momo-rapports.mtn.bj",
                    "Admin Momo Rapports": "https://admin-momo-rapports.mtn.bj/",
                    "Fraud report": "http://10.77.152.70:8042/auth/login",
                    "Identity and Access Management": "https://iam.mtn.bj/health"
                }
                self.logger.warning(f"Fichier de configuration {self.config_path} non trouvé. Utilisation de la configuration par défaut.")
                
                # Créer le fichier de configuration par défaut
                try:
                    config_dir = os.path.dirname(self.config_path)
                    if not os.path.exists(config_dir):
                        os.makedirs(config_dir)
                    
                    with open(self.config_path, 'w') as config_file:
                        json.dump(self.applications, config_file, indent=4)
                    self.logger.info(f"Configuration par défaut enregistrée dans {self.config_path}")
                except Exception as e:
                    self.logger.error(f"Impossible de créer le fichier de configuration par défaut: {str(e)}")
                    
        except Exception as e:
            self.logger.error(f"Erreur lors du chargement de la configuration: {str(e)}")
            sys.exit(1)

    def check_application_status(self, app_name, url):
        """
        Vérifie le statut d'une application via son URL
        Retourne un dictionnaire avec les informations de statut
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        start_time = time.time()
        
        try:
            self.logger.debug(f"Vérification de {app_name} ({url})")
            response = requests.get(url, timeout=self.timeout)
            response_time = round((time.time() - start_time) * 1000, 2)  # en ms
            
            status = "Online" if 200 <= response.status_code < 400 else "Offline"
            status_code = response.status_code
            
            self.logger.info(f"{app_name} | {url} | {status.upper()} | Code: {status_code} | Temps: {response_time}ms")
            
        except requests.exceptions.Timeout:
            status = "Offline"
            status_code = "TIMEOUT"
            response_time = None
            self.logger.warning(f"{app_name} | {url} | OFFLINE | Timeout dépassé ({self.timeout}s)")
            
        except requests.exceptions.ConnectionError:
            status = "Offline"
            status_code = "CONNECTION_ERROR"
            response_time = None
            self.logger.warning(f"{app_name} | {url} | OFFLINE | Erreur de connexion")
            
        except requests.exceptions.RequestException as e:
            status = "Offline"
            status_code = "REQUEST_ERROR"
            response_time = None
            self.logger.warning(f"{app_name} | {url} | OFFLINE | Erreur: {str(e)}")
            
        except Exception as e:
            status = "Offline"
            status_code = "UNKNOWN_ERROR"
            response_time = None
            self.logger.error(f"{app_name} | {url} | OFFLINE | Erreur inattendue: {str(e)}")
            
        return {
            'timestamp': timestamp,
            'application': app_name,
            'url': url,
            'statut': status,
            'code': status_code,
            'temps_reponse': response_time
        }

    def backup_existing_file(self, filename):
        """
        Fait un backup du fichier existant avec un timestamp
        """
        if os.path.exists(filename):
            # Créer le nom du fichier backup
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            base, ext = os.path.splitext(filename)
            backup_filename = f"{base}_{timestamp}{ext}"
            
            try:
                # Copier le fichier existant vers le backup
                shutil.copy2(filename, backup_filename)
                self.logger.info(f"Backup créé: {backup_filename}")
                return backup_filename
            except Exception as e:
                self.logger.error(f"Erreur lors de la création du backup: {str(e)}")
                return None
        return None

    def save_to_csv(self, data):
        """
        Sauvegarde les données dans un fichier CSV
        """
        # Vérifier et créer le dossier si nécessaire
        csv_dir = os.path.dirname(self.csv_path)
        if not os.path.exists(csv_dir):
            try:
                os.makedirs(csv_dir)
                self.logger.info(f"Dossier créé: {csv_dir}")
            except Exception as e:
                self.logger.error(f"Impossible de créer le dossier {csv_dir}: {str(e)}")
                return None
        
        # Vérifier et faire un backup du fichier existant
        self.backup_existing_file(self.csv_path)
        
        try:
            # Écrire les nouvelles données
            with open(self.csv_path, 'w', newline='') as csvfile:
                fieldnames = ['timestamp', 'application', 'url', 'statut', 'code', 'temps_reponse']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for entry in data:
                    writer.writerow(entry)
            
            self.logger.info(f"Résultats sauvegardés dans {self.csv_path}")
            return self.csv_path
        except Exception as e:
            self.logger.error(f"Erreur lors de l'écriture dans le fichier CSV: {str(e)}")
            return None

    def run(self):
        """
        Exécute la surveillance des applications
        """
        self.logger.info(f"Début de la surveillance des applications - {datetime.now()}")
        
        status_data = []
        
        # Utiliser un ThreadPoolExecutor pour exécuter les vérifications en parallèle
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # Créer une liste de futures
            future_to_app = {
                executor.submit(self.check_application_status, app_name, url): (app_name, url)
                for app_name, url in self.applications.items()
            }
            
            # Récupérer les résultats au fur et à mesure
            for future in future_to_app:
                try:
                    result = future.result()
                    status_data.append(result)
                except Exception as e:
                    app_name, url = future_to_app[future]
                    self.logger.error(f"Erreur lors de la vérification de {app_name} ({url}): {str(e)}")
        
        # Trier les résultats par nom d'application
        status_data.sort(key=lambda x: x['application'])
        
        # Sauvegarder dans le fichier CSV
        self.save_to_csv(status_data)
        
        # Résumé final
        online_count = sum(1 for entry in status_data if entry['statut'] == 'Online')
        offline_count = len(status_data) - online_count
        
        self.logger.info(f"Surveillance terminée. Résumé: {online_count} applications en ligne, {offline_count} hors ligne.")
        
        return status_data


def parse_arguments():
    """
    Parse les arguments de ligne de commande
    """
    parser = argparse.ArgumentParser(description='Moniteur d\'applications web')
    parser.add_argument('--csv', dest='csv_path', default=DEFAULT_CSV_PATH,
                        help=f'Chemin du fichier CSV de sortie (défaut: {DEFAULT_CSV_PATH})')
    parser.add_argument('--log', dest='log_path', default=DEFAULT_LOG_PATH,
                        help=f'Chemin du fichier de log (défaut: {DEFAULT_LOG_PATH})')
    parser.add_argument('--config', dest='config_path', default=DEFAULT_CONFIG_PATH,
                        help=f'Chemin du fichier de configuration JSON (défaut: {DEFAULT_CONFIG_PATH})')
    parser.add_argument('--timeout', dest='timeout', type=int, default=DEFAULT_TIMEOUT,
                        help=f'Timeout en secondes pour les requêtes HTTP (défaut: {DEFAULT_TIMEOUT})')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Activer le mode verbeux')
    
    return parser.parse_args()


def main():
    """
    Fonction principale
    """
    args = parse_arguments()
    
    # Ajuster le niveau de log si mode verbeux
    if args.verbose:
        logging.getLogger('application_monitor').setLevel(logging.DEBUG)
    
    # Créer et exécuter le moniteur
    monitor = ApplicationMonitor(
        csv_path=args.csv_path,
        log_path=args.log_path,
        config_path=args.config_path,
        timeout=args.timeout
    )
    
    monitor.run()


if __name__ == "__main__":
    main()