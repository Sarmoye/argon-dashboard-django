from django import forms
from .models import ErrorType, ErrorEvent, ErrorTicket

class ErrorTypeForm(forms.ModelForm):
    """Formulaire pour la création/modification du type d'erreur"""
    class Meta:
        model = ErrorType
        fields = ['system_name', 'service_type', 'service_name', 'error_reason', 
                  'code_erreur', 'comportement_attendu', 'correction_automatique']
        widgets = {
            'system_name': forms.TextInput(attrs={'class': 'form-control'}),
            'service_type': forms.TextInput(attrs={'class': 'form-control'}),
            'service_name': forms.TextInput(attrs={'class': 'form-control'}),
            'error_reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'code_erreur': forms.TextInput(attrs={'class': 'form-control'}),
            'comportement_attendu': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'correction_automatique': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class ErrorEventForm(forms.ModelForm):
    """Formulaire pour les détails de l'événement d'erreur"""
    class Meta:
        model = ErrorEvent
        fields = ['error_count', 'domain', 'logs', 'version_system', 'inserted_by', 'notes']
        widgets = {
            'error_count': forms.NumberInput(attrs={'class': 'form-control'}),
            'domain': forms.TextInput(attrs={'class': 'form-control'}),
            'logs': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'version_system': forms.TextInput(attrs={'class': 'form-control'}),
            'inserted_by': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class ErrorTicketForm(forms.ModelForm):
    """Formulaire pour la création/modification d'un ticket d'erreur"""
    class Meta:
        model = ErrorTicket
        fields = ['priorite', 'niveau_criticite', 'symptomes', 'impact', 
                 'services_affectes', 'nombre_utilisateurs', 'responsable', 
                 'equipe', 'actions']
        widgets = {
            'priorite': forms.Select(attrs={'class': 'form-control'}),
            'niveau_criticite': forms.Select(attrs={'class': 'form-control'}),
            'symptomes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'impact': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'services_affectes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'nombre_utilisateurs': forms.NumberInput(attrs={'class': 'form-control'}),
            'responsable': forms.TextInput(attrs={'class': 'form-control'}),
            'equipe': forms.TextInput(attrs={'class': 'form-control'}),
            'actions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }