import pandas as pd
from config.systems import SYSTEMS_CONFIG

def read_csv_data(file_path, system_name):
    """Lit et traite les données CSV"""
    try:
        config = SYSTEMS_CONFIG[system_name]
        headers = config['headers']
        skip_rows = config['skip_rows']
        
        df = pd.read_csv(file_path, header=None, names=headers, skiprows=skip_rows)
        
        if 'Error Count' in df.columns:
            df['Error Count'] = pd.to_numeric(df['Error Count'], errors='coerce').fillna(0)
        
        return df
    except Exception as e:
        print(f"Erreur lecture CSV: {e}")
        return None