"""
Module de securite pour l'application accounts.

Implemente la protection contre les attaques par force brute sur la page
de connexion en comptabilisant les tentatives echouees dans le cache
Django.  Apres un nombre configurable d'echecs consecutifs, le login est
bloque pendant une duree definie.
"""

from django.core.cache import cache

# Nombre maximal de tentatives echouees avant blocage
MAX_TENTATIVES_ECHOUEES = 5
# Duree du blocage en secondes (15 minutes)
DUREE_BLOCAGE_SECONDES = 60 * 15


def _clef_bruteforce(username):
    """Genere la clef de cache unique pour le compteur d'echecs d'un login."""
    return f'connexion_echoue:{username}'


def tentative_autorisee(username):
    """Renvoie ``True`` si l'utilisateur ``username`` peut encore tenter de se connecter.

    La tentative est refusee lorsque le compteur d'echecs en cache atteint
    ou depasse ``MAX_TENTATIVES_ECHOUEES``.
    """
    return cache.get(_clef_bruteforce(username), 0) < MAX_TENTATIVES_ECHOUEES


def reinitialiser_echecs(username):
    """Supprime le compteur d'echecs du cache pour ``username``.

    Appele apres une connexion reussie.
    """
    cache.delete(_clef_bruteforce(username))


def enregistrer_echec(username):
    """Incremente le compteur d'echecs de ``username`` dans le cache.

    La clef expire automatiquement apres ``DUREE_BLOCAGE_SECONDES`` secondes
    pour debloquer l'utilisateur apres la periode de quarantine.
    """
    tentatives = cache.get(_clef_bruteforce(username), 0) + 1
    cache.set(_clef_bruteforce(username), tentatives, DUREE_BLOCAGE_SECONDES)
