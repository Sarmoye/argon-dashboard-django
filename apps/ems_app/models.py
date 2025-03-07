import uuid
from django.db import models
from django.utils import timezone


class ErrorType(models.Model):
    """
    Définition d'un type d'erreur unique pour un système.
    Chaque combinaison système/raison d'erreur n'existe qu'une seule fois.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    system_name = models.CharField(max_length=50, verbose_name="Nom du système")
    service_type = models.CharField(max_length=100, verbose_name="Type de service")
    service_name = models.CharField(max_length=100, verbose_name="Nom du service")
    error_reason = models.TextField(verbose_name="Raison de l'erreur")
    code_erreur = models.CharField(max_length=50, blank=True, verbose_name="Code d'erreur")
    
    # Documentation technique
    comportement_attendu = models.TextField(blank=True, verbose_name="Comportement attendu")
    correction_automatique = models.BooleanField(default=False, verbose_name="Correction automatique possible")
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Dernière mise à jour")
    
    class Meta:
        verbose_name = "Type d'erreur"
        verbose_name_plural = "Types d'erreurs"
        constraints = [
            models.UniqueConstraint(fields=['system_name', 'error_reason'], name='unique_system_error')
        ]
    
    def __str__(self):
        return f"{self.system_name}: {self.error_reason[:50]}"


class ErrorEvent(models.Model):
    """
    Enregistrement d'une occurrence spécifique d'erreur.
    Remplace le modèle SourceData1 original.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    error_type = models.ForeignKey(ErrorType, on_delete=models.CASCADE, related_name='events', verbose_name="Type d'erreur")
    reference_id = models.CharField(max_length=50, unique=True, blank=True, verbose_name="Identifiant unique")
    
    # Détails de l'événement
    error_count = models.IntegerField(verbose_name="Nombre d'erreurs")
    timestamp = models.DateTimeField(default=timezone.now, verbose_name="Horodatage")
    domain = models.CharField(max_length=100, verbose_name="Domaine")
    logs = models.TextField(blank=True, verbose_name="Messages de logs")
    version_system = models.CharField(max_length=50, blank=True, verbose_name="Version du système")
    
    # Informations complémentaires
    inserted_by = models.CharField(max_length=50, verbose_name="Enregistré par")
    notes = models.TextField(blank=True, null=True, verbose_name="Notes")
    
    class Meta:
        verbose_name = "Événement d'erreur"
        verbose_name_plural = "Événements d'erreurs"
        ordering = ['-timestamp']
    
    def save(self, *args, **kwargs):
        if not self.reference_id:
            system = self.error_type.system_name
            self.reference_id = f"{system}_{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Erreur {self.reference_id} - {self.timestamp.strftime('%d/%m/%Y %H:%M')}"


class ErrorTicket(models.Model):
    """
    Ticket de suivi et résolution pour un type d'erreur.
    Remplace le modèle FicheErreur original avec une structure optimisée.
    """
    # Clés et références
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    error_type = models.OneToOneField(ErrorType, on_delete=models.CASCADE, related_name='ticket', verbose_name="Type d'erreur")
    
    # États et priorités
    PRIORITY_CHOICES = [
        ('P1', 'Critique'),
        ('P2', 'Haute'),
        ('P3', 'Normale'),
        ('P4', 'Basse')
    ]
    
    STATUS_CHOICES = [
        ('OPEN', 'Ouvert'),
        ('IN_PROGRESS', 'En cours'),
        ('PENDING', 'En attente'),
        ('RESOLVED', 'Résolu'),
        ('CLOSED', 'Fermé')
    ]
    
    priorite = models.CharField(max_length=2, choices=PRIORITY_CHOICES, default="P3", verbose_name="Priorité")
    statut = models.CharField(max_length=15, choices=STATUS_CHOICES, default="OPEN", verbose_name="Statut")
    niveau_criticite = models.IntegerField(default=3, choices=[(i, str(i)) for i in range(1, 6)], verbose_name="Criticité (1-5)")
    
    # Analyse de l'erreur
    symptomes = models.TextField(blank=True, verbose_name="Symptômes observés")
    impact = models.TextField(blank=True, verbose_name="Impact utilisateur")
    services_affectes = models.TextField(blank=True, verbose_name="Services affectés")
    nombre_utilisateurs = models.IntegerField(blank=True, null=True, verbose_name="Utilisateurs impactés")
    
    # Analyse et diagnostic
    cause_racine = models.TextField(blank=True, verbose_name="Cause racine")
    hypotheses = models.TextField(blank=True, verbose_name="Hypothèses")
    
    # Résolution
    responsable = models.CharField(max_length=100, blank=True, verbose_name="Responsable")
    equipe = models.CharField(max_length=100, blank=True, verbose_name="Équipe assignée")
    actions = models.TextField(blank=True, verbose_name="Actions prévues")
    solution = models.TextField(blank=True, verbose_name="Solution implémentée")
    
    # Suivi temporel
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    date_modification = models.DateTimeField(auto_now=True, verbose_name="Dernière modification")
    date_resolution = models.DateTimeField(null=True, blank=True, verbose_name="Date de résolution")
    
    # Commentaires et historique
    commentaires = models.TextField(blank=True, verbose_name="Commentaires")
    historique = models.JSONField(default=dict, blank=True, verbose_name="Historique des modifications")
    
    class Meta:
        verbose_name = "Ticket d'erreur"
        verbose_name_plural = "Tickets d'erreurs"
    
    def __str__(self):
        return f"Ticket: {self.error_type.system_name} [{self.get_statut_display()}]"
    
    def save(self, *args, **kwargs):
        # Mettre à jour la date de résolution si le statut passe à "Résolu"
        if self.statut == 'RESOLVED' and not self.date_resolution:
            self.date_resolution = timezone.now()
        super().save(*args, **kwargs)
    
    def get_duration(self):
        """Retourne la durée du ticket en heures"""
        end_date = self.date_resolution or timezone.now()
        duration = end_date - self.date_creation
        return round(duration.total_seconds() / 3600, 1)