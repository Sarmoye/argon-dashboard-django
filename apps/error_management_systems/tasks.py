# apps/error_management_systems/tasks.py

import os
import subprocess
from datetime import datetime
from celery import shared_task, Task
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

@shared_task(
    bind=True,
    base=Task,
    max_retries=3,
    default_retry_delay=60,
    queue='queue_execute_cis_error_report',
    name='apps.error_management_systems.tasks.task_execute_cis_error_report'
)
def task_execute_cis_error_report(self):
    """
    Génère un rapport d'erreurs CIS quotidien via Presto
    et écrit un CSV dans le répertoire défini en settings.
    """

    try:
        # --- 1. Préparer le répertoire de sortie et les paramètres Presto
        output_dir = settings.CIS_ERROR_REPORT_OUTPUT_DIR
        os.makedirs(output_dir, exist_ok=True)

        presto_cfg = {
            "PRESTO_SERVER": settings.PRESTO_SERVER,
            "PRESTO_PORT": settings.PRESTO_PORT,
            "PRESTO_CATALOG": settings.PRESTO_CATALOG,
            "PRESTO_SCHEMA": settings.PRESTO_SCHEMA,
            "PRESTO_USER": settings.PRESTO_USER,
            "PRESTO_PASSWORD": settings.PRESTO_PASSWORD,
            "PRESTO_KEYSTORE_PATH": settings.PRESTO_KEYSTORE_PATH,
            "PRESTO_KEYSTORE_PASSWORD": settings.PRESTO_KEYSTORE_PASSWORD,
        }

        # --- 2. Construire la requête
        today_str = datetime.now().strftime("%Y%m%d")
        query = f"""
        SELECT 
            'CIS' as Domain,
            sptype as "Service Type",
            producttype as "Service Name", 
            COUNT(*) AS "Error Count", 
            reason as "Error Reason"
        FROM hive.feeds.cis
        WHERE tbl_dt = {today_str}
          AND upper(success_failure) LIKE '%FAIL%'
        GROUP BY producttype, reason, sptype
        ORDER BY "Error Count" DESC
        """

        # --- 3. Fichier de sortie
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(output_dir, f"cis_error_report_{timestamp}.csv")
        logger.info("Génération du rapport CIS vers: %s", output_file)

        # --- 4. Préparer la commande Presto CLI
        presto_cli = settings.PRESTO_CLI_PATH
        cmd = [
            presto_cli,
            f"--server={presto_cfg['PRESTO_SERVER']}:{presto_cfg['PRESTO_PORT']}",
            f"--catalog={presto_cfg['PRESTO_CATALOG']}",
            f"--schema={presto_cfg['PRESTO_SCHEMA']}",
            f"--user={presto_cfg['PRESTO_USER']}",
            f"--keystore-path={presto_cfg['PRESTO_KEYSTORE_PATH']}",
            f"--keystore-password={presto_cfg['PRESTO_KEYSTORE_PASSWORD']}",
            "--password",
            "--output-format=CSV",
            "--execute", query
        ]

        # Éviter de logger le mot de passe en clair
        safe_cmd = " ".join(cmd).replace(presto_cfg['PRESTO_KEYSTORE_PASSWORD'], "********")
        logger.debug("Commande Presto CLI: %s", safe_cmd)

        # Injecter le password dans l'environnement
        env = os.environ.copy()
        env["PRESTO_PASSWORD"] = presto_cfg['PRESTO_PASSWORD']

        # Exécution
        with open(output_file, "w") as f_out:
            proc = subprocess.run(
                cmd,
                stdout=f_out,
                stderr=subprocess.PIPE,
                env=env,
                text=True
            )

        if proc.returncode != 0:
            err = proc.stderr.strip()
            logger.error("Presto CLI error: %s", err)
            return {"status": "error", "message": err}

        logger.info("Rapport CIS généré avec succès: %s", output_file)
        return {"status": "success", "output_file": output_file}

    except Exception as exc:
        logger.exception("Exception dans task_execute_cis_error_report")
        # retry si nécessaire
        raise self.retry(exc=exc)


import os
import glob
import csv
import urllib.parse
from datetime import datetime
from celery import shared_task
from django.conf import settings
import logging
import requests
import json

logger = logging.getLogger(__name__)

HEADERS = ['Domain', 'Service Type', 'Service Name', 'Error Count', 'Error Reason']

