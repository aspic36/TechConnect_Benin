#!/usr/bin/env python3
"""
Script de ligne de commande Django pour TechConnect Bénin.

Ce script est le point d'entrée principal pour toutes les opérations d'administration
du projet : lancement du serveur de développement, exécution des migrations, création
d'un superutilisateur, collecte des fichiers statiques, etc.

Utilisation :
    python3 manage.py <commande> [options]

Commandes courantes :
    runserver          Lancer le serveur de développement (port 8000 par défaut)
    makemigrations     Générer les fichiers de migration SQL à partir des modèles
    migrate            Appliquer les migrations en base de données
    createsuperuser    Créer un compte superutilisateur (admin Django)
    collectstatic      Copier les fichiers statiques dans STATIC_ROOT (prod)
    seed_demo          Peupler la base avec des données de démonstration
    test               Exécuter la suite de tests automatisés
"""

import os
import sys


def main():
    """
    Configure l'environnement Django et lance l'exécution de la commande.

    Définit le module de settings par défaut (config.settings), puis délègue
    à execute_from_command_line() de Django pour parser les arguments et
    exécuter la commande demandée (runserver, migrate, etc.).

    Si Django n'est pas installé ou indisponible, affiche un message d'erreur
    explicite pour aider au diagnostic (virtual environment oubliée, etc.).
    """
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    # Permet l'exécution directe du script : python3 manage.py <commande>
    main()
