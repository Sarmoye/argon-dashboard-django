#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import warnings
warnings.filterwarnings('ignore')

from datetime import datetime
from core.monitoring_engine import MonitoringEngine
import matplotlib.pyplot as plt
import seaborn as sns

def main():
    """Fonction principale"""
    try:
        # Configuration matplotlib
        plt.style.use('default')
        sns.set_palette("husl")
        
        # Création et exécution du moteur de monitoring
        engine = MonitoringEngine()
        engine.run_with_trends()
        
    except Exception as e:
        print(f"❌ ERREUR CRITIQUE: {e}")
        print("Contactez l'équipe technique immédiatement!")

if __name__ == "__main__":
    main()