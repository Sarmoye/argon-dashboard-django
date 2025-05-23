import os
import subprocess
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

PRESTO_SERVER="https://lnx-eva-master01.mtn.bj"
PRESTO_PORT="8443"
PRESTO_CATALOG="hive"
PRESTO_SCHEMA="hive"
PRESTO_USER="itsea_user_svc"
PRESTO_PASSWORD="g3$JdBv2C3t#Tc&JjK57@8/qA)"
PRESTO_KEYSTORE_PATH="/etc/nginx/sites-available/argon-dashboard-django/eva_key/benin_keystore.jks"
PRESTO_KEYSTORE_PASSWORD="enzoslR722$"
PRESTO_CLI_PATH="/etc/nginx/sites-available/argon-dashboard-django/presto"

def execute_presto_query_to_csv(query, output_file, presto_config=None):
    """
    Exécute une requête SQL via Presto CLI et sauvegarde les résultats dans un fichier CSV.
    
    Args:
        query (str): La requête SQL à exécuter
        output_file (str): Chemin complet du fichier CSV de sortie
        presto_config (dict, optional): Configuration Presto personnalisée.
                                       Si non fournie, utilise les paramètres des 
    
    Returns:
        dict: Résultat de l'opération avec statut et détails
    """
    
    try:
        # Assurer que le répertoire de sortie existe
        output_dir = os.path.dirname(output_file)
        os.makedirs(output_dir, exist_ok=True)
        
        # Utiliser la configuration par défaut ou celle fournie
        if presto_config is None:
            presto_config = {
                "PRESTO_SERVER": PRESTO_SERVER,
                "PRESTO_PORT": PRESTO_PORT,
                "PRESTO_CATALOG": PRESTO_CATALOG,
                "PRESTO_SCHEMA": PRESTO_SCHEMA,
                "PRESTO_USER": PRESTO_USER,
                "PRESTO_PASSWORD": PRESTO_PASSWORD,
                "PRESTO_KEYSTORE_PATH": PRESTO_KEYSTORE_PATH,
                "PRESTO_KEYSTORE_PASSWORD": PRESTO_KEYSTORE_PASSWORD,
                "PRESTO_CLI_PATH": PRESTO_CLI_PATH
            }
        
        # Vérifier que les paramètres requis sont présents
        required_params = ["PRESTO_SERVER", "PRESTO_PORT", "PRESTO_CATALOG", 
                          "PRESTO_SCHEMA", "PRESTO_USER", "PRESTO_PASSWORD",
                          "PRESTO_KEYSTORE_PATH", "PRESTO_KEYSTORE_PASSWORD",
                          "PRESTO_CLI_PATH"]
        
        for param in required_params:
            if param not in presto_config:
                raise ValueError(f"Paramètre requis manquant dans la configuration Presto: {param}")
        
        # Préparer la commande Presto CLI
        presto_cli = presto_config["PRESTO_CLI_PATH"]
        cmd = [
            presto_cli,
            f"--server={presto_config['PRESTO_SERVER']}:{presto_config['PRESTO_PORT']}",
            f"--catalog={presto_config['PRESTO_CATALOG']}",
            f"--schema={presto_config['PRESTO_SCHEMA']}",
            f"--user={presto_config['PRESTO_USER']}",
            f"--keystore-path={presto_config['PRESTO_KEYSTORE_PATH']}",
            f"--keystore-password={presto_config['PRESTO_KEYSTORE_PASSWORD']}",
            "--password",
            "--output-format=CSV",
            "--execute", query
        ]
        
        # Version sécurisée pour le logging (masque les mots de passe)
        safe_cmd = " ".join(cmd).replace(presto_config['PRESTO_KEYSTORE_PASSWORD'], "********")
        logger.debug("Commande Presto CLI: %s", safe_cmd)
        
        # Injecter le password dans l'environnement
        env = os.environ.copy()
        env["PRESTO_PASSWORD"] = presto_config['PRESTO_PASSWORD']
        
        logger.info("Exécution de la requête Presto vers: %s", output_file)
        
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
            return {"status": "error", "message": err, "output_file": output_file}
        
        logger.info("Requête Presto exécutée avec succès: %s", output_file)
        return {"status": "success", "output_file": output_file}
    
    except Exception as exc:
        logger.exception("Exception lors de l'exécution de la requête Presto")
        return {"status": "error", "message": str(exc), "exception": exc}