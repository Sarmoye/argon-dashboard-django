from django import forms
from .models import ErrorType, ErrorEvent, ErrorTicket

class ErrorTypeForm(forms.ModelForm):
    """Formulaire pour la création/modification d'un type d'erreur"""
    class Meta:
        model = ErrorType
        fields = [
            'system',
            'service',
            'category',
            'error_code',
            'error_description',
            'error_metadata',
            'root_cause',
            'detected_by',
            'error_source',
            'dependency_chain',
            'is_active'
        ]
        widgets = {
            'system': forms.Select(attrs={'class': 'form-control'}),
            'service': forms.Select(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'error_code': forms.TextInput(attrs={'class': 'form-control'}),
            'error_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'error_metadata': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'root_cause': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'detected_by': forms.Select(attrs={'class': 'form-control'}),
            'error_source': forms.Select(attrs={'class': 'form-control'}),
            'dependency_chain': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class ErrorEventForm(forms.ModelForm):
    """Formulaire pour la création/modification d'un événement d'erreur"""
    class Meta:
        model = ErrorEvent
        fields = [
            'error_type',
            'system',
            'service',
            'event_log',
            'source_ip',
            'trigger_event',
            'error_count',
            'environment'
        ]
        widgets = {
            'error_type': forms.Select(attrs={'class': 'form-control'}),
            'system': forms.Select(attrs={'class': 'form-control'}),
            'service': forms.Select(attrs={'class': 'form-control'}),
            'event_log': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'source_ip': forms.TextInput(attrs={'class': 'form-control'}),
            'trigger_event': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'error_count': forms.NumberInput(attrs={'class': 'form-control'}),
            'environment': forms.Select(attrs={'class': 'form-control'}),
        }

class ErrorTicketForm(forms.ModelForm):
    """Formulaire pour la création/modification d'un ticket d'erreur"""
    class Meta:
        model = ErrorTicket
        fields = [
            'error_type',
            'status',
            'priority',
            'title',
            'description',
            'assigned_to',
            'assigned_team',
            'resolved_at',
            'ticket_metadata',
            'business_impact',
            'impacted_services',
            'root_cause',
            'resolution_details',
            'compliance_checked',
            'regulatory_impact',
            'estimated_downtime',
            'remediation_complexity',
            'recommended_actions',
            'comments',
            'documented_knowledge_base'
        ]
        widgets = {
            'error_type': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'assigned_to': forms.TextInput(attrs={'class': 'form-control'}),
            'assigned_team': forms.TextInput(attrs={'class': 'form-control'}),
            'resolved_at': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'ticket_metadata': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'business_impact': forms.NumberInput(attrs={'class': 'form-control'}),
            'impacted_services': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'root_cause': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'resolution_details': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'compliance_checked': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'regulatory_impact': forms.Select(attrs={'class': 'form-control'}),
            # Pour estimated_downtime, vous pouvez choisir d'utiliser TextInput si vous souhaitez un format libre
            'estimated_downtime': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'HH:MM:SS'}),
            'remediation_complexity': forms.Select(attrs={'class': 'form-control'}),
            'recommended_actions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'comments': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'documented_knowledge_base': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }