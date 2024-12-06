# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(unique=True, blank=True, null=True)
    role = models.CharField(max_length=50, choices=[
        ('superadmin', 'Superadmin'),
        ('admin', 'Admin'),
        ('analyst', 'Analyst'),
        ('viewer', 'Viewer')
    ], default='viewer')

    # Ajoutez un related_name unique pour éviter les conflits
    groups = models.ManyToManyField(
        'auth.Group', 
        related_name='customuser_groups',  # Nom unique pour éviter le conflit
        blank=True,
    )
    
    user_permissions = models.ManyToManyField(
        'auth.Permission', 
        related_name='customuser_permissions',  # Nom unique pour éviter le conflit
        blank=True,
    )

    def __str__(self):
        return self.username