@shared_task(
    bind=True,
    queue='queue_process_cis_error_report',  # ou autre queue dédiée
    name='apps.error_management_systems.tasks.process_cis_error_report'
)
def process_cis_error_report(self):
    """
    1) Lit le CSV CIS du jour
    2) Obtient un token auprès de l'API interne
    3) Envoie en batch les événements vers create_event_api
    """
    # Configuration de l'API
    BASE_URL = "http://ems.mtn.bj"
    USER = "celery_user_report"
    PASS = "samitoure@!1&112024sadmin"
    
    # Log des informations de configuration (sans le mot de passe complet)
    logger.info(f"Utilisation de l'API sur: {BASE_URL}")
    logger.info(f"Utilisateur API: {USER}")

    # --- 1) Lecture du CSV ---
    output_dir = settings.CIS_ERROR_REPORT_OUTPUT_DIR
    today_str = datetime.now().strftime('%Y%m%d')
    pattern = os.path.join(output_dir, f'cis_error_report_{today_str}_*.csv')
    files = glob.glob(pattern)
    if not files:
        logger.info(f"Aucun rapport CIS pour le {today_str}")
        return {"status": "no_file"}

    latest_file = max(files)
    logger.info(f"Fichier à traiter : {latest_file} (taille {os.path.getsize(latest_file)} octets)")
    
    try:
        with open(latest_file, newline='', encoding='utf-8-sig') as csvfile:
            reader = csv.reader(csvfile)
            rows = list(reader)
    except Exception as e:
        logger.error(f"Erreur lors de la lecture du fichier CSV: {str(e)}")
        return {"status": "error", "msg": "file_read_error", "detail": str(e)}

    if not rows:
        logger.warning("Le CSV est vide après lecture.")
        return {"status": "empty_file"}

    # --- 2) Récupération du token ---
    token_url = f"{BASE_URL}/errors/api/token/"
    
    # Vérifier la disponibilité du serveur d'API
    try:
        health_check = requests.get(f"{BASE_URL}/", timeout=5)
        logger.info(f"API disponible, code: {health_check.status_code}")
    except Exception as e:
        logger.warning(f"Vérification de disponibilité API échouée: {str(e)}")
    
    # Utiliser uniquement la méthode POST avec JSON comme spécifié dans l'API
    logger.info("Tentative d'authentification avec méthode POST (JSON)")
    token = None
    try:
        # Préparer les données d'authentification au format JSON
        auth_data = {
            "username": USER,
            "password": PASS
        }
        
        # Ajouter les headers appropriés
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Exécuter la requête POST
        logger.info(f"Envoi de la requête d'authentification à {token_url}")
        resp = requests.post(
            token_url,
            json=auth_data,  # Utiliser json= pour encoder automatiquement en JSON
            headers=headers,
            timeout=10
        )
        
        # Log détaillé de la réponse
        logger.info(f"Status: {resp.status_code}")
        logger.info(f"Headers: {dict(resp.headers)}")
        logger.info(f"Réponse: {resp.text[:100]}")
        
        # Tenter de parser la réponse
        if resp.status_code < 400:  # Si la réponse est OK
            try:
                token_data = resp.json()
                logger.info(f"Réponse JSON reçue: {token_data}")
                
                if "access" in token_data:
                    token = token_data["access"]
                    logger.info("Token obtenu avec succès")
                else:
                    logger.error(f"Format de réponse valide mais sans token: {resp.text}")
            except Exception as json_exc:
                logger.error(f"Impossible de parser la réponse JSON: {str(json_exc)}")
        else:
            logger.error(f"Erreur d'authentification: {resp.status_code} {resp.reason}: {resp.text}")
    except Exception as exc:
        logger.exception(f"Exception lors de l'authentification: {str(exc)}")

    
    token = None
    auth_errors = []
    
    if token is None:
        logger.error("Impossible d'obtenir un token d'authentification")
        
        # Vérifier l'existence de settings spécifiques
        try:
            from django.conf import settings as django_settings
            if hasattr(django_settings, 'EMS_AUTH_CONFIG'):
                config_file = django_settings.EMS_AUTH_CONFIG
                if os.path.exists(config_file):
                    with open(config_file, 'r') as f:
                        config = json.load(f)
                    logger.info("Configuration alternative trouvée")
        except Exception as config_exc:
            logger.error(f"Erreur lors de la lecture de configuration alternative: {str(config_exc)}")
        
        # Vérifier si l'API est bien démarrée
        try:
            health_resp = requests.get(f"{BASE_URL}/errors/api/health/", timeout=5)
            logger.info(f"API health check: {health_resp.status_code} - {health_resp.text[:100]}")
        except Exception as health_exc:
            logger.error(f"API health check failed: {str(health_exc)}")
        
        return {"status": "error", "msg": "token_error", "detail": "Échec de l'authentification avec la méthode GET"}

    # --- 3) Préparation du payload ---
    try:
        def map_csv_to_event_dict(csv_row):
            # Validation des données
            try:
                error_count = int(csv_row[3]) if csv_row[3].isdigit() else csv_row[3]
            except (IndexError, ValueError):
                error_count = 0
                
            return {
                "system_name": csv_row[0] if len(csv_row) > 0 else "Unknown",
                "service_name": csv_row[1] if len(csv_row) > 1 else "Unknown",
                "error_category_name": csv_row[2] if len(csv_row) > 2 else "Unknown",
                "error_count": error_count,
                "error_description": csv_row[4] if len(csv_row) > 4 else "",
            }

        payload = [map_csv_to_event_dict(r) for r in rows]
        
    except Exception as e:
        logger.error(f"Erreur lors de la préparation du payload: {str(e)}")
        return {"status": "error", "msg": "payload_error", "detail": str(e)}

    # --- 4) Envoi en batch ---
    api_url = f"{BASE_URL}/errors/api/create-event/"
    headers = {
        "Authorization": f"Token {token}", 
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    try:
        logger.info(f"Envoi du payload au endpoint {api_url}")
        logger.info(f"Nombre d'événements à envoyer: {len(payload)}")
        
        resp = requests.post(api_url, json=payload, headers=headers, timeout=30)
        
        # Log de la réponse pour debug
        logger.info(f"Réponse API (code {resp.status_code}): {resp.text[:200]}...")
        
        resp.raise_for_status()
        logger.info("Envoi des événements réussi.")
        return {"status": "success", "response": resp.json()}
    except Exception as exc:
        logger.exception(f"Erreur lors de l'envoi des événements: {str(exc)}")
        # On peut stocker les données non envoyées pour réessayer plus tard
        try:
            backup_file = os.path.join(
                output_dir, 
                f"failed_payload_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            with open(backup_file, 'w') as f:
                json.dump(payload, f)
            logger.info(f"Sauvegarde du payload dans {backup_file}")
        except Exception as save_exc:
            logger.error(f"Impossible de sauvegarder le payload: {str(save_exc)}")
        
        # Si échec, on peut relancer la tâche
        raise self.retry(exc=exc, countdown=60, max_retries=3)