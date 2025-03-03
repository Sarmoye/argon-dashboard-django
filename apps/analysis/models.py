from django.db import models
from apps.sources_data_app.models import SourceData

# Create your models here.
class FicheErreur(models.Model):
    source_data = models.OneToOneField(SourceData, on_delete=models.CASCADE)
    system_name = models.CharField(max_length=50)
    service_type = models.CharField(max_length=100)
    service_name = models.CharField(max_length=100)
    error_count = models.IntegerField()
    error_reason = models.TextField()
    timestamp = models.DateTimeField(blank=True)
    priorite = models.CharField(max_length=50, default="Normale")
    statut = models.CharField(max_length=50, default="Ouvert")
    symptomes_observes = models.TextField(blank=True)
    logs_messages = models.TextField(blank=True)
    gravite = models.CharField(max_length=50, default="Moyenne")
    services_affectes = models.TextField(blank=True)
    cause = models.TextField(blank=True)
    hypotheses = models.TextField(blank=True)
    prochaines_actions = models.TextField(blank=True)
    responsable_resolution = models.CharField(max_length=100, blank=True)
    commentaires = models.TextField(blank=True)

    # Nouvelles suggestions de champs
    type_erreur = models.CharField(max_length=100, blank=True)  # Type d'erreur
    impact_utilisateur = models.CharField(max_length=100, blank=True)  # Impact sur les utilisateurs
    statut_resolution = models.CharField(max_length=50, default="Non commencé")  # Statut de la résolution
    historique_actions = models.TextField(blank=True)  # Historique des actions entreprises
    equipe_responsable = models.CharField(max_length=100, blank=True)  # Équipe responsable
    priorite_numerique = models.IntegerField(default=5)  # Priorité numérique
    frequence = models.CharField(max_length=50, blank=True)  # Fréquence de l'erreur
    automatisation_possible = models.BooleanField(default=False)  # Diagnostic/correction automatique
    version_systeme = models.CharField(max_length=50, blank=True)  # Version du système
    comportement_attendu = models.TextField(blank=True)  # Comportement attendu
    comportement_observe = models.TextField(blank=True)  # Comportement observé

    # Suivi des délais
    delai_resolution = models.DurationField(blank=True, null=True)  # Durée estimée pour résoudre
    delai_ecoule = models.DurationField(blank=True, null=True)  # Temps écoulé depuis détection

    # Impact et gravité
    impact_financier = models.IntegerField(blank=True, null=True)  # Impact financier
    nombre_utilisateurs_impactes = models.IntegerField(blank=True, null=True)  # Nombre d’utilisateurs touchés
    zone_geographique_affectee = models.CharField(max_length=100, blank=True)  # Zone affectée

    # Catégorisation et évaluation
    categorie_erreur = models.CharField(max_length=50, blank=True)  # Catégorie de l’erreur
    niveau_criticite = models.IntegerField(default=3)  # Criticité (1-5)
    etape_detection = models.CharField(max_length=100, blank=True)  # Étape de détection

    # Collaboration
    notifications_envoyees = models.BooleanField(default=False)  # Parties informées
    canaux_communication = models.CharField(max_length=100, blank=True)  # Canaux utilisés
    parties_prenantes = models.TextField(blank=True)  # Parties prenantes impliquées

    # Suivi des solutions
    solution_proposee = models.TextField(blank=True)  # Solution initiale
    solution_implantee = models.TextField(blank=True)  # Solution mise en œuvre
    efficacite_solution = models.IntegerField(blank=True, null=True)  # Score d'efficacité
    tests_effectues = models.TextField(blank=True)  # Tests pour vérifier la solution

    # Évolutivité et gestion des données
    timestamp_modification = models.DateTimeField(auto_now=True)  # Dernière modification
    precedent_incidents_similaires = models.TextField(blank=True)  # Erreurs similaires
    resolution_automatique_possible = models.BooleanField(default=False)  # Automatisation future

    # Audit et conformité
    audit_log = models.TextField(blank=True)  # Journal des modifications
    documentation_associee = models.TextField(blank=True)  # Références documentaires

    # Informations techniques
    code_erreur = models.CharField(max_length=50, blank=True)  # Code d’erreur
    fichiers_impactes = models.TextField(blank=True)  # Fichiers/modules impactés
    charge_systeme = models.IntegerField(blank=True, null=True)  # Charge système

    # Analystes travaillant sur la fiche
    analysts = models.TextField(blank=True)  # Liste des analystes

    # Champ pour les erreurs normales
    erreur_normale = models.BooleanField(default=False)  # Erreur normale sans impact réel

    def __str__(self):
        return f"Fiche Erreur: {self.source_data.unique_identifier}"