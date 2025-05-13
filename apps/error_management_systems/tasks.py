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
import requests
from datetime import datetime
from django.conf import settings

# 1. Lecture du CSV (comme vous l'avez déjà)
def load_cis_csv_rows():
    output_dir = settings.CIS_ERROR_REPORT_OUTPUT_DIR
    today_str = datetime.now().strftime('%Y%m%d')
    pattern = os.path.join(output_dir, f'cis_error_report_{today_str}_*.csv')
    files = glob.glob(pattern)
    if not files:
        return []
    latest_file = max(files)
    with open(latest_file, newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.reader(csvfile)
        return list(reader)

# 2. Mapping de chaque ligne CSV vers le schéma attendu par l’API
def map_csv_to_event_dict(csv_row):
    # csv_row = ['CIS', 'PRODUCT_BUY', 'DATA', '4574', 'CIS:200:SUCCESS']
    return {
        "system_name":         csv_row[0],
        "service_name":        csv_row[1],
        "error_category_name": csv_row[2],
        "error_count":         csv_row[3],
        "error_description":   csv_row[4],
        # vous pouvez ajouter ici d'autres champs optionnels, e.g. :
        # "system_classification": "...",
        # "service_classification": "...",
        # "detected_by": "logs",
        # etc.
    }

# 3. Récupération d’un token d’authentification
def get_token(username, password, base_url):
    url = f"{base_url}/errors/api/token/"
    resp = requests.post(url, json={"username": username, "password": password})
    resp.raise_for_status()
    return resp.json()['token']

# 4. Envoi en batch vers create_event_api
def push_events_to_api(rows, token, base_url):
    url = f"{base_url}/errors/api/create-event/"
    headers = {"Authorization": f"Token {token}"}
    # DRF supporte la liste en entrée
    payload = [map_csv_to_event_dict(r) for r in rows]
    resp = requests.post(url, json=payload, headers=headers)
    resp.raise_for_status()
    return resp.json()

# 5. Script principal
if __name__ == "__main__":
    BASE_URL = "http://ems.mtn.bj"        # Ajustez selon votre host/port
    USER     = "celery_user"                  # l’utilisateur que vous utilisez pour l’API
    PASS     = "samitoure@!1&112024sadmin"
    rows = load_cis_csv_rows()
    if not rows:
        print("Aucune ligne à traiter.")
        exit(0)

    token = get_token(USER, PASS, BASE_URL)
    result = push_events_to_api(rows, token, BASE_URL)
    print("Réponse API :", result)
