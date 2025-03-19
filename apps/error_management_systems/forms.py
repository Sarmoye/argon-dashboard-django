from django import forms
from .models import ErrorType, ErrorEvent, ErrorTicket

class ErrorTypeForm(forms.ModelForm):
    class Meta:
        model = ErrorType
        fields = '__all__'

class ErrorEventForm(forms.ModelForm):
    class Meta:
        model = ErrorEvent
        fields = ['error_type', 'error_count', 'inserted_by', 'notes']

class ErrorTicketForm(forms.ModelForm):
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