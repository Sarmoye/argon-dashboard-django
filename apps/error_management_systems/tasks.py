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
from datetime import datetime
from celery import shared_task
from django.conf import settings
import logging
import requests

logger = logging.getLogger(__name__)

HEADERS = ['Domain', 'Service Type', 'Service Name', 'Error Count', 'Error Reason']

@shared_task(
    bind=True,
    queue='queue_process_cis_error_report',  # ou autre queue dédiée
    name='apps.error_management_systems.tasks.process_cis_error_report'
)
def process_and_push_cis_errors(self):
    """
    1) Lit le CSV CIS du jour
    2) Obtient un token auprès de l'API interne
    3) Envoie en batch les événements vers create_event_api
    """
    BASE_URL = "http://ems.mtn.bj"        # Ajustez selon votre host/port
    USER     = "celery_user"                  # l’utilisateur que vous utilisez pour l’API
    PASS     = "samitoure@!1&112024sadmin"
    # --- 1) Lecture du CSV ---
    output_dir = settings.CIS_ERROR_REPORT_OUTPUT_DIR
    today_str  = datetime.now().strftime('%Y%m%d')
    pattern    = os.path.join(output_dir, f'cis_error_report_{today_str}_*.csv')
    files      = glob.glob(pattern)
    if not files:
        logger.info(f"Aucun rapport CIS pour le {today_str}")
        return {"status": "no_file"}

    latest_file = max(files)
    logger.info(f"Fichier à traiter : {latest_file} (taille {os.path.getsize(latest_file)} octets)")
    with open(latest_file, newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.reader(csvfile)
        rows   = list(reader)

    if not rows:
        logger.warning("Le CSV est vide après lecture.")
        return {"status": "empty_file"}

    # --- 2) Récupération du token ---
    api_user = USER
    api_pass = PASS
    base_url = BASE_URL

    token_url = f"{base_url}/errors/api/token/"
    try:
        resp = requests.post(token_url, json={"username": api_user, "password": api_pass}, timeout=10)
        resp.raise_for_status()
        token = resp.json()['token']
        logger.info("Token obtenu avec succès.")
    except Exception as exc:
        logger.exception("Erreur lors de la récupération du token")
        return {"status": "error", "msg": "token_error", "detail": str(exc)}

    # --- 3) Préparation du payload ---
    def map_csv_to_event_dict(csv_row):
        return {
            "system_name":         csv_row[0],
            "service_name":        csv_row[1],
            "error_category_name": csv_row[2],
            "error_count":         csv_row[3],
            "error_description":   csv_row[4],
        }

    payload = [map_csv_to_event_dict(r) for r in rows]

    # --- 4) Envoi en batch ---
    api_url = f"{base_url}/errors/api/create-event/"
    headers = {"Authorization": f"Token {token}"}
    try:
        resp = requests.post(api_url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        logger.info("Envoi des événements réussi.")
        return {"status": "success", "response": resp.json()}
    except Exception as exc:
        logger.exception("Erreur lors de l'envoi des événements")
        # Si échec, on peut relancer la tâche
        raise self.retry(exc=exc, countdown=60, max_retries=3)

