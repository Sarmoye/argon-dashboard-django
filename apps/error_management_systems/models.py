import uuid
from django.db import models
from django.db.models import UniqueConstraint, Index
from django.utils import timezone
from django.core.exceptions import ValidationError

SYSTEM_CLASSIFICATION_CHOICES = [
    ('A', 'A'),
    ('B', 'B'),
    ('C', 'C'),
    ('D', 'D')
]

SERVICE_CLASSIFICATION_CHOICES = [
    ('primary', 'Primary Service'),
    ('secondary', 'Secondary Service'),
    ('tertiary', 'Tertiary Service'),
    ('external', 'External Service'),
]

class System(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Nom du Système")
    system_classification = models.CharField(
        max_length=1,
        choices=SYSTEM_CLASSIFICATION_CHOICES,
        verbose_name="Classification du Système",
        blank=True,
        null=True
    )
    description = models.TextField(blank=True, verbose_name="Description du Système")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name

class Service(models.Model):
    system = models.ForeignKey(
        System, 
        on_delete=models.CASCADE,
        related_name="services",
        verbose_name="Système"
    )
    name = models.CharField(max_length=100, verbose_name="Nom du Service")
    service_classification = models.CharField(
        max_length=50, 
        choices=SERVICE_CLASSIFICATION_CHOICES,
        verbose_name="Classification du Service",
        blank=True,
        null=True
    )
    description = models.TextField(blank=True, verbose_name="Description du Service")
    owner = models.CharField(max_length=100, blank=True, null=True, verbose_name="Responsable du Service")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        unique_together = ('name', 'system')  # Ensures uniqueness at DB level

    def clean(self):
        if Service.objects.filter(name=self.name, system=self.system).exclude(id=self.id).exists():
            raise ValidationError(f"Service '{self.name}' already exists in system '{self.system}'.")
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.system.name} - {self.name}"

