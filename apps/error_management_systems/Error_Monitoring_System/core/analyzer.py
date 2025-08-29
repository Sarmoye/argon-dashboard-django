import pandas as pd
from datetime import datetime, timedelta
from core.file_utils import get_files_by_date_range
from core.data_processor import read_csv_data
import os

def analyze_historical_trends(directory, system_name, days=7):
    """Analyse les tendances sur les N derniers jours avec insights avancés"""
    files = get_files_by_date_range(directory, days)
    if len(files) < 2:
        return None
    
    trends_data = []
    
    for file_path in files:
        try:
            data = read_csv_data(file_path, system_name)
            if data is not None and not data.empty:
                grouped_data = data.groupby('Service Name')['Error Count'].sum().reset_index()
                
                file_date = datetime.fromtimestamp(os.path.getctime(file_path))
                total_errors = grouped_data['Error Count'].sum()
                
                # Récupérer les listes de services
                affected_services_list = grouped_data[grouped_data['Error Count'] > 0]['Service Name'].tolist()
                critical_services_list = grouped_data[grouped_data['Error Count'] >= 10]['Service Name'].tolist()
                
                affected_services_count = len(affected_services_list)
                critical_services_count = len(critical_services_list)
                total_services = len(grouped_data)
                
                trends_data.append({
                    'date': file_date,
                    'total_errors': total_errors,
                    'affected_services': affected_services_count,
                    'critical_services': critical_services_count,
                    'total_services': total_services,
                    'error_density': total_errors / total_services if total_services > 0 else 0,
                    'reliability_score': ((total_services - affected_services_count) / total_services * 100) if total_services > 0 else 0,
                    'affected_services_list': affected_services_list,
                    'critical_services_list': critical_services_list
                })
        except Exception as e:
            print(f"Erreur analyse fichier {file_path}: {e}")
            continue
            
    if not trends_data or len(trends_data) < 2:
        return None
    
    trends_df = pd.DataFrame(trends_data)
    trends_df = trends_df.sort_values('date')
    
    # Trouver le fichier le plus récent (current)
    current = trends_df.iloc[-1]
    current_time = current['date']
    
    # Calculer la veille à la même heure avec gestion des minutes négatives
    previous_day = current_time - timedelta(days=1)
    
    # Créer la fenêtre horaire de ±30 minutes de manière sécurisée
    time_target = previous_day.replace(hour=current_time.hour, minute=current_time.minute, second=0, microsecond=0)
    time_window_start = time_target - timedelta(minutes=30)
    time_window_end = time_target + timedelta(minutes=30)
    
    # Filtrer les fichiers dans la fenêtre horaire de la veille
    previous_files = trends_df[
        (trends_df['date'] >= time_window_start) & 
        (trends_df['date'] <= time_window_end)
    ]
    
    if previous_files.empty:
        # Si aucun fichier à la même heure hier, prendre le fichier le plus proche de la veille
        previous_day_files = trends_df[trends_df['date'].dt.date == previous_day.date()]
        if previous_day_files.empty:
            # Si aucun fichier la veille, prendre le précédent disponible
            previous_files_all = trends_df[trends_df['date'] < current_time]
            if previous_files_all.empty:
                return None
            previous = previous_files_all.iloc[-1]
        else:
            # Prendre le fichier le plus proche de l'heure cible
            previous_day_files = previous_day_files.copy()
            previous_day_files['time_diff'] = abs((previous_day_files['date'] - time_target).dt.total_seconds())
            previous = previous_day_files.loc[previous_day_files['time_diff'].idxmin()]
    else:
        # Prendre le fichier le plus proche de l'heure exacte dans la fenêtre
        previous_files = previous_files.copy()
        previous_files['time_diff'] = abs((previous_files['date'] - time_target).dt.total_seconds())
        previous = previous_files.loc[previous_files['time_diff'].idxmin()]

    print(f'CURRENT {current}')
    print(f'PREVIOUS {previous}')
    print(f'Current time: {current_time}')
    print(f'Target time for previous day: {time_target}')
    print(f'Time window: {time_window_start} - {time_window_end}')
    
    error_trend = current['total_errors'] - previous['total_errors']
    affected_trend = current['affected_services'] - previous['affected_services']
    critical_trend = current['critical_services'] - previous['critical_services']
    reliability_trend = current['reliability_score'] - previous['reliability_score']
    
    if len(trends_df) >= 4:
        avg_recent = trends_df.tail(3)['total_errors'].mean()
        avg_older = trends_df.head(3)['total_errors'].mean()
        week_trend = avg_recent - avg_older
        volatility = trends_df['total_errors'].std()
        stability_trend = "STABLE" if volatility < 5 else "MODERATE" if volatility < 15 else "HIGH_VOLATILITY"
    else:
        week_trend = error_trend
        volatility = 0
        stability_trend = "INSUFFICIENT_DATA"
    
    momentum = "NEUTRAL"
    if len(trends_df) >= 3:
        # Pour le momentum, trouver le jour précédent du previous
        previous_time = previous['date']
        day_before_previous = previous_time - timedelta(days=1)
        day_before_files = trends_df[trends_df['date'].dt.date == day_before_previous.date()]
        if not day_before_files.empty:
            # Trouver le fichier le plus proche de la même heure que previous
            target_time_prev = day_before_previous.replace(hour=previous_time.hour, minute=previous_time.minute)
            day_before_files = day_before_files.copy()
            day_before_files['time_diff'] = abs((day_before_files['date'] - target_time_prev).dt.total_seconds())
            day_before = day_before_files.loc[day_before_files['time_diff'].idxmin()]
            
            trend_yesterday = previous['total_errors'] - day_before['total_errors']
            if error_trend > trend_yesterday + 2:
                momentum = "ACCELERATING"
            elif error_trend < trend_yesterday - 2:
                momentum = "DECELERATING"
    
    predicted_errors = max(0, current['total_errors'] + error_trend)
    prediction_confidence = "HIGH" if len(trends_df) >= 5 else "MEDIUM" if len(trends_df) >= 3 else "LOW"

    return {
        'data': trends_df,
        'current_errors': int(current['total_errors']),
        'previous_errors': int(previous['total_errors']),
        'error_trend': int(error_trend),
        'affected_trend': int(affected_trend),
        'critical_trend': int(critical_trend),
        'reliability_trend': round(reliability_trend, 1),
        'week_trend': week_trend,
        'improvement_rate': round((error_trend / previous['total_errors'] * 100) if previous['total_errors'] > 0 else 0, 1),
        'days_analyzed': len(trends_df),
        'volatility': round(volatility, 2),
        'stability_trend': stability_trend,
        'momentum': momentum,
        'predicted_errors': int(predicted_errors),
        'prediction_confidence': prediction_confidence,
        'avg_error_density': round(trends_df['error_density'].mean(), 2),
        'peak_errors': int(trends_df['total_errors'].max()),
        'best_day_errors': int(trends_df['total_errors'].min()),
        'current_affected_services_list': current['affected_services_list'],
        'current_critical_services_list': current['critical_services_list'],
        'comparison_time_info': f"Comparé à {previous['date'].strftime('%Y-%m-%d %H:%M')} (cible: {time_target.strftime('%H:%M')})"
    }