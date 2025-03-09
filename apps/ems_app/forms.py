from django import forms
from .models import ErrorType, ErrorEvent, ErrorTicket

class ErrorTypeForm(forms.ModelForm):
    """Formulaire pour la création/modification du type d'erreur"""
    class Meta:
        model = ErrorType
        fields = ['system_name', 'service_type', 'service_name', 'error_reason', 
                  'code_erreur', 'comportement_attendu', 'correction_automatique']
        widgets = {
            'error_reason': forms.Textarea(attrs={'rows': 3}),
            'comportement_attendu': forms.Textarea(attrs={'rows': 3}),
        }

class ErrorEventForm(forms.ModelForm):
    """Formulaire pour les détails de l'événement d'erreur"""
    class Meta:
        model = ErrorEvent
        fields = ['error_count', 'domain', 'logs', 'version_system', 'inserted_by', 'notes']
        widgets = {
            'logs': forms.Textarea(attrs={'rows': 5}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

class ErrorTicketForm(forms.ModelForm):
    """Formulaire pour la création/modification d'un ticket d'erreur"""
    class Meta:
        model = ErrorTicket
        fields = ['priorite', 'niveau_criticite', 'symptomes', 'impact', 
                 'services_affectes', 'nombre_utilisateurs', 'responsable', 
                 'equipe', 'actions']
        widgets = {
            'symptomes': forms.Textarea(attrs={'rows': 3}),
            'impact': forms.Textarea(attrs={'rows': 3}),
            'services_affectes': forms.Textarea(attrs={'rows': 3}),
            'actions': forms.Textarea(attrs={'rows': 3}),
        }