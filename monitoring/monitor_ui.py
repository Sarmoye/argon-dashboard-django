import streamlit as st
import pandas as pd
import time

# Fonction pour lire le fichier CSV
def lire_csv(chemin_fichier):
    """
    Lit un fichier CSV et retourne son contenu sous forme de DataFrame.
    Gère les erreurs si le fichier n'est pas trouvé ou s'il y a un problème de lecture.

    Args:
        chemin_fichier (str): Le chemin du fichier CSV.

    Returns:
        pandas.DataFrame: Le contenu du fichier CSV, ou None en cas d'erreur.
    """
    try:
        df = pd.read_csv(chemin_fichier)
        return df
    except FileNotFoundError:
        st.error(f"Erreur: Le fichier CSV '{chemin_fichier}' n'a pas été trouvé.")
        return None
    except Exception as e:
        st.error(f"Erreur: Une erreur s'est produite lors de la lecture du fichier CSV '{chemin_fichier}': {e}")
        return None

# Fonction principale de l'application Streamlit
def main():
    """
    Fonction principale de l'application Streamlit.
    Lit et affiche le contenu du fichier CSV à intervalles réguliers.
    """
    st.title("Lecture et affichage de fichier CSV en temps réel")
    # Remplacez ceci par le chemin de votre fichier CSV
    chemin_fichier = "/srv/itsea_files/monitoring_files/status_log.csv"
    # Ajout d'un message d'information pour l'utilisateur
    st.info(f"L'application va lire et afficher le fichier CSV : `{chemin_fichier}`. Assurez-vous que le fichier existe et est accessible.")

    # Boucle infinie pour mettre à jour les données toutes les 30 minutes
    while True:
        df = lire_csv(chemin_fichier)
        if df is not None:  # Vérifie si la lecture du CSV a réussi
            st.header("Contenu du fichier CSV")
            st.dataframe(df)  # Affiche le DataFrame dans Streamlit

            # Calcul des statistiques (si le DataFrame n'est pas vide)
            if not df.empty:
                st.header("Statistiques des applications")
                # Compte le nombre d'applications par statut
                statut_counts = df['statut'].value_counts()
                st.write("Nombre d'applications par statut:")
                st.write(statut_counts)

                # Affiche un message si le fichier est vide.
            else:
                st.warning("Le fichier CSV est vide.")
        # Attend 30 minutes (1800 secondes) avant de relire le fichier
        time.sleep(1800)

if __name__ == "__main__":
    main()