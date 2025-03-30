# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

# Create your views here.
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from .forms import LoginForm, SignUpForm

from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from .forms import LoginForm
from .utils import ldap_connect, send_email
import logging
from django.contrib import messages
from .models import *
from django.urls import reverse


logger = logging.getLogger(__name__)

def login_view(request):
    form = LoginForm(request.POST or None)
    msg = None

    if request.method == "POST":
        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            
            # Vérifier si l'utilisateur existe dans la base de données
            try:
                user = CustomUser.objects.get(username=username)
            except CustomUser.DoesNotExist:
                logger.info(f"User {username} are not authorized.")
                msg = 'You are not authorized'
                messages.error(request, msg)
                return render(request, "accounts/login.html", {"form": form, "msg": msg})
            
            # Vérifier les informations d'authentification dans le serveur LDAP
            ldap_status = ldap_connect(username, password)
            
            if ldap_status['stat'] == 1:

                # Authentifier l'utilisateur avec le nom d'utilisateur Django et le mot de passe par défaut
                user = authenticate(request, username=username, password=ldap_status['pass'])
                
                if user is not None:
                    login(request, user)
                    # Enregistrement du log
                    logger.info(f"User {username} successfully logged in.")
                    
                    # Envoi d'un e-mail à l'administrateur
                    # from_email = "EMS.Administrator@mtn.com"
                    # to_email = ["Sarmoye.AmitoureHaidara@mtn.com"]
                    # body = f"User {username} has logged in to the application."
                    # subject = "New user login"
                    # send_email(from_email, to_email, subject, body)
                    
                    # Retrieve the next parameter or redirect to the home page of the other app
                    next_url = request.GET.get('next', reverse('error_management_systems:dashboard1'))  # Redirect to home app
                    
                    return redirect(next_url)
                else:    
                    msg = 'Invalid credentials'    
                    logger.error(f"User {username} Invalid credentials.")           
            else:
                msg = 'Invalid credentials (MTN)'
                logger.error(f"User {username} Invalid credentials.(MTN)")
        else:
            msg = 'Error validating the form'
            logger.info(f"User {username} Error validating the form.")

    return render(request, "accounts/login.html", {"form": form, "msg": msg})

def register_user(request):
    msg = None
    success = False

    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get("username")
            raw_password = form.cleaned_data.get("password1")
            user = authenticate(username=username, password=raw_password)

            msg = 'User created - please <a href="/login">login</a>.'
            success = True

            # return redirect("/login/")

        else:
            msg = 'Form is not valid'
    else:
        form = SignUpForm()

    return render(request, "accounts/register.html", {"form": form, "msg": msg, "success": success})
