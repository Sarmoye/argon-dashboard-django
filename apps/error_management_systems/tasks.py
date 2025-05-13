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

logger = logging.getLogger(__name__)

@shared_task(
    bind=True,
    queue='queue_process_cis_error_report',  # ou autre queue dédiée
    name='apps.error_management_systems.tasks.process_cis_error_report'
)
def process_cis_error_report(self):
    """
    Récupère le fichier CIS ERROR REPORT le plus récent du jour,
    lit toutes les lignes CSV et les renvoie sous forme de liste de dicts.
    """
    # 1. Préparer le répertoire et la date du jour
    output_dir = settings.CIS_ERROR_REPORT_OUTPUT_DIR
    today_str = datetime.now().strftime('%Y%m%d')

    # 2. Chercher tous les fichiers du jour
    pattern = os.path.join(output_dir, f'cis_error_report_{today_str}_*.csv')
    files = glob.glob(pattern)
    if not files:
        logger.info(f"Aucun rapport CIS pour la date {today_str}")
        return []

    # 3. Sélectionner le fichier le plus récent (max par nom lexicographique)
    latest_file = max(files)
    logger.info(f"Fichier CIS le plus récent trouvé: {latest_file}")

    # 4. Lire le CSV
    rows = []
    try:
        with open(latest_file, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # On s'assure d'avoir les bons headers
                rows.append({
                    'Domain': row.get('Domain'),
                    'Service Type': row.get('Service Type'),
                    'Service Name': row.get('Service Name'),
                    'Error Count': row.get('Error Count'),
                    'Error Reason': row.get('Error Reason'),
                })
    except Exception as exc:
        logger.exception(f"Erreur lecture CSV {latest_file}: {exc}")
        raise self.retry(exc=exc)

    logger.info(f"Total lignes lues: {len(rows)}")
    return rows
