from django import forms
from .models import ErrorType, ErrorEvent, ErrorTicket

from django import forms
from .models import ErrorType

class ErrorTypeForm(forms.ModelForm):
    """Formulaire pour la création/modification du type d'erreur"""
    class Meta:
        model = ErrorType
        fields = [
            'system_name', 'service_type', 'service_name', 'error_reason',
            'type_error', 'system_classification', 'service_classification', 'error_category', 'impact_level', 'trigger_event',
            'occurred_at', 'source_component', 'code_erreur', 'fichiers_impactes',
            'request_payload', 'stack_trace'
        ]
        widgets = {
            'system_name': forms.TextInput(attrs={'class': 'form-control'}),
            'service_type': forms.TextInput(attrs={'class': 'form-control'}),
            'service_name': forms.TextInput(attrs={'class': 'form-control'}),
            'error_reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'type_error': forms.Select(attrs={'class': 'form-control'}),
            'system_classification': forms.Select(attrs={'class': 'form-control'}),
            'service_classification': forms.Select(attrs={'class': 'form-control'}),
            'error_category': forms.Select(attrs={'class': 'form-control'}),
            'impact_level': forms.Select(attrs={'class': 'form-control'}),
            'trigger_event': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'occurred_at': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'source_component': forms.TextInput(attrs={'class': 'form-control'}),
            'code_erreur': forms.TextInput(attrs={'class': 'form-control'}),
            'fichiers_impactes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'request_payload': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'stack_trace': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
        }

class ErrorEventForm(forms.ModelForm):
    class Meta:
        model = ErrorEvent
        fields = [
            'error_type', 'system_name', 'service_type', 'service_name', 
            'error_reason', 'error_count', 'timestamp', 'inserted_by', 
            'notes'
        ]
        widgets = {
            'error_type': forms.Select(attrs={'class': 'form-control'}),
            'system_name': forms.TextInput(attrs={'class': 'form-control'}),
            'service_type': forms.TextInput(attrs={'class': 'form-control'}),
            'service_name': forms.TextInput(attrs={'class': 'form-control'}),
            'error_reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'error_count': forms.NumberInput(attrs={'class': 'form-control'}),
            'timestamp': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'inserted_by': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class ErrorTicketForm(forms.ModelForm):
    class Meta:
        model = ErrorTicket
        fields = [
            'statut','symptomes', 'impact',
            'services_affectes', 'charge_systeme', 'nombre_utilisateurs',
            'cause_racine', 'hypotheses', 'responsable', 'equipe', 'actions',
            'solution', 'commentaires', 'historique', 'date_resolution',
            'lessons_learned', 'validation_responsable', 'documented_knowledge_base'
        ]
        widgets = {
            'statut': forms.Select(attrs={'class': 'form-control'}),
            'symptomes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'impact': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'services_affectes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'charge_systeme': forms.NumberInput(attrs={'class': 'form-control'}),
            'nombre_utilisateurs': forms.NumberInput(attrs={'class': 'form-control'}),
            'cause_racine': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'hypotheses': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'responsable': forms.TextInput(attrs={'class': 'form-control'}),
            'equipe': forms.TextInput(attrs={'class': 'form-control'}),
            'actions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'solution': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'commentaires': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'historique': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'date_resolution': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'lessons_learned': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'validation_responsable': forms.TextInput(attrs={'class': 'form-control'}),
            'documented_knowledge_base': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }