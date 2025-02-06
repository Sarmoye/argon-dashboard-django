from ldap3 import Server, Connection, NTLM, SUBTREE, ALL
from ldap3.core.exceptions import LDAPBindError
import getpass

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

"""
MTN ldap servers
ldap://srv-vdcs01.mtn.local:389
ldap://srv-vdcs02.mtn.local:389
ldap://srv-vdcs11.mtn.local:389
"""

LDAP_URL = 'ldap://srv-vdcs02.mtn.local:389'
BASE_DN = 'DC=mtn,DC=local'

def ldap_connect(username, password):
    """
    Connect to LDAP server and search for user by username.
    Returns a dictionary with status, fullname, and email if user is found, None otherwise.
    """
    try:
        # Connect to LDAP server
        server = Server(LDAP_URL, get_info=ALL)
        connection = Connection(server, user=f"mtn\\{username}", password=password, auto_bind=True)

        # Search for user
        search_filter = f"(&(objectClass=user)(sAMAccountName={username}))"
        search_scope = SUBTREE
        search_attrs = ["cn", "mail"]

        search_results = connection.search(BASE_DN, search_filter, attributes=search_attrs)

        # Iterate over search results
        for entry in connection.entries:
            print("Found user: {}".format(entry.cn) + " [MTN BENIN]")
            if "mail" in entry:
                print("Email address: {}".format(entry.mail.value))
                status = {
                    "stat": 1,
                    "username": username,
                    "password": password,
                    "fullname": entry.cn,
                    "email": entry.mail.value,
                    "pass": "Cool boy 242526"
                }
                return status
        
        return None

    except LDAPBindError:
        print("Invalid credentials")
        status = {"stat": 0}
        return status
    except Exception as e:
        print(f"Error: {str(e)}")
        status = {"stat": 0}
        return status
    

def send_email(from_email, to_emails, subject, body, pdf_file_path=None):
    smtp_server = '10.77.152.66'  # Adresse IP du serveur SMTP de votre entreprise
    smtp_port = 25  # Port SMTP utilisé par votre serveur

    # Créer le message
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = ', '.join(to_emails)  # Concaténer les adresses e-mail avec une virgule
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    """ # Attacher le fichier PDF en pièce jointe
    with open(pdf_file_path, 'rb') as pdf_file:
        pdf_attachment = MIMEApplication(pdf_file.read(), _subtype='pdf')
        pdf_attachment.add_header('Content-Disposition', f'attachment; filename="{pdf_file_path}"')
        msg.attach(pdf_attachment) """

    try:
        # Se connecter au serveur SMTP
        server = smtplib.SMTP(smtp_server, smtp_port)
        # Envoyer l'e-mail
        server.sendmail(from_email, to_emails, msg.as_string())
        print('E-mail envoyé avec succès !')
    except Exception as e:
        print('Erreur lors de l\'envoi de l\'e-mail:', str(e))
    finally:
        try:
            # Déconnecter du serveur SMTP
            server.quit()
        except NameError:
            pass

# Envoi d'un e-mail à l'administrateur
from_email = "EMS.Administrator@mtn.com"
to_email = ["Sarmoye.AmitoureHaidara@mtn.com"]
body = f"User Hi ! this is a send mail test in to the application."
subject = "New user login"
# send_email(from_email, to_email, subject, body)

username = input("Username: ")
password = getpass.getpass("Enter Password:")

stat = ldap_connect(username=username, password=password)

print (stat)