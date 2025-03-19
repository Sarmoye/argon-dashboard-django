from django.db import models
import uuid
from django.utils import timezone
from django.utils.text import slugify
import hashlib

#######################
# ErrorType Model
#######################
class ErrorType(models.Model):
    # For ErrorType, the id is a CharField that combines the system name and a short hash of the error reason
    id = models.CharField(primary_key=True, max_length=255, editable=False)
    
    # Identification
    system_name = models.CharField(max_length=50, verbose_name="System Name")
    service_type = models.CharField(max_length=100, verbose_name="Service Type")
    service_name = models.CharField(max_length=100, verbose_name="Service Name")
    error_reason = models.TextField(verbose_name="Error Reason")
    
    # Technical Information
    code_erreur = models.CharField(max_length=50, blank=True, verbose_name="Error Code")
    fichiers_impactes = models.TextField(blank=True, verbose_name="Impacted Files/Modules")
    
    # Additional Suggestions
    logs = models.TextField(blank=True, verbose_name="Log Messages")
    description_technique = models.TextField(blank=True, verbose_name="Detailed Technical Description")
    comportement_attendu = models.TextField(blank=True, verbose_name="Expected Behavior")
    procedures_contournement = models.TextField(blank=True, verbose_name="Workaround Procedures")
    environnement = models.CharField(max_length=100, blank=True, verbose_name="Environment (OS, version, etc.)")
    niveau_severite = models.PositiveSmallIntegerField(blank=True, null=True, verbose_name="Severity Level (1-5)")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Creation Date")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Last Updated")
    
    class Meta:
        verbose_name = "Error Type"
        verbose_name_plural = "Error Types"
        constraints = [
            models.UniqueConstraint(
                fields=['system_name', 'service_name', 'error_reason'], 
                name='1unique_system_error_reason'
            )
        ]
    
    def save(self, *args, **kwargs):
        if not self.id:
            # Create an id by combining a slugified version of the system name with a short hash of the error
            system_slug = slugify(self.system_name)
            service_slug = slugify(self.service_name)
            error_hash = hashlib.md5(self.error_reason.encode('utf-8')).hexdigest()[:6].upper()
            self.id = f"{system_slug}_{service_slug}_{error_hash}"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.system_name}: {self.error_reason[:50]}"

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
            date_str = self.date_creation.strftime('%Y%m%d%H%M%S') if self.date_creation else timezone.now().strftime('%Y%m%d%H%M%S')
            error_hash = hashlib.md5(self.error_reason.encode('utf-8')).hexdigest()[:6].upper()
            self.id = f"{system_slug}_{service_slug}_{error_hash}_{date_str}"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Error {self.id} - {self.timestamp.strftime('%d/%m/%Y %H:%M')}"

#######################
# ErrorTicket Model
#######################
class ErrorTicket(models.Model):
    # Primary key maintained as UUID
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # One-to-One association with ErrorType
    error_type = models.OneToOneField(
        ErrorType, 
        on_delete=models.CASCADE, 
        related_name='ticket', 
        verbose_name="Error Type"
    )
    
    # New reference field for traceability
    ticket_reference = models.CharField(max_length=255, editable=False, blank=True, null=True)
    
    # States and Priorities
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
    
    # Error Analysis
    symptomes = models.TextField(blank=True, verbose_name="Observed Symptoms")
    impact = models.TextField(blank=True, verbose_name="User Impact")
    services_affectes = models.TextField(blank=True, verbose_name="Affected Services")
    charge_systeme = models.IntegerField(blank=True, null=True, verbose_name="System Load")
    nombre_utilisateurs = models.IntegerField(blank=True, null=True, verbose_name="Impacted Users")
    
    # Analysis and Diagnosis
    cause_racine = models.TextField(blank=True, verbose_name="Root Cause")
    hypotheses = models.TextField(blank=True, verbose_name="Hypotheses")
    
    # Resolution
    responsable = models.CharField(max_length=100, blank=True, verbose_name="Responsible")
    equipe = models.CharField(max_length=100, blank=True, verbose_name="Assigned Team")
    actions = models.TextField(blank=True, verbose_name="Planned Actions")
    solution = models.TextField(blank=True, verbose_name="Implemented Solution")
    
    # Time Tracking
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name="Creation Date")
    date_modification = models.DateTimeField(auto_now=True, verbose_name="Last Modified")
    date_resolution = models.DateTimeField(null=True, blank=True, verbose_name="Resolution Date")
    
    # Comments and History
    commentaires = models.TextField(blank=True, verbose_name="Comments")
    historique = models.JSONField(default=dict, blank=True, verbose_name="Modification History")
    
    class Meta:
        verbose_name = "Error Ticket"
        verbose_name_plural = "Error Tickets"
    
    def save(self, *args, **kwargs):
        # Generate the ticket_reference if not defined
        if not self.ticket_reference:
            system_slug = slugify(self.error_type.system_name)
            service_slug = slugify(self.error_type.service_name)
            error_hash = hashlib.md5(self.error_reason.encode('utf-8')).hexdigest()[:6].upper()
            self.ticket_reference = f"{system_slug}_{service_slug}_{error_hash}"
        
        # Manage the resolution date
        if self.statut == 'RESOLVED' and not self.date_resolution:
            self.date_resolution = timezone.now()
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Ticket: {self.error_type.system_name} [{self.get_statut_display()}]"
    
    def get_duration(self):
        end_date = self.date_resolution or timezone.now()
        duration = end_date - self.date_creation
        return round(duration.total_seconds() / 3600, 1)