class ErrorCategory(models.Model):
    """
    Centralized error category management
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True, db_index=True)
    description = models.TextField(blank=True)
    severity_level = models.IntegerField(
        choices=[
            (1, 'Low'),
            (2, 'Medium'),
            (3, 'High'),
            (4, 'Critical')
        ],
        default=2
    )

    def __str__(self):
        return self.name


class ErrorType(models.Model):
    """
    Comprehensive Error Type Model with Enhanced Tracking
    """
    # Unique Identifier
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Indexed Fields for Performance
    system = models.ForeignKey(
        System,
        on_delete=models.PROTECT,
        related_name='error_types',
        verbose_name="System"
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.PROTECT,
        related_name='error_types',
        verbose_name="Service"
    )
    
    # Foreign Key with Protected Deletion
    category = models.ForeignKey(
        ErrorCategory, 
        on_delete=models.PROTECT,
        related_name='error_types',
        verbose_name="Error Category"
    )
    
    # Error Identification
    error_code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True
    )

    error_description = models.TextField()
    
    # Logging and Flexibility
    error_metadata = models.JSONField(
        blank=True,
        null=True,
        verbose_name="Detailed Error Metadata"
    )

    # Root Cause Analysis and Detection
    root_cause = models.TextField(blank=True, verbose_name="Root Cause Analysis")

    detected_by = models.CharField(
        max_length=100,
        choices=[
            ('monitoring', 'Monitoring System'),
            ('logs', 'Log Analysis'),
            ('user_report', 'User Report'),
            ('automated_test', 'Automated Test'),
            ('other', 'Other'),
        ],
        default='logs',
        verbose_name="Detected By"
    )

    error_source = models.CharField(
        max_length=100,
        choices=[
            ('internal', 'Internal'),
            ('external', 'External'),
            ('third_party', 'Third-Party Service'),
        ],
        default='internal',
        verbose_name="Error Source"
    )
    
    # Dependency and Traceability
    dependency_chain = models.JSONField(blank=True, null=True, verbose_name="Service Dependencies")
    
    # Error Occurrence Tracking
    first_occurrence = models.DateTimeField(auto_now_add=True)
    last_occurrence = models.DateTimeField(auto_now=True)
    total_occurrences = models.PositiveIntegerField(default=1)
    
    # Performance and Tracking Fields
    is_active = models.BooleanField(default=True, db_index=True)
    
    class Meta:
        # Unique Constraints
        constraints = [
            UniqueConstraint(
                fields=['system', 'service', 'error_code'], 
                name='unique_error_type'
            )
        ]
        
        # Database Indexing
        indexes = [
            Index(fields=['system', 'service']),
            Index(fields=['first_occurrence']),
            Index(fields=['last_occurrence'])
        ]
    
    def save(self, *args, **kwargs):
        # Ensure error code is unique
        if not self.error_code:
            self.error_code = self._generate_unique_error_code()
        
        super().save(*args, **kwargs)
    
    def _generate_unique_error_code(self):
        """
        Generate a unique error code with counter if needed
        """
        base_code = f"{self.system.name[:3]}_{self.service.name[:3]}_{uuid.uuid4().hex[:6]}"
        counter = 1
        
        while ErrorType.objects.filter(error_code=base_code).exists():
            base_code = f"{self.system.name[:3]}_{self.service.name[:3]}_{uuid.uuid4().hex[:6]}_{counter}"
            counter += 1
        
        return base_code.upper()
    
    def increment_occurrence(self):
        """
        Increment total occurrences and update last occurrence
        """
        self.total_occurrences += 1
        self.last_occurrence = timezone.now()
        self.save()
    
    def __str__(self):
        return f"{self.system.name} - {self.error_code}"


class ErrorEvent(models.Model):
    """
    Detailed Error Event Tracking
    """
    # Unique Identifier
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Protected Foreign Key
    error_type = models.ForeignKey(ErrorType, on_delete=models.PROTECT, related_name='events', verbose_name="Associated Error Type")
    
    # Indexed Fields
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    system = models.ForeignKey(
        System,
        on_delete=models.PROTECT,
        related_name='error_events',
        verbose_name="System"
    )
    
    service = models.ForeignKey(
        Service,
        on_delete=models.PROTECT,
        related_name='error_events',
        verbose_name="Service"
    )
    
    # Comprehensive Logging
    event_log = models.TextField(blank=True, verbose_name="Messages de logs")
    
    # Error Context
    source_ip = models.CharField(blank=True, null=True, verbose_name="Source IP Address")

    trigger_event = models.TextField(blank=True, verbose_name="Trigger Event")
    
    # Error Count and Tracking
    error_count = models.PositiveIntegerField(default=1)

    # New Enhanced Fields
    environment = models.CharField(
        max_length=50, 
        choices=[
            ('development', 'Development'),
            ('staging', 'Staging'),
            ('production', 'Production'),
            ('testing', 'Testing')
        ],
        default='production',
        verbose_name="Environment"
    )
    
    class Meta:
        # Unique Constraints
        constraints = [
            UniqueConstraint(
                fields=['error_type', 'timestamp', 'system', 'service'], 
                name='unique_error_event'
            )
        ]
        
        # Database Indexing
        indexes = [
            Index(fields=['timestamp', 'system']),
            Index(fields=['source_ip'])
        ]
    
    def save(self, *args, **kwargs):
        # Validate before saving
        self.full_clean()
        
        # Update associated error type
        self.error_type.increment_occurrence()
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Error Event: {self.error_type.error_code} at {self.timestamp}"


class ErrorTicket(models.Model):
    """
    Comprehensive Error Ticket Management Model
    """
    # Unique Identifiers
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket_number = models.CharField(
        max_length=50, 
        unique=True, 
        db_index=True
    )
    
    # Foreign Key Relationships with Protected Deletion
    error_type = models.ForeignKey(
        'ErrorType', 
        on_delete=models.PROTECT,
        related_name='tickets',
        verbose_name="Associated Error Type"
    )
    
    # Status and Priority Management
    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('IN_PROGRESS', 'In Progress'),
        ('PENDING', 'Pending'),
        ('RESOLVED', 'Resolved'),
        ('CLOSED', 'Closed'),
        ('BLOCKED', 'Blocked')
    ]
    
    PRIORITY_CHOICES = [
        ('P1', 'Critical - Immediate Action Required'),
        ('P2', 'High - Urgent Resolution'),
        ('P3', 'Medium - Normal Priority'),
        ('P4', 'Low - Minor Impact')
    ]
    
    # Indexed Status and Priority Fields
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='OPEN',
        db_index=True
    )
    priority = models.CharField(
        max_length=20, 
        choices=PRIORITY_CHOICES, 
        default='P3',
        db_index=True
    )
    
    # Comprehensive Ticket Metadata
    title = models.CharField(max_length=255)
    description = models.TextField()
    
    # Advanced Tracking Fields
    assigned_to = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        db_index=True
    )
    assigned_team = models.CharField(
        max_length=100, 
        blank=True, 
        null=True
    )
    
    # Timestamps with Indexing
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    # Flexible Metadata Storage
    ticket_metadata = models.JSONField(
        blank=True, 
        null=True, 
        verbose_name="Additional Ticket Metadata"
    )
    
    # Impact and Business Context
    business_impact = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name="Estimated Business Impact"
    )
    impacted_services = models.TextField(
        blank=True, 
        verbose_name="Impacted Services/Systems"
    )
    
    # Resolution and Root Cause
    root_cause = models.TextField(
        blank=True, 
        verbose_name="Root Cause Analysis"
    )
    resolution_details = models.TextField(
        blank=True, 
        verbose_name="Resolution Details"
    )
    
    # Compliance and Tracking
    compliance_checked = models.BooleanField(default=False)
    regulatory_impact = models.CharField(
        max_length=100, 
        blank=True, 
        choices=[
            ('gdpr', 'GDPR'),
            ('hipaa', 'HIPAA'),
            ('pci', 'PCI DSS'),
            ('sox', 'SOX'),
            ('none', 'No Specific Regulation')
        ]
    )
    
    # Audit and History
    modification_history = models.JSONField(
        default=list, 
        blank=True, 
        verbose_name="Ticket Modification History"
    )

    estimated_downtime = models.DurationField(
        null=True, 
        blank=True, 
        verbose_name="Estimated Downtime"
    )

    # Enhanced Remediation Fields
    remediation_complexity = models.CharField(
        max_length=50,
        choices=[
            ('low', 'Low - Simple Fix'),
            ('medium', 'Medium - Moderate Effort'),
            ('high', 'High - Complex Resolution'),
            ('critical', 'Critical - Comprehensive Redesign')
        ],
        default='medium',
        verbose_name="Remediation Complexity"
    )

    recommended_actions = models.TextField(
        blank=True, 
        verbose_name="AI-Suggested Recommended Actions"
    )

    comments = models.TextField(blank=True, verbose_name="Comments")
    documented_knowledge_base = models.BooleanField(default=False, verbose_name="Documented in Knowledge Base")
    
    class Meta:
        # Unique Constraints
        constraints = [
            models.UniqueConstraint(
                fields=['error_type', 'created_at'], 
                name='unique_error_ticket'
            )
        ]
        
        # Database Indexing
        indexes = [
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['created_at', 'resolved_at']),
            models.Index(fields=['assigned_to'])
        ]
        
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        # Générer le numéro de ticket s'il n'existe pas
        if not self.ticket_number:
            self.ticket_number = self.error_type.error_code

        # Suivre les changements de statut
        if self.pk:
            try:
                original = ErrorTicket.objects.get(pk=self.pk)
                if original.status != self.status:
                    self._log_status_change(original.status, self.status)
            except ErrorTicket.DoesNotExist:
                # L'objet n'existe pas encore, aucune action nécessaire
                pass

        # Logique d'auto-résolution
        if self.status == 'RESOLVED' and not self.resolved_at:
            self.resolved_at = timezone.now()

        super().save(*args, **kwargs)

    
    def _generate_ticket_number(self):
        """
        Generate a unique ticket number
        Format: [ERROR_TYPE_CODE]-[TIMESTAMP]-[UNIQUE_SUFFIX]
        """
        timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
        error_code = self.error_type.error_code[:6] if self.error_type else 'ERR'
        unique_suffix = uuid.uuid4().hex[:4].upper()
        
        ticket_number = f"{error_code}-{timestamp}-{unique_suffix}"
        
        # Ensure uniqueness
        while ErrorTicket.objects.filter(ticket_number=ticket_number).exists():
            unique_suffix = uuid.uuid4().hex[:4].upper()
            ticket_number = f"{error_code}-{timestamp}-{unique_suffix}"
        
        return ticket_number
    
    def _log_status_change(self, old_status, new_status):
        """
        Log status changes in modification history
        """
        status_change = {
            'old_status': old_status,
            'new_status': new_status,
            'changed_at': timezone.now().isoformat()
        }
        
        history = self.modification_history or []
        history.append(status_change)
        self.modification_history = history
    
    def calculate_resolution_time(self):
        """
        Calculate total resolution time
        """
        if self.resolved_at and self.created_at:
            return (self.resolved_at - self.created_at).total_seconds() / 3600  # hours
        return None
    
    def __str__(self):
        return f"Ticket {self.ticket_number} - {self.title}"