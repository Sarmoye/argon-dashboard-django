import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
import numpy as np
from config.systems import SYSTEMS_CONFIG
from core.file_utils import *
from core.data_processor import read_csv_data


def create_trend_chart(directory, trends_data, system_name):
    """Crée un graphique de tendance avancé avec prédictions au style Soft UI."""
    if not trends_data or trends_data['data'].empty:
        return None
    
    try:
        df = trends_data['data']
        
        # --- Soft UI Enhancements ---
        plt.style.use('seaborn-v0_8-whitegrid')
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(18, 14))
        fig.patch.set_facecolor('#f0f2f5')
        
        colors_map = {'CIS': '#e74c3c', 'IRM': '#f39c12', 'ECW': '#27ae60'}
        primary_color = colors_map.get(system_name, '#3498db')
        
        # Helper for common styling
        def apply_soft_ui_to_ax(ax):
            ax.set_facecolor('white')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_color('#cccccc')
            ax.spines['bottom'].set_color('#cccccc')
            ax.tick_params(axis='x', colors='#555555')
            ax.tick_params(axis='y', colors='#555555')
            ax.grid(color='#e0e0e0', linestyle='--', linewidth=0.7, alpha=0.7)

        # Graphique 1: Evolution des erreurs avec prédiction
        dates = [d.strftime('%b %d') for d in df['date']]
        ax1.plot(dates, df['total_errors'], marker='o', linewidth=3, markersize=8, 
                 color=primary_color, markerfacecolor='white', markeredgewidth=2, 
                 markeredgecolor=primary_color, label='Actual Errors')
        ax1.fill_between(dates, df['total_errors'], alpha=0.1, color=primary_color)
        
        # Ajouter la prédiction
        if 'predicted_errors' in trends_data:
            pred_date = (df['date'].iloc[-1] + timedelta(days=1)).strftime('%b %d')
            all_dates = dates + [pred_date]
            pred_line = list(df['total_errors']) + [trends_data['predicted_errors']]
            ax1.plot(all_dates[-2:], pred_line[-2:], 'r--', linewidth=2, alpha=0.6, label='Prediction')
            ax1.scatter([pred_date], [trends_data['predicted_errors']], color='red', s=120, alpha=0.7, zorder=5)
            ax1.text(pred_date, trends_data['predicted_errors'] * 1.05, 
                     f"{int(trends_data['predicted_errors'])}", color='red', 
                     ha='center', va='bottom', fontsize=10, fontweight='bold')
        
        ax1.set_title(f'{system_name} - Error Trends & Predictions', 
                      fontsize=16, fontweight='bold', color='#333333', pad=20)
        ax1.set_ylabel('Total Errors', fontsize=12, fontweight='bold', color='#555555')
        ax1.tick_params(axis='x', rotation=30)
        ax1.legend(fontsize=10, frameon=True, shadow=True, fancybox=True, loc='upper left')
        apply_soft_ui_to_ax(ax1)
        
        # Graphique 2: Répartition des erreurs par service
        # Obtenir les données du jour le plus récent
        latest_data = df.iloc[-1]
        
        # Lire le fichier CSV du jour le plus récent pour obtenir la répartition par service
        latest_date = latest_data['date']
        latest_file = None
        
        # Trouver le fichier correspondant à la date la plus récente
        for file_path in get_files_by_date_range(directory, 1):  # On cherche dans les fichiers du dernier jour
            file_date = datetime.fromtimestamp(os.path.getctime(file_path))
            if file_date.date() == latest_date.date():
                latest_file = file_path
                break
        
        if latest_file:
            try:
                # Lire les données du fichier
                data = read_csv_data(latest_file, system_name)
                if data is not None and not data.empty:
                    # Grouper par service et sommer les erreurs
                    service_errors = data.groupby('Service Name')['Error Count'].sum().reset_index()
                    # Trier par nombre d'erreurs décroissant
                    service_errors = service_errors.sort_values('Error Count', ascending=False)
                    
                    # Prendre les 10 services avec le plus d'erreurs (ou moins si moins de 10)
                    top_services = service_errors.head(10)
                    
                    # Créer un graphique à barres horizontales
                    bars = ax2.barh(top_services['Service Name'], top_services['Error Count'], 
                                   color=primary_color, alpha=0.7)
                    
                    # Ajouter les valeurs sur les barres
                    for bar in bars:
                        width = bar.get_width()
                        ax2.text(width + 0.1, bar.get_y() + bar.get_height()/2, 
                                f'{int(width)}', ha='left', va='center', fontsize=9)
                    
                    ax2.set_title(f'Top 10 Services by Error Count\n({latest_date.strftime("%Y-%m-%d")})', 
                                 fontsize=14, fontweight='bold', color='#333333')
                    ax2.set_xlabel('Error Count', fontsize=12, color='#555555')
                    ax2.set_ylabel('Service Name', fontsize=12, color='#555555')
                    
                    # Inverser l'axe Y pour avoir le service avec le plus d'erreurs en haut
                    ax2.invert_yaxis()
                    
            except Exception as e:
                print(f"Erreur lecture fichier {latest_file}: {e}")
                ax2.text(0.5, 0.5, 'Données non disponibles', ha='center', va='center', 
                        transform=ax2.transAxes, fontsize=12, color='red')
        else:
            ax2.text(0.5, 0.5, 'Fichier non trouvé', ha='center', va='center', 
                    transform=ax2.transAxes, fontsize=12, color='red')
        
        apply_soft_ui_to_ax(ax2)

        # Graphique 3: Densité d'erreurs
        ax3.bar(dates, df['error_density'], color=primary_color, alpha=0.7, width=0.6)
        ax3.set_title('Error Density (Errors/Service)', fontsize=14, fontweight='bold', color='#333333')
        ax3.set_ylabel('Errors per Service', fontsize=12, color='#555555')
        apply_soft_ui_to_ax(ax3)
        ax3.tick_params(axis='x', rotation=30)
        
        # Graphique 4: Score de fiabilité
        ax4.plot(dates, df['reliability_score'], marker='s', linewidth=2.5, markersize=7, 
                 color='#28a745', markerfacecolor='white', markeredgewidth=2, markeredgecolor='#28a745')
        ax4.fill_between(dates, df['reliability_score'], 100, alpha=0.1, color='#28a745')
        ax4.set_title('Reliability Score (%)', fontsize=14, fontweight='bold', color='#333333')
        ax4.set_ylabel('Reliability (%)', fontsize=12, color='#555555')
        ax4.set_ylim(max(0, df['reliability_score'].min() - 10), 100)
        ax4.axhline(y=95, color='#007bff', linestyle='--', alpha=0.7, label='SLA Target', linewidth=1.5)
        ax4.legend(fontsize=10, frameon=True, shadow=True, fancybox=True)
        apply_soft_ui_to_ax(ax4)
        ax4.tick_params(axis='x', rotation=30)
        
        plt.tight_layout(pad=3.0)
        fig.suptitle(f'System Performance Analysis: {system_name}', 
                     fontsize=20, fontweight='bold', color='#222222', y=1.02)
        
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight', facecolor=fig.patch.get_facecolor())
        buffer.seek(0)
        chart_data = buffer.getvalue()
        buffer.close()
        plt.close()
        
        return chart_data
        
    except Exception as e:
        print(f"Erreur graphique tendance: {e}")
        plt.close()
        return None

