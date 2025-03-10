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


from django import forms
from .models import ErrorType1, ErrorEvent1, ErrorTicket1

from django import forms
from .models import ErrorType1, ErrorEvent1, ErrorTicket1

class ErrorType1Form(forms.ModelForm):
    """Formulaire pour la création/modification du type d'erreur"""
    class Meta:
        model = ErrorType1
        fields = ['system_name', 'service_type', 'service_name', 'error_reason',
                  'code_erreur', 'fichiers_impactes', 'logs', 'description_technique',
                  'comportement_attendu', 'procedures_contournement', 'environnement', 'niveau_severite']
        widgets = {
            'system_name': forms.TextInput(attrs={'class': 'form-control'}),
            'service_type': forms.TextInput(attrs={'class': 'form-control'}),
            'service_name': forms.TextInput(attrs={'class': 'form-control'}),
            'error_reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'code_erreur': forms.TextInput(attrs={'class': 'form-control'}),
            'fichiers_impactes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'logs': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'description_technique': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'comportement_attendu': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'procedures_contournement': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'environnement': forms.TextInput(attrs={'class': 'form-control'}),
            'niveau_severite': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class ErrorEvent1Form(forms.ModelForm):
    """Formulaire pour la création/modification d'un événement d'erreur"""
    class Meta:
        model = ErrorEvent1
        fields = ['error_type', 'system_name', 'service_type', 'service_name', 'error_reason', 'error_count', 'timestamp', 'inserted_by', 'notes']
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

class ErrorTicket1Form(forms.ModelForm):
    """Formulaire pour la création/modification d'un ticket d'erreur"""
    class Meta:
        model = ErrorTicket1
        fields = ['error_type', 'priorite', 'statut', 'niveau_criticite', 'symptomes', 'impact',
                  'services_affectes', 'charge_systeme', 'nombre_utilisateurs', 'cause_racine', 'hypotheses',
                  'responsable', 'equipe', 'actions', 'solution', 'commentaires']
        widgets = {
            'error_type': forms.Select(attrs={'class': 'form-control'}),
            'priorite': forms.Select(attrs={'class': 'form-control'}),
            'statut': forms.Select(attrs={'class': 'form-control'}),
            'niveau_criticite': forms.NumberInput(attrs={'class': 'form-control'}),
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
        }
