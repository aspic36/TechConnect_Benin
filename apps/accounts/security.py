from django.core.cache import cache

MAX_TENTATIVES_ECHOUEES = 5
DUREE_BLOCAGE_SECONDES = 60 * 15


def _clef_bruteforce(username):
    return f'connexion_echoue:{username}'


def tentative_autorisee(username):
    return cache.get(_clef_bruteforce(username), 0) < MAX_TENTATIVES_ECHOUEES


def reinitialiser_echecs(username):
    cache.delete(_clef_bruteforce(username))


def enregistrer_echec(username):
    tentatives = cache.get(_clef_bruteforce(username), 0) + 1
    cache.set(_clef_bruteforce(username), tentatives, DUREE_BLOCAGE_SECONDES)