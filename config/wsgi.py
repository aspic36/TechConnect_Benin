"""
Point d'entrée WSGI (Web Server Gateway Interface) pour le projet TechConnect Bénin.

Ce module expose un objet ``application`` compatible WSGI, utilisé par les serveurs
web de production (Gunicorn, uWSGI, Apache mod_wsgi…) pour servir l'application
Django en HTTP synchrone.

En mode développement, le serveur intégré de Django (manage.py runserver) utilise
également ce point d'entrée via le module wsgi.py.

Référence officielle :
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

# Indique à Django quel module de settings utiliser par défaut.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Crée et expose l'objet WSGI callable que le serveur web invocera
# pour traiter chaque requête HTTP entrante.
application = get_wsgi_application()
