import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import time
import altair as alt

# Configuration de la page
st.set_page_config(
    page_title="Tableau de Bord de Disponibilité",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Personnalisation CSS pour améliorer l'apparence
st.markdown("""
<style>
    .main {
        background-color: #f5f7f9;
    }
    .stApp {
        max-width: 1200px;
        margin: 0 auto;
    }
    .dashboard-title {
        color: #1E3A8A;
        text-align: center;
        padding: 20px 0;
        margin-bottom: 20px;
        border-bottom: 2px solid #E5E7EB;
    }
    .status-card {
        background-color: white;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 20px;
    }
    .last-update {
        color: #6B7280;
        text-align: right;
        font-size: 12px;
        margin-top: 5px;
    }
    .alert-success {
        background-color: #D1FAE5;
        border-left: 5px solid #10B981;
        padding: 15px;
        border-radius: 5px;
    }
    .alert-warning {
        background-color: #FEF3C7;
        border-left: 5px solid #F59E0B;
        padding: 15px;
        border-radius: 5px;
    }
    .alert-danger {
        background-color: #FEE2E2;
        border-left: 5px solid #EF4444;
        padding: 15px;
        border-radius: 5px;
    }
    .metric-card {
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        text-align: center;
    }
    .metric-value {
        font-size: 28px;
        font-weight: bold;
    }
    .metric-label {
        font-size: 14px;
        color: #6B7280;
    }
    .chart-container {
        background-color: white;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    /* Styliser le tableau */
    .dataframe-container {
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    /* Barre de navigation */
    .sidebar .sidebar-content {
        background-color: #1E293B;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# Fonction pour lire le fichier CSV
def lire_csv(chemin_fichier):
    """
    Lit un fichier CSV et retourne son contenu sous forme de DataFrame.
    Gère les erreurs si le fichier n'est pas trouvé ou s'il y a un problème de lecture.
    """
    try:
        df = pd.read_csv(chemin_fichier)
        # Si le DataFrame contient une colonne de dates, la convertir au format datetime
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    except FileNotFoundError:
        st.error(f"Erreur: Le fichier CSV '{chemin_fichier}' n'a pas été trouvé.")
        return None
    except Exception as e:
        st.error(f"Erreur: Une erreur s'est produite lors de la lecture du fichier CSV '{chemin_fichier}': {e}")
        return None

# Fonction pour créer un style basé sur le statut
def style_status(val):
    if val == 'Online':
        return 'background-color: #D1FAE5; color: #065F46; font-weight: bold'
    elif val == 'Warning':
        return 'background-color: #FEF3C7; color: #92400E; font-weight: bold'
    elif val == 'Offline':
        return 'background-color: #FEE2E2; color: #B91C1C; font-weight: bold'
    else:
        return ''

# Fonction pour créer les métriques principales
def create_metrics(df):
    if df is None or df.empty:
        return
        
    col1, col2, col3 = st.columns(3)
    
    # Calculer les métriques
    total_apps = len(df['application'].unique())
    
    # Calculer le nombre d'applications par statut
    status_counts = df['statut'].value_counts().to_dict()
    online_count = status_counts.get('Online', 0)
    warning_count = status_counts.get('Warning', 0)
    offline_count = status_counts.get('Offline', 0)
    
    # Calculer le taux de disponibilité
    availability_rate = (online_count / total_apps) * 100 if total_apps > 0 else 0
    
    with col1:
        st.markdown("""
        <div class="metric-card" style="background-color: #D1FAE5;">
            <div class="metric-value" style="color: #065F46;">{}</div>
            <div class="metric-label">Applications en ligne</div>
        </div>
        """.format(online_count), unsafe_allow_html=True)
        
    with col2:
        st.markdown("""
        <div class="metric-card" style="background-color: #FEF3C7;">
            <div class="metric-value" style="color: #92400E;">{}</div>
            <div class="metric-label">Applications en avertissement</div>
        </div>
        """.format(warning_count), unsafe_allow_html=True)
        
    with col3:
        st.markdown("""
        <div class="metric-card" style="background-color: #FEE2E2;">
            <div class="metric-value" style="color: #B91C1C;">{}</div>
            <div class="metric-label">Applications hors ligne</div>
        </div>
        """.format(offline_count), unsafe_allow_html=True)
    
    # Créer une barre de progression pour le taux de disponibilité
    st.markdown("### Taux de disponibilité global")
    progress_color = "#10B981" if availability_rate >= 90 else "#F59E0B" if availability_rate >= 70 else "#EF4444"
    
    st.markdown(f"""
    <div style="margin: 10px 0;">
        <div style="background-color: #E5E7EB; border-radius: 10px; height: 20px; width: 100%;">
            <div style="background-color: {progress_color}; width: {availability_rate}%; height: 20px; border-radius: 10px; text-align: center; color: white; line-height: 20px; font-size: 12px;">
                {availability_rate:.1f}%
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Fonction pour créer les graphiques
def create_charts(df):
    if df is None or df.empty:
        return
        
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.subheader("Répartition des statuts")
        
        # Graphique en secteurs (pie chart) pour les statuts
        status_counts = df['statut'].value_counts().reset_index()
        status_counts.columns = ['statut', 'count']
        
        # Définir des couleurs pour chaque statut
        colors = {'Online': '#10B981', 'Warning': '#F59E0B', 'Offline': '#EF4444'}
        
        # Créer le graphique avec Plotly
        fig = px.pie(
            status_counts, 
            names='statut', 
            values='count',
            color='statut',
            color_discrete_map=colors,
            hole=0.4
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(margin=dict(t=30, b=0, l=0, r=0), height=300)
        
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.subheader("Applications par catégorie")
        
        # Si une colonne 'categorie' existe, créer un graphique à barres
        if 'categorie' in df.columns:
            category_status = df.groupby(['categorie', 'statut']).size().reset_index(name='count')
            
            fig = px.bar(
                category_status,
                x='categorie',
                y='count',
                color='statut',
                color_discrete_map=colors,
                barmode='stack'
            )
            fig.update_layout(margin=dict(t=30, b=0, l=0, r=0), height=300)
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            # Afficher un autre graphique si la colonne 'categorie' n'existe pas
            app_status = df.groupby('application')['statut'].first().reset_index()
            
            # Tri par statut
            status_order = {'Offline': 0, 'Warning': 1, 'Online': 2}
            app_status['status_order'] = app_status['statut'].map(status_order)
            app_status = app_status.sort_values('status_order')
            
            # Créer un graphique à barres horizontales
            fig = px.bar(
                app_status,
                y='application',
                x=[1] * len(app_status),  # Chaque barre a la même longueur
                color='statut',
                color_discrete_map=colors,
                orientation='h'
            )
            fig.update_layout(
                showlegend=True,
                xaxis={'visible': False},
                margin=dict(t=30, b=0, l=0, r=0),
                height=min(300, 30 * len(app_status.index) + 50)  # Hauteur dynamique selon le nombre d'applications
            )
            
            st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

# Fonction pour afficher la liste des applications avec leur statut
def display_app_status_table(df):
    if df is None or df.empty:
        return
        
    st.markdown('<div class="status-card">', unsafe_allow_html=True)
    st.subheader("État détaillé des applications")
    
    # Préparation des données pour l'affichage
    status_df = df[['application', 'statut']].copy()
    if 'timestamp' in df.columns:
        status_df['dernière_mise_à_jour'] = df['timestamp']
    if 'description' in df.columns:
        status_df['description'] = df['description']
        
    # Application du style et affichage
    st.markdown('<div class="dataframe-container">', unsafe_allow_html=True)
    st.dataframe(
        status_df.style.map(
            lambda x: style_status(x), 
            subset=['statut']
        ),
        hide_index=True,
        use_container_width=True
    )
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# Fonction pour afficher les alertes
def display_alerts(df):
    if df is None or df.empty:
        return
        
    # Filtrer les applications avec des problèmes
    problematic_apps = df[df['statut'] != 'Online']
    
    if not problematic_apps.empty:
        st.markdown('<div class="status-card">', unsafe_allow_html=True)
        st.subheader("⚠️ Alertes actives")
        
        for _, app in problematic_apps.iterrows():
            status_class = "alert-warning" if app['statut'] == 'Warning' else "alert-danger"
            st.markdown(f"""
            <div class="{status_class}">
                <strong>{app['application']}</strong> - {app['statut']}
                {f"<br><small>{app['description']}</small>" if 'description' in app and not pd.isna(app['description']) else ""}
            </div>
            """, unsafe_allow_html=True)
            
        st.markdown('</div>', unsafe_allow_html=True)

# Fonction principale de l'application Streamlit
def main():
    # Sidebar pour les options de configuration
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/6295/6295417.png", width=80)
        st.title("Options")
        
        # Chemin du fichier CSV
        chemin_fichier = st.text_input(
            "Chemin du fichier CSV",
            value="/srv/itsea_files/monitoring_files/status_log.csv"
        )
        
        # Intervalle de rafraîchissement
        refresh_interval = st.slider(
            "Intervalle de rafraîchissement (secondes)",
            min_value=30,
            max_value=3600,
            value=1800,
            step=30
        )
        
        st.info("Le tableau de bord sera automatiquement mis à jour selon l'intervalle choisi.")
        
        # Afficher des informations système
        st.subheader("Informations système")
        st.markdown(f"**Date actuelle:** {datetime.now().strftime('%d-%m-%Y')}")
        st.markdown(f"**Heure:** {datetime.now().strftime('%H:%M:%S')}")

    # Titre principal
    st.markdown('<h1 class="dashboard-title">Tableau de Bord de Disponibilité des Applications</h1>', unsafe_allow_html=True)
    
    # Initialiser la variable pour afficher la dernière mise à jour
    placeholder_last_update = st.empty()
    
    # Boucle de mise à jour
    while True:
        # Lire les données
        df = lire_csv(chemin_fichier)
        
        # Mettre à jour l'affichage de la dernière mise à jour
        placeholder_last_update.markdown(
            f'<p class="last-update">Dernière mise à jour: {datetime.now().strftime("%d-%m-%Y %H:%M:%S")}</p>',
            unsafe_allow_html=True
        )
        
        if df is not None and not df.empty:
            # Créer les métriques principales
            create_metrics(df)
            
            # Afficher les alertes
            display_alerts(df)
            
            # Créer les graphiques
            create_charts(df)
            
            # Afficher le tableau détaillé
            display_app_status_table(df)
        else:
            st.warning("Aucune donnée n'est disponible. Veuillez vérifier le chemin du fichier CSV.")
            
        # Attendre avant la prochaine mise à jour
        # Utiliser st.spinner pour indiquer que le dashboard attend la prochaine mise à jour
        with st.spinner(f"Prochaine mise à jour dans {refresh_interval} secondes..."):
            time.sleep(refresh_interval)
            st.experimental_rerun()

if __name__ == "__main__":
    main()