# apps/error_management_systems/tasks.py

import os
import subprocess
from datetime import datetime, timedelta
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
        now = datetime.now()
        now_str       = now.strftime("%Y%m%d%H%M%S")
        threshold_str = (now - timedelta(minutes=30)).strftime("%Y%m%d%H%M%S")
        today_str     = now.strftime("%Y%m%d")

        query = f"""
        WITH parsed AS (
          SELECT
            sptype,
            producttype,
            reason,
            success_failure,
            CASE
              WHEN regexp_replace(starttime, '[^0-9]', '') = '' THEN NULL
              ELSE CAST(substr(regexp_replace(starttime, '[^0-9]', ''), 1, 14) AS BIGINT)
            END AS start_num,
            CASE
              WHEN regexp_replace(endtime, '[^0-9]', '') = '' THEN NULL
              ELSE CAST(substr(regexp_replace(endtime,   '[^0-9]', ''), 1, 14) AS BIGINT)
            END AS end_num
          FROM hive.feeds.cis
          WHERE tbl_dt = {today_str}
        )
        SELECT
          'CIS'            AS Domain,
          sptype           AS "Service Type",
          producttype      AS "Service Name",
          COUNT(*)         AS "Error Count",
          reason           AS "Error Reason"
        FROM parsed
        WHERE
          start_num IS NOT NULL
          AND (end_num   >= {threshold_str} OR end_num IS NULL) -- Inclure les cas où end_num est NULL
          AND start_num <= {now_str}
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
    4) Renomme le fichier traité avec le préfixe OK_
    """
    # Configuration de l'API
    BASE_URL = "http://ems.mtn.bj"
    USER = "celery_user_report"
    PASS = "samiure@!1&112024sadmin" 
    
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
                "service_name": csv_row[2] if len(csv_row) > 1 else "Unknown",
                "error_category_name": csv_row[1] if len(csv_row) > 2 else "Unknown",
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
        "Authorization": f"Bearer {token}", 
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
        
        # --- 5) Renommer le fichier traité avec préfixe OK_ ---
        file_name = os.path.basename(latest_file)
        new_file_name = f"OK_{file_name}"
        new_file_path = os.path.join(output_dir, new_file_name)
        
        try:
            os.rename(latest_file, new_file_path)
            logger.info(f"Fichier renommé avec succès: {new_file_path}")
        except Exception as rename_exc:
            logger.error(f"Impossible de renommer le fichier: {str(rename_exc)}")
        
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
        

@shared_task(
    bind=True,
    base=Task,
    max_retries=3,
    default_retry_delay=60,
    queue='queue_execute_ecw_error_report',
    name='apps.error_management_systems.tasks.task_execute_ecw_error_report'
)
def task_execute_ecw_error_report(self):
    """
    Génère un rapport d'erreurs ECW quotidien via Presto
    et écrit un ECW dans le répertoire défini en settings.
    """

    try:
        # --- 1. Préparer le répertoire de sortie et les paramètres Presto
        output_dir = settings.ECW_ERROR_REPORT_OUTPUT_DIR
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
        now = datetime.now()
        now_str = now.strftime("%Y%m%d%H%M%S")
        threshold_dt = now - timedelta(minutes=30)
        threshold_str = threshold_dt.strftime("%Y%m%d%H%M%S")

        now_formatted = now.strftime("%Y-%m-%d %H:%M:%S")
        threshold_formatted = threshold_dt.strftime("%Y-%m-%d %H:%M:%S")
        today_str     = now.strftime("%Y%m%d")

        query = f"""
        WITH failed_in AS (
            SELECT 
                transactionid,
                messages AS failed_in_message, -- Message d'erreur IN
                logdate
            FROM hive.feeds.service_provider_log
            WHERE tbl_dt = {today_str}
            AND UPPER(messages) LIKE '%FAIL%'
            AND direction = 'IN'
        ),
        failed_out AS (
            SELECT 
                transactionid,
                messages AS failed_out_message, -- Message OUT (tous les messages OUT, sans filtre sur FAIL)
                logdate
            FROM hive.feeds.service_provider_log
            WHERE tbl_dt = {today_str}
            AND direction = 'OUT'
        ),
        aggregated_data AS (
            SELECT 
                fi.transactionid,
                fi.failed_in_message,
                fo.failed_out_message,
                regexp_extract(lo.message_receivingfri, '@(.*?)/', 1) AS receiving_fri_component,
                COUNT(*) AS error_count,
                fi.logdate AS logdate
            FROM hive.feeds.service_provider_log lo
            JOIN failed_in fi 
            ON lo.transactionid = fi.transactionid
            LEFT JOIN failed_out fo 
            ON lo.transactionid = fo.transactionid
            WHERE lo.tbl_dt = {today_str}
            AND lo.direction = 'OUT'
            AND lo.message_receivingfri LIKE '%.sp/SP%'
            AND fi.logdate BETWEEN TIMESTAMP '{threshold_formatted}' AND TIMESTAMP '{now_formatted}'
            GROUP BY 
                fi.transactionid,
                fi.failed_in_message, 
                fo.failed_out_message,
                regexp_extract(lo.message_receivingfri, '@(.*?)/', 1),
                fi.logdate
        )
        SELECT
            'ECW' AS domain,
            'ECW SP' AS Service_Type,
            transactionid,
            receiving_fri_component AS Service_Name,
            error_count AS messages_count,
            failed_in_message AS failed_in_messages,
            failed_out_message AS failed_out_messages,
            logdate
        FROM aggregated_data
        ORDER BY error_count DESC;
        """

        # --- 3. Fichier de sortie
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(output_dir, f"ecw_error_report_{timestamp}.csv")
        logger.info("Génération du rapport ECW vers: %s", output_file)

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

        logger.info("Rapport ECW généré avec succès: %s", output_file)
        return {"status": "success", "output_file": output_file}

    except Exception as exc:
        logger.exception("Exception dans task_execute_ecw_error_report")
        # retry si nécessaire
        raise self.retry(exc=exc)
    
