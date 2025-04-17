from celery import shared_task
import os
import logging
from datetime import datetime
from typing import Dict

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def execute_cis_error_report(config: Dict[str, str], output_dir: str = "/srv/itsea_files/error_report_files"):
    """
    Tâche Celery qui exécute une requête SQL pour générer un rapport d'erreurs CIS
    et sauvegarde le résultat dans un fichier CSV. 
    Chaque exécution génère un nouveau fichier avec horodatage.
    
    Args:
        config (Dict[str, str]): Configuration Presto
        output_dir (str): Répertoire pour les fichiers de sortie
    
    Returns:
        Dict: Résultat de l'exécution
    """
    try:
        # Créer le répertoire de sortie s'il n'existe pas
        os.makedirs(output_dir, exist_ok=True)
        # Format the current date as YYYYMMDD
        today_str = datetime.now().strftime("%Y%m%d")
        
        # Définir la requête SQL directement
        query = f"""
        SELECT 
            'CIS' as Domain,
            sptype as "Service Type",
            producttype as "Service Name", 
            COUNT(*) AS "Error Count", 
            reason as "Error Reason"
        FROM hive.feeds.cis
        WHERE tbl_dt = '{today_str}'
        and upper(success_failure) like '%FAIL%'
        GROUP BY producttype, reason, sptype
        ORDER BY "Error Count" desc
        """
        
        # Générer un nom de fichier de sortie unique avec horodatage
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(output_dir, f"cis_error_report_{timestamp}.csv")
        
        logger.info(f"Génération du rapport d'erreurs CIS vers: {output_file}")
        
        # Construction de la commande Presto
        import subprocess
        import os
        
        PRESTO_CLI_PATH = "/etc/nginx/sites-available/argon-dashboard-django/presto"
        
        cmd = [
            PRESTO_CLI_PATH,
            f"--server={config['PRESTO_SERVER']}:{config['PRESTO_PORT']}",
            f"--catalog={config['PRESTO_CATALOG']}",
            f"--schema={config['PRESTO_SCHEMA']}",
            f"--user={config['PRESTO_USER']}",
            f"--keystore-path={config['PRESTO_KEYSTORE_PATH']}",
            f"--keystore-password={config['PRESTO_KEYSTORE_PASSWORD']}",
            "--password",
            "--output-format=CSV",
            "--execute", query
        ]
        
        # Configurer l'environnement pour le mot de passe
        env = os.environ.copy()
        env["PRESTO_PASSWORD"] = config['PRESTO_PASSWORD']
        
        # Logging de la commande (sans le mot de passe)
        safe_cmd = ' '.join(cmd).replace(config['PRESTO_KEYSTORE_PASSWORD'], '********')
        logger.debug("Commande d'exécution: %s", safe_cmd)
        
        # Exécuter avec sortie dans le fichier CSV
        with open(output_file, 'w') as f_out:
            process = subprocess.run(
                cmd,
                stdout=f_out,
                stderr=subprocess.PIPE,
                env=env,
                text=True,
                check=False
            )
        
        # Vérifier le résultat
        if process.returncode != 0:
            logger.error(f"Erreur lors de l'exécution de la requête Presto: {process.stderr}")
            return {
                "status": "error",
                "message": process.stderr
            }
        else:
            logger.info(f"Rapport d'erreurs CIS généré avec succès: {output_file}")
            return {
                "status": "success",
                "output_file": output_file,
                "message": f"Résultat enregistré dans {output_file}"
            }
            
    except Exception as e:
        logger.exception(f"Exception dans l'exécution de la tâche CIS error report: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }