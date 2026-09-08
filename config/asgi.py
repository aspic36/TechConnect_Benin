"""
Point d'entrée ASGI (Asynchronous Server Gateway Interface) pour TechConnect Bénin.

Ce module expose un objet ``application`` compatible ASGI, utilisé par des serveurs
web asynchrones (Daphne, Uvicorn, Hypercorn…) pour servir l'application Django
en mode asynchrone. ASGI est requis pour les WebSocket et les connexions longues
(futur : temps réel dans la messagerie).

Référence officielle :
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

# Indique à Django quel module de settings utiliser par défaut.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Crée et expose l'objet ASGI callable que le serveur asynchrone invocera
# pour traiter chaque requête / connexion entrante.
application = get_asgi_application()