@shared_task(
    bind=True,
    queue='queue_process_ecw_error_report',  # ou autre queue dédiée
    name='apps.error_management_systems.tasks.process_ecw_error_report'
)
def process_ecw_error_report(self):
    """
    1) Lit le CSV ECW du jour
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
    output_dir = settings.ECW_ERROR_REPORT_OUTPUT_DIR
    today_str = datetime.now().strftime('%Y%m%d')
    pattern = os.path.join(output_dir, f'ecw_error_report_{today_str}_*.csv')
    files = glob.glob(pattern)
    if not files:
        logger.info(f"Aucun rapport ECW pour le {today_str}")
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

    # --- 3) Préparation du payload ---
    try:
        def map_csv_to_event_dict(csv_row):
            # Validation des données
            try:
                error_count = int(csv_row[4]) if csv_row[4].isdigit() else csv_row[4]
            except (IndexError, ValueError):
                error_count = 0
                
            return {
                "system_name": csv_row[0] if len(csv_row) > 0 else "Unknown",
                "service_name": csv_row[3] if len(csv_row) > 3 else "Unknown",
                "error_category_name": csv_row[1] if len(csv_row) > 1 else "Unknown",
                "error_count": error_count,
                "error_description": f"{csv_row[5]} {csv_row[6]}" if len(csv_row) > 6 else (csv_row[5] if len(csv_row) > 5 else ""),
            }

        payload = [map_csv_to_event_dict(r) for r in rows]
        
    except Exception as e:
        logger.error(f"Erreur lors de la préparation du payload: {str(e)}")
        return {"status": "error", "msg": "payload_error", "detail": str(e)}

    # --- 4) Envoi en batch ---
    api_url = f"{BASE_URL}/errors/api/create-event/"
    headers = {
        "Authorization": f"Bearer {token}", 
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
    

@shared_task(
    bind=True,
    base=Task,
    max_retries=3,
    default_retry_delay=60,
    queue='queue_execute_irm_error_report',
    name='apps.error_management_systems.tasks.task_execute_irm_error_report'
)
def task_execute_irm_error_report(self):
    """
    Génère un rapport d'erreurs IRM quotidien via Oracle
    et écrit un CSV dans le répertoire défini en settings.
    """

    # Configuration d'Oracle - à effectuer avant l'import de cx_Oracle
    import os
    # Définir les variables d'environnement pour le client Oracle si nécessaire
    if hasattr(settings, 'ORACLE_CLIENT_HOME'):
        os.environ['ORACLE_HOME'] = settings.ORACLE_CLIENT_HOME
        os.environ['LD_LIBRARY_PATH'] = settings.ORACLE_CLIENT_HOME + '/lib:' + os.environ.get('LD_LIBRARY_PATH', '')
        os.environ['PATH'] = settings.ORACLE_CLIENT_HOME + '/bin:' + os.environ.get('PATH', '')
    
    try:
        # --- 1. Préparer le répertoire de sortie et les paramètres Oracle
        output_dir = settings.IRM_ERROR_REPORT_OUTPUT_DIR
        os.makedirs(output_dir, exist_ok=True)

        oracle_cfg = {
            "ORACLE_HOST": settings.ORACLE_HOST,
            "ORACLE_PORT": settings.ORACLE_PORT,
            "ORACLE_SERVICE": settings.ORACLE_SERVICE,
            "ORACLE_USER": settings.ORACLE_USER,
            "ORACLE_PASSWORD": settings.ORACLE_PASSWORD,
        }

        # --- 2. Construire la requête
        query = f"""
        SELECT * FROM ISL_MTNB5.L1_VW_CALLDATA
        """

        # --- 3. Fichier de sortie
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(output_dir, f"irm_error_report_{timestamp}.csv")
        logger.info("Génération du rapport IRM vers: %s", output_file)

        # --- 4. Connexion à la base de données Oracle via SQLAlchemy
        import pandas as pd
        from sqlalchemy import create_engine
        
        # Création de la chaîne de connexion directement pour plus de contrôle
        # Format: oracle+cx_oracle://username:password@host:port/?service_name=service
        connection_string = f"oracle+cx_oracle://{oracle_cfg['ORACLE_USER']}:{oracle_cfg['ORACLE_PASSWORD']}@{oracle_cfg['ORACLE_HOST']}:{oracle_cfg['ORACLE_PORT']}/?service_name={oracle_cfg['ORACLE_SERVICE']}"
        
        # Log de débogage sans le mot de passe
        safe_connection = connection_string.replace(oracle_cfg['ORACLE_PASSWORD'], '********')
        logger.debug(f"Connexion avec: {safe_connection}")
        
        engine = create_engine(connection_string)
        
        try:
            # Exécution de la requête et obtention des résultats dans un DataFrame
            logger.debug("Connexion à Oracle et exécution de la requête")
            
            # Dans un contexte de production, on utiliserait un with pour gérer la connexion
            with engine.connect() as connection:
                # Ajout d'un délai d'attente plus long car la requête peut prendre du temps
                df = pd.read_sql(query, connection, coerce_float=True)
            
            # Écriture des résultats dans un fichier CSV avec une configuration améliorée
            logger.debug(f"Écriture de {len(df)} lignes dans le fichier CSV")
            df.to_csv(
                output_file, 
                index=False, 
                encoding='utf-8',
                quoting=1,  # QUOTE_ALL pour éviter les problèmes de format
                date_format='%Y-%m-%d %H:%M:%S'
            )
            
            row_count = len(df)
            logger.info(f"Rapport IRM généré avec succès: {output_file} ({row_count} lignes)")
            return {"status": "success", "output_file": output_file, "row_count": row_count}
            
        except Exception as db_exc:
            logger.error(f"Erreur lors de l'exécution de la requête Oracle: {str(db_exc)}")
            # Ajouter plus de détails pour le débogage
            if hasattr(db_exc, 'orig') and db_exc.orig is not None:
                logger.error(f"Erreur Oracle originale: {str(db_exc.orig)}")
            raise db_exc

    except Exception as exc:
        logger.exception("Exception dans task_execute_irm_error_report")
        # retry si nécessaire
        raise self.retry(exc=exc)
    

@shared_task(
    bind=True,
    queue='queue_process_irm_error_report',  # ou autre queue dédiée
    name='apps.error_management_systems.tasks.process_irm_error_report'
)
def process_irm_error_report(self):
    """
    1) Lit le CSV IRM du jour
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
    output_dir = settings.IRM_ERROR_REPORT_OUTPUT_DIR
    today_str = datetime.now().strftime('%Y%m%d')
    pattern = os.path.join(output_dir, f'irm_error_report_{today_str}_*.csv')
    files = glob.glob(pattern)
    if not files:
        logger.info(f"Aucun rapport IRM pour le {today_str}")
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
                "service_name": csv_row[2] if len(csv_row) > 2 else "Unknown",
                "error_category_name": csv_row[1] if len(csv_row) > 1 else "Unknown",
                "error_count": error_count,
                "error_description": csv_row[4] if len(csv_row) > 4 else "Unknown",
            }

        payload = [map_csv_to_event_dict(r) for r in rows]
        
    except Exception as e:
        logger.error(f"Erreur lors de la préparation du payload: {str(e)}")
        return {"status": "error", "msg": "payload_error", "detail": str(e)}

    # --- 4) Envoi en batch ---
    api_url = f"{BASE_URL}/errors/api/create-event/"
    headers = {
        "Authorization": f"Bearer {token}", 
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