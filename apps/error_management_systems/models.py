import uuid
from django.db import models
from django.db.models import UniqueConstraint, Index
from django.utils import timezone
from django.core.exceptions import ValidationError

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
    system_name = models.CharField(max_length=100, db_index=True)
    service_name = models.CharField(max_length=100, db_index=True)
    
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
                fields=['system_name', 'service_name', 'error_code'], 
                name='unique_error_type'
            )
        ]
        
        # Database Indexing
        indexes = [
            Index(fields=['system_name', 'service_name']),
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
        base_code = f"{self.system_name[:3]}_{self.service_name[:3]}_{uuid.uuid4().hex[:6]}"
        counter = 1
        
        while ErrorType.objects.filter(error_code=base_code).exists():
            base_code = f"{self.system_name[:3]}_{self.service_name[:3]}_{uuid.uuid4().hex[:6]}_{counter}"
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
        return f"{self.system_name} - {self.error_code}"


class ErrorEvent(models.Model):
    """
    Detailed Error Event Tracking
    """
    # Unique Identifier
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Protected Foreign Key
    error_type = models.ForeignKey(
        ErrorType, 
        on_delete=models.PROTECT,
        related_name='events',
        verbose_name="Associated Error Type"
    )
    
    # Indexed Fields
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    system_name = models.CharField(max_length=100, db_index=True)
    service_name = models.CharField(max_length=100, db_index=True)
    
    # Comprehensive Logging
    event_log = models.JSONField(
        blank=True, 
        null=True, 
        verbose_name="Detailed Event Logs"
    )
    
    # Error Context
    source_ip = models.GenericIPAddressField(
        blank=True, 
        null=True, 
        verbose_name="Source IP Address"
    )
    user_context = models.JSONField(
        blank=True, 
        null=True, 
        verbose_name="User Context Details"
    )
    
    # Error Count and Tracking
    error_count = models.PositiveIntegerField(default=1)
    
    class Meta:
        # Unique Constraints
        constraints = [
            UniqueConstraint(
                fields=['error_type', 'timestamp', 'system_name', 'service_name'], 
                name='unique_error_event'
            )
        ]
        
        # Database Indexing
        indexes = [
            Index(fields=['timestamp', 'system_name']),
            Index(fields=['source_ip'])
        ]
    
    def clean(self):
        """
        Additional validation
        """
        # Prevent excessive error count
        if self.error_count > 1000:
            raise ValidationError("Error count cannot exceed 1000")
    
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
        # Generate Ticket Number if not exists
        if not self.ticket_number:
            self.ticket_number = self._generate_ticket_number()
        
        # Track status changes
        if self.pk:
            original = ErrorTicket.objects.get(pk=self.pk)
            if original.status != self.status:
                self._log_status_change(original.status, self.status)
        
        # Auto-resolve logic
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

# Custom Manager for Advanced Querying
class ErrorTicketManager(models.Manager):
    def get_urgent_tickets(self):
        """
        Retrieve urgent tickets
        """
        return self.filter(
            models.Q(priority__in=['P1', 'P2']) & 
            models.Q(status__in=['OPEN', 'IN_PROGRESS'])
        )
    
    def get_overdue_tickets(self, days=7):
        """
        Find tickets that have been open beyond a certain threshold
        """
        threshold_date = timezone.now() - timezone.timedelta(days=days)
        return self.filter(
            created_at__lt=threshold_date,
            status__in=['OPEN', 'IN_PROGRESS']
        )

# Apply custom manager
ErrorTicket.objects = ErrorTicketManager()


# Optional: Custom Model Manager for Advanced Querying
class ErrorTypeManager(models.Manager):
    def get_critical_errors(self):
        """
        Retrieve critical error types
        """
        return self.filter(
            category__severity_level=4, 
            is_active=True
        )
    
    def aggregate_by_system(self):
        """
        Aggregate error occurrences by system
        """
        return self.values('system_name').annotate(
            total_errors=models.Sum('total_occurrences')
        ).order_by('-total_errors')

# Apply custom manager
ErrorType.objects = ErrorTypeManager()