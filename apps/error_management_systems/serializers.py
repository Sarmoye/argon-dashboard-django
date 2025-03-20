from rest_framework import serializers
from .models import ErrorEvent  # Import your models

class ErrorEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = ErrorEvent
        fields = '__all__'  # Or specify the fields you want to include