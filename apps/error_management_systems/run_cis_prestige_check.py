from utils import execute_presto_query_to_csv
from datetime import datetime, timedelta

def task_generate_my_report():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"/srv/itsea_files/prestige_report_files/prestige_report_{timestamp}.csv"
    now = datetime.now()
    yesterday = now - timedelta(days=1)
    yesterday_str = yesterday.strftime("%Y%m%d")

    query = f"""
    select msisdn_key
    FROM hive.feeds.air_refill_ma
    WHERE tbl_dt={yesterday_str}
    AND transaction_type_cd like '%Prestige%'
    """

    result = execute_presto_query_to_csv(query=query, output_file=output_path)

    if result["status"] == "success":
        print("CSV généré:", result["output_file"])
    else:
        print("Erreur:", result["message"])
