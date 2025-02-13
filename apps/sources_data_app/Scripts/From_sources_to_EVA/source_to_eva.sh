#!/bin/bash

# Définir le fichier de log
LOG_FILE="/var/log/itsea/execute_presto_and_process.log"

# Créer le répertoire du fichier de log s'il n'existe pas
mkdir -p /var/log/itsea

# Fonction pour ajouter des messages dans le fichier de log avec timestamp
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

# Charger les configurations à partir du fichier config.properties
CONFIG_FILE="/nethome/samitoure_pws/itsea/Scripts/SourceData/eva/connection_settings/config.properties"

if [[ ! -f "$CONFIG_FILE" ]]; then
  log_message "Erreur : Le fichier config.properties est introuvable."
  exit 1
fi

source "$CONFIG_FILE"

# Vérifier que toutes les variables nécessaires sont définies
REQUIRED_VARS=("PRESTO_SERVER" "PRESTO_PORT" "PRESTO_CATALOG" "PRESTO_SCHEMA" "PRESTO_USER" "PRESTO_PASSWORD" "PRESTO_KEYSTORE_PATH" "PRESTO_KEYSTORE_PASSWORD")

for VAR in "${REQUIRED_VARS[@]}"; do
  if [[ -z "${!VAR}" ]]; then
    log_message "Erreur : La variable $VAR n'est pas définie dans config.properties."
    exit 1
  fi
done

# Définir les chemins
PRESTO_CLI="/nethome/samitoure_pws/itsea/Scripts/SourceData/eva/connection_settings/presto" # Assurez-vous que l'exécutable Presto CLI est dans ce chemin ou modifiez-le.
OUTPUT_FILE="/srv/itsea_files/cis_source_output_$(date '+%Y%m%d_%H%M%S').csv" # Nom dynamique avec date et heure
PYTHON_SCRIPT="/nethome/samitoure_pws/itsea/Scripts/SourceData/cis_process_csv.py"

# Vérifier que Presto CLI est accessible
if [[ ! -x "$PRESTO_CLI" ]]; then
  log_message "Erreur : L'exécutable Presto CLI est introuvable ou non exécutable."
  exit 1
fi

# Obtenez la date actuelle au format YYYYMMDD
CURRENT_DATE=$(date +%Y%m%d)

# Définir la requête SQL avec la date dynamique
SQL_QUERY=$(cat <<EOF
SELECT 
    'CIS' as Domain,
    sptype as Service_Type,
    producttype as Service_Name, 
    COUNT(*) AS Error_Count, 
    reason as Error_Reason
FROM hive.feeds.cis
WHERE tbl_dt = $CURRENT_DATE
and success_failure = 'FAILURE'
GROUP BY producttype, reason, sptype
ORDER BY Error_Count desc;
EOF
)

# Exécuter la requête et enregistrer les résultats dans un fichier CSV
log_message "Exécution de la requête Presto..."
"${PRESTO_CLI}" \
  --server "${PRESTO_SERVER}:${PRESTO_PORT}" \
  --catalog "${PRESTO_CATALOG}" \
  --schema "${PRESTO_SCHEMA}" \
  --user "${PRESTO_USER}" \
  --keystore-path="${PRESTO_KEYSTORE_PATH}" \
  --keystore-password="${PRESTO_KEYSTORE_PASSWORD}" \
  --execute "${SQL_QUERY}" \
  --output-format CSV > "${OUTPUT_FILE}" 2>> "$LOG_FILE"

if [[ $? -ne 0 ]]; then
  log_message "Erreur : La requête Presto a échoué."
  exit 1
fi

# Add header to the result CSV file
sed -i '1i\Domain,Service_Type,Service_Name,Error_Count,Error_Reason' "${OUTPUT_FILE}"

log_message "Résultats enregistrés dans ${OUTPUT_FILE}."

# Lancer le script Python pour traiter le fichier CSV
if [[ -f "$PYTHON_SCRIPT" ]]; then
  log_message "Lancement du script Python pour traiter les données..."
  python3 "$PYTHON_SCRIPT" "$OUTPUT_FILE" >> "$LOG_FILE" 2>&1

  if [[ $? -eq 0 ]]; then
    log_message "Traitement des données terminé avec succès."
  else
    log_message "Erreur lors de l'exécution du script Python."
  fi
else
  log_message "Erreur : Le script Python ${PYTHON_SCRIPT} est introuvable."
  exit 1
fi