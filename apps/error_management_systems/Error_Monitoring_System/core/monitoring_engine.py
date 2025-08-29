from datetime import datetime
from core.file_utils import get_latest_csv_file
from core.data_processor import read_csv_data
from core.analyzer import analyze_historical_trends
from core.visualizer import create_trend_chart, create_enhanced_chart
from core.reporter import create_professional_system_html_with_trends, create_executive_summary_html_with_trends
from core.email_sender import send_email_with_reports
from models.system_stats import SystemStats
from config.systems import SYSTEMS_CONFIG
from config.email import EMAIL_CONFIG

class MonitoringEngine:
    """Moteur principal de monitoring"""
    
    def __init__(self):
        self.systems_data = {}
        self.all_stats = {}
    
    def process_system(self, system_name, config):
        """Traite un système spécifique"""
        print(f"\n{config['icon']} Traitement système {system_name}...")
        
        # Données actuelles
        current_file = get_latest_csv_file(config['directory'])
        current_data = None
        trends_data = None
        
        if current_file:
            current_data = read_csv_data(current_file, system_name)
            # Analyse de tendance
            trends_data = analyze_historical_trends(config['directory'], system_name, days=7)
            
            if current_data is not None:
                self.systems_data[system_name] = current_data
                stats = SystemStats.from_data(system_name, current_data, trends_data)
                self.all_stats[system_name] = stats
                
                # Génération du rapport HTML
                html_body = create_professional_system_html_with_trends(
                    system_name, current_data, stats, datetime.now().strftime('%Y-%m-%d'), trends_data
                )
                
                # Graphiques
                charts = []
                # Graphique de tendance
                if trends_data:
                    trend_chart = create_trend_chart(config['directory'], trends_data, system_name)
                    if trend_chart:
                        charts.append(trend_chart)
                
                # Envoi du rapport
                trend_indicator = "📈" if stats.error_trend < 0 else "📉" if stats.error_trend > 0 else "➡️"
                
                send_email_with_reports(
                    EMAIL_CONFIG['from_email'],
                    config['recipients'],
                    f"{config['icon']} {system_name} SYSTEM REPORT {trend_indicator} - {datetime.now().strftime('%Y-%m-%d')}",
                    html_body,
                    charts
                )
                
                print(f"   ✓ Rapport {system_name} envoyé")
                print(f"   📊 Statut: {stats.status}")
                print(f"   📈 Tendance: {stats.error_trend:+d} erreurs ({stats.improvement_rate:+.1f}%)")
            else:
                self.all_stats[system_name] = SystemStats(system_name)
                print(f"   ⚠ Aucune donnée {system_name} trouvée")
        else:
            self.all_stats[system_name] = SystemStats(system_name)
            print(f"   ⚠ Fichier {system_name} non trouvé")
    
    def run_with_trends(self):
        """Exécute le monitoring avec analyse de tendance"""
        print(f"=== GÉNÉRATION DES RAPPORTS AVEC ANALYSE DE TENDANCE ===")
        print(f"Démarrage: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Traiter tous les systèmes configurés
        for system_name, config in SYSTEMS_CONFIG.items():
            self.process_system(system_name, config)
        
        # Rapport de synthèse
        print("\n📊 Génération du rapport de synthèse...")
        if self.all_stats:
            summary_html = create_executive_summary_html_with_trends(
                self.systems_data, self.all_stats, datetime.now().strftime('%Y-%m-%d')
            )
            
            # Déterminer priorité
            critical_count = sum(1 for stats in self.all_stats.values() if stats.status == 'CRITICAL')
            improving_count = sum(1 for stats in self.all_stats.values() if stats.error_trend < 0)
            
            if critical_count > 0:
                priority = "🚨 URGENT"
            elif improving_count > 0:
                priority = "📈 IMPROVING"
            else:
                priority = "📊 MONITORING"
            
            send_email_with_reports(
                EMAIL_CONFIG['from_email'],
                EMAIL_CONFIG['summary_recipients'],
                f"{priority} - EXECUTIVE SUMMARY WITH TRENDS - {datetime.now().strftime('%Y-%m-%d')}",
                summary_html,
                []
            )
            print("   ✓ Rapport de synthèse envoyé")
        
        # Résumé final
        print(f"\n{'='*60}")
        print("📊 RÉSUMÉ AVEC ANALYSE DE TENDANCE:")
        print(f"{'='*60}")
        
        for system_name, stats in self.all_stats.items():
            status_icon = {'HEALTHY': '✅', 'WARNING': '⚠️', 'CRITICAL': '🚨', 'NO_DATA': '⚪'}[stats.status]
            trend_icon = '📈' if stats.error_trend < 0 else '📉' if stats.error_trend > 0 else '➡️'
            print(f"   {status_icon} {system_name}: {stats.total_errors} erreurs {trend_icon} ({stats.error_trend:+d})")
        
        print(f"\n✅ RAPPORTS AVEC ANALYSE DE TENDANCE GÉNÉRÉS!")
        print(f"⏰ Terminé: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")