def create_enhanced_chart(data, system_name):
    """Crée un graphique professionnel (fonction existante)"""
    try:
        if data is None or data.empty:
            return None
            
        plt.figure(figsize=(16, 10))
        colors_map = {'CIS': '#e74c3c', 'IRM': '#f39c12', 'ECW': '#27ae60'}
        color = colors_map.get(system_name, '#3498db')
        
        # Top 15 services par erreurs
        service_errors = data.groupby('Service Name')['Error Count'].sum().sort_values(ascending=False).head(15)
        
        if service_errors.empty:
            plt.close()
            return None
        
        bars = plt.bar(range(len(service_errors)), service_errors.values, 
                      color=color, alpha=0.8, edgecolor='black', linewidth=0.7)
        
        plt.title(f'{system_name} - Error Analysis (Top 15 Services)', 
                 fontsize=20, fontweight='bold', pad=25)
        plt.xlabel('Services', fontsize=14, fontweight='bold')
        plt.ylabel('Error Count', fontsize=14, fontweight='bold')
        
        plt.xticks(range(len(service_errors)), service_errors.index, 
                  rotation=45, ha='right', fontsize=11)
        plt.grid(axis='y', alpha=0.3, linestyle='--')
        
        # Valeurs sur les barres
        for i, (bar, value) in enumerate(zip(bars, service_errors.values)):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(service_errors.values) * 0.01,
                   str(int(value)), ha='center', va='bottom', fontweight='bold', fontsize=10)
        
        plt.tight_layout()
        
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight', facecolor='white')
        buffer.seek(0)
        chart_data = buffer.getvalue()
        buffer.close()
        plt.close()
        
        return chart_data
    except Exception as e:
        print(f"Erreur graphique: {e}")
        plt.close()
        return None