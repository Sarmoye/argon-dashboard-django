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
        fields = '__all__'