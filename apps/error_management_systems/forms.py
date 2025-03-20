from django import forms
from .models import ErrorType, ErrorEvent, ErrorTicket

class ErrorTypeForm(forms.ModelForm):
    """Formulaire pour la création/modification du type d'erreur"""
    class Meta:
        model = ErrorType
        fields = ['system_name', 'service_type', 'service_name', 'error_reason', 
                  'code_erreur', 'comportement_attendu']
        widgets = {
            'system_name': forms.TextInput(attrs={'class': 'form-control'}),
            'service_type': forms.TextInput(attrs={'class': 'form-control'}),
            'service_name': forms.TextInput(attrs={'class': 'form-control'}),
            'error_reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'code_erreur': forms.TextInput(attrs={'class': 'form-control'}),
            'comportement_attendu': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class ErrorEventForm(forms.ModelForm):
    class Meta:
        model = ErrorEvent
        fields = ['error_type', 'error_count', 'inserted_by', 'notes']

class ErrorTicketForm(forms.ModelForm):
    class Meta:
        model = ErrorTicket
        fields = [
            'priorite', 'statut', 'niveau_criticite', 'symptomes', 'impact',
            'services_affectes', 'charge_systeme', 'nombre_utilisateurs',
            'cause_racine', 'hypotheses', 'responsable', 'equipe', 'actions',
            'solution', 'commentaires', 'historique', 'date_resolution',
            'lessons_learned', 'validation_responsable', 'documented_knowledge_base'
        ]
        widgets = {
            'priorite': forms.Select(attrs={'class': 'form-control'}),
            'statut': forms.Select(attrs={'class': 'form-control'}),
            'niveau_criticite': forms.Select(attrs={'class': 'form-control'}),
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