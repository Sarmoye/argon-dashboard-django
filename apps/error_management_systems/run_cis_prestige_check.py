import csv
import requests
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
import os

# Assume this utility function is available as provided
from utils import execute_presto_query_to_csv

def task_generate_my_report():
    """
    Generates a CSV report from Presto with MSISDN and external_data2 for Prestige transactions.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"/srv/itsea_files/prestige_report_files/prestige_report_{timestamp}.csv"
    now = datetime.now()
    yesterday = now - timedelta(days=1)
    yesterday_str = yesterday.strftime("%Y%m%d")

    query = f"""
    select msisdn_key,
	external_data2
    FROM hive.feeds.air_refill_ma
    WHERE tbl_dt={yesterday_str}
    AND transaction_type_cd like '%Prestige%'
    """

    result = execute_presto_query_to_csv(query=query, output_file=output_path)

    if result["status"] == "success":
        print("CSV généré:", result["output_file"])
        return result["output_file"]
    else:
        print("Erreur:", result["message"])
        return None

def process_prestige_data():
    """
    Orchestrates the process of generating the initial report,
    calling the API for each MSISDN, parsing the response,
    filtering data, and generating the final report.
    """
    input_csv_path = task_generate_my_report()

    if not input_csv_path:
        print("Failed to generate initial Presto report. Exiting.")
        return

    api_url_template = "http://10.10.48.70:8080/cisBusiness/service/fulfillmentService?username=aa8600be791820d82325ab7fa2467d88&password=3f2e678227aa078e56e60bf38663876f&iname=OBCC&msisdn={msisdn_key}&input=VIEW_HISTORY"

    output_report_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_output_path = f"/srv/itsea_files/prestige_report_files/prestige_final_report_{output_report_timestamp}.csv"

    processed_data = []

    with open(input_csv_path, 'r') as infile:
        reader = csv.reader(infile)
        next(reader)  # Skip header row if exists

        for row in reader:
            if len(row) < 2:
                print(f"Skipping malformed row: {row}")
                continue

            msisdn_key = row[0]
            external_data2 = row[1]

            api_url = api_url_template.format(msisdn_key=msisdn_key)
            try:
                response = requests.get(api_url)
                response.raise_for_status()  # Raise an exception for HTTP errors
                
                # Parse the XML response
                root = ET.fromstring(response.text)
                
                product_id = None
                product_expiry = None
                is_balance_available = None

                # Navigate through the XML to find the desired elements
                for product_detail in root.findall(".//productDetail"):
                    current_product_id = product_detail.findtext("productId")
                    
                    if current_product_id == external_data2:
                        product_id = current_product_id
                        product_expiry = product_detail.findtext("productExpiry")
                        is_balance_available = product_detail.findtext("isBalanceAvailable")
                        break # Found the matching product, no need to check other products for this MSISDN

                if product_id and product_expiry and is_balance_available:
                    processed_data.append({
                        "MSISDN": msisdn_key,
                        "Product ID": product_id,
                        "Expiry Date": product_expiry,
                        "Prestige bundle is display": is_balance_available
                    })
                else:
                    print(f"No matching product found or incomplete data for MSISDN: {msisdn_key} (external_data2: {external_data2})")
                    processed_data.append({
                        "MSISDN": msisdn_key,
                        "Product ID": "",
                        "Expiry Date": "",
                        "Prestige bundle is display": "False"
                    })

            except requests.exceptions.RequestException as e:
                print(f"Error making API request for MSISDN {msisdn_key}: {e}")
            except ET.ParseError as e:
                print(f"Error parsing XML response for MSISDN {msisdn_key}: {e}")
            except Exception as e:
                print(f"An unexpected error occurred for MSISDN {msisdn_key}: {e}")


    # Write the processed data to the final CSV
    if processed_data:
        with open(final_output_path, 'w', newline='') as outfile:
            fieldnames = ["MSISDN", "Product ID", "Expiry Date", "Prestige bundle is display"]
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)

            writer.writeheader()
            writer.writerows(processed_data)
        print("Final report generated:", final_output_path)
    else:
        print("No data to write to the final report.")

# To run the entire process:
if __name__ == "__main__":
    # Ensure the directory exists
    output_dir = "/srv/itsea_files/prestige_report_files/"
    os.makedirs(output_dir, exist_ok=True)
    process_prestige_data()