from django.db import models
import uuid
from django.utils import timezone
from django.utils.text import slugify
import hashlib

#######################
# ErrorType Model
#######################
class ErrorType(models.Model):
    # ID automatique basé sur le système, service et erreur
    id = models.CharField(primary_key=True, max_length=255, editable=False)
    
    # Identification
    system_name = models.CharField(max_length=50, verbose_name="System Name")
    service_type = models.CharField(max_length=100, verbose_name="Service Type")
    service_name = models.CharField(max_length=100, verbose_name="Service Name")
    error_reason = models.TextField(verbose_name="Error Reason")
    
    # Catégorisation
    error_type = models.CharField(
        max_length=50, 
        choices=[('expected', 'Expected'), ('unexpected', 'Unexpected')], 
        default='unexpected', 
        verbose_name="Error Type"
    )
    error_category = models.CharField(
        max_length=50, 
        choices=[
            ('logic', 'Logic'), 
            ('performance', 'Performance'), 
            ('security', 'Security'), 
            ('integration', 'Integration'), 
            ('data', 'Data'), 
            ('configuration', 'Configuration')
        ], 
        verbose_name="Error Category",
        default='logic'
    )
    impact_level = models.CharField(
        max_length=20, 
        choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical')], 
        verbose_name="Impact Level",
        default='low'
    )

    # Contexte
    trigger_event = models.TextField(blank=True, verbose_name="Trigger Event")
    occurred_at = models.DateTimeField(verbose_name="Occurrence Timestamp", default='Unknown')
    source_component = models.CharField(max_length=100, blank=True, verbose_name="Source Component")
    
    # Données techniques
    code_erreur = models.CharField(max_length=50, blank=True, verbose_name="Error Code")
    fichiers_impactes = models.TextField(blank=True, verbose_name="Impacted Files/Modules")
    request_payload = models.JSONField(blank=True, null=True, verbose_name="Request Payload")
    stack_trace = models.TextField(blank=True, verbose_name="Stack Trace")
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Creation Date")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Last Updated")
    
    class Meta:
        verbose_name = "Error Type"
        verbose_name_plural = "Error Types"
        constraints = [
            models.UniqueConstraint(
                fields=['system_name', 'service_name', 'error_reason'], 
                name='unique_system_error_reason'
            )
        ]
    
    def save(self, *args, **kwargs):
        if not self.id:
            system_slug = slugify(self.system_name)
            service_slug = slugify(self.service_name)
            error_hash = hashlib.md5(self.error_reason.encode('utf-8')).hexdigest()[:6].upper()
            self.id = f"{system_slug}_{service_slug}_{error_hash}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.system_name} - {self.error_reason[:50]}"


#######################
# ErrorEvent Model
#######################
class ErrorEvent(models.Model):
    # For ErrorEvent, the id includes the system name, the date (yyyymmdd) and a unique suffix
    id = models.CharField(primary_key=True, max_length=255, editable=False)
    
    # Link to ErrorType to retrieve all events of a specific error type
    error_type = models.ForeignKey(
        ErrorType, 
        on_delete=models.CASCADE, 
        related_name='events', 
        verbose_name="Error Type"
    )
    
    # Also keep basic information, even if it is redundant with ErrorType, to facilitate searches or historical records
    system_name = models.CharField(max_length=50, verbose_name="System Name")
    service_type = models.CharField(max_length=100, verbose_name="Service Type")
    service_name = models.CharField(max_length=100, verbose_name="Service Name")
    error_reason = models.TextField(verbose_name="Error Reason")
    error_count = models.IntegerField(verbose_name="Error Count")
    
    timestamp = models.DateTimeField(default=timezone.now, verbose_name="Timestamp")
    
    # Additional Information
    inserted_by = models.CharField(max_length=50, verbose_name="Inserted by")
    notes = models.TextField(blank=True, null=True, verbose_name="Notes")
    
    class Meta:
        verbose_name = "Error Event"
        verbose_name_plural = "Error Events"
        ordering = ['-timestamp']
    
    def save(self, *args, **kwargs):
        if not self.id:
            system_slug = slugify(self.system_name)
            service_slug = slugify(self.service_name)
            date_str = self.timestamp.strftime('%Y%m%d%H%M%S') if self.timestamp else timezone.now().strftime('%Y%m%d%H%M%S')
            error_hash = hashlib.md5(self.error_reason.encode('utf-8')).hexdigest()[:6].upper()
            self.id = f"{system_slug}_{service_slug}_{error_hash}_{date_str}"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Error {self.id} - {self.timestamp.strftime('%d/%m/%Y %H:%M')}"

#######################
# ErrorTicket Model
#######################
class ErrorTicket(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    error_type = models.OneToOneField(
        'ErrorType', 
        on_delete=models.CASCADE, 
        related_name='ticket', 
        verbose_name="Error Type"
    )
    ticket_reference = models.CharField(max_length=255, editable=False, blank=True, null=True)
    
    PRIORITY_CHOICES = [
        ('P1', 'Critical'),
        ('P2', 'High'),
        ('P3', 'Normal'),
        ('P4', 'Low')
    ]
    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('IN_PROGRESS', 'In Progress'),
        ('PENDING', 'Pending'),
        ('RESOLVED', 'Resolved'),
        ('CLOSED', 'Closed')
    ]
    
    priorite = models.CharField(max_length=2, choices=PRIORITY_CHOICES, default="P3", verbose_name="Priority")
    statut = models.CharField(max_length=15, choices=STATUS_CHOICES, default="OPEN", verbose_name="Status")
    niveau_criticite = models.IntegerField(default=3, choices=[(i, str(i)) for i in range(1, 6)], verbose_name="Criticality Level (1-5)")
    
    symptomes = models.TextField(blank=True, verbose_name="Observed Symptoms")
    impact = models.TextField(blank=True, verbose_name="User Impact")
    services_affectes = models.TextField(blank=True, verbose_name="Affected Services")
    charge_systeme = models.IntegerField(blank=True, null=True, verbose_name="System Load")
    nombre_utilisateurs = models.IntegerField(blank=True, null=True, verbose_name="Impacted Users")
    
    cause_racine = models.TextField(blank=True, verbose_name="Root Cause")
    hypotheses = models.TextField(blank=True, verbose_name="Hypotheses")
    
    responsable = models.CharField(max_length=100, blank=True, verbose_name="Responsible")
    equipe = models.CharField(max_length=100, blank=True, verbose_name="Assigned Team")
    actions = models.TextField(blank=True, verbose_name="Planned Actions")
    solution = models.TextField(blank=True, verbose_name="Implemented Solution")
    
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name="Creation Date")
    date_modification = models.DateTimeField(auto_now=True, verbose_name="Last Modified")
    date_resolution = models.DateTimeField(null=True, blank=True, verbose_name="Resolution Date")
    
    commentaires = models.TextField(blank=True, verbose_name="Comments")
    historique = models.JSONField(default=dict, blank=True, verbose_name="Modification History")
    
    lessons_learned = models.TextField(blank=True, verbose_name="Lessons Learned")
    validation_responsable = models.BooleanField(default=False, verbose_name="Validated by Responsible")
    documented_knowledge_base = models.BooleanField(default=False, verbose_name="Documented in Knowledge Base")
    
    class Meta:
        verbose_name = "Error Ticket"
        verbose_name_plural = "Error Tickets"
    
    def save(self, *args, **kwargs):
        if not self.ticket_reference:
            type_id = slugify(self.error_type.id)
            self.ticket_reference = f"{type_id}"
        
        if self.statut == 'RESOLVED' and not self.date_resolution:
            self.date_resolution = timezone.now()
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Ticket: {self.error_type.system_name} [{self.get_statut_display()}]"
    
    def get_duration(self):
        end_date = self.date_resolution or timezone.now()
        duration = end_date - self.date_creation
        return round(duration.total_seconds() / 3600, 1)