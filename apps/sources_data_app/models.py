from django.db import models
import uuid

class SourceData(models.Model):
    SYSTEM_CHOICES = [
        ('BSS_ESF', 'BSS ESF'),
        ('IRM', 'IRM'),
        ('CIS', 'CIS'),
        ('ECW_SP', 'ECW SP'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    unique_identifier = models.CharField(max_length=50, unique=True, blank=True)
    system_name = models.CharField(max_length=50, choices=SYSTEM_CHOICES)
    domain = models.CharField(max_length=100)
    service_type = models.CharField(max_length=100)
    service_name = models.CharField(max_length=100)
    error_count = models.IntegerField()
    error_reason = models.TextField()
    source_type = models.CharField(max_length=50)
    timestamp = models.DateTimeField(auto_now_add=True)
    validation_status = models.CharField(max_length=20, default='Pending', choices=[
        ('Pending', 'Pending'),
        ('Validated', 'Validated'),
        ('Rejected', 'Rejected')
    ])
    processed_flag = models.BooleanField(default=False)
    admin_notes = models.TextField(blank=True, null=True)
    inserted_by = models.CharField(max_length=50, default='Automated_Script')

    def save(self, *args, **kwargs):
        if not self.unique_identifier:
            # Generate a unique identifier based on the system_name and a UUID
            self.unique_identifier = f"{self.system_name}_{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.system_name} - {self.unique_identifier}"