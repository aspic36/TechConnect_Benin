"""
Configuration Django du projet TechConnect Bénin.

Ce module centralise l'ensemble des paramètres de configuration de l'application
Django : connexion à la base de données MySQL (via PyMySQL), variables d'environnement
chargées depuis le fichier .env, paramètres de sécurité, localisation (français,
fuseau Africa/Porto-Novo), applications installées, gestion des fichiers statiques
et médias, ainsi que les hooks de sécurité pour la production (HTTPS, HSTS, cookies
 sécurisés).

Les variables critiques (clé secrète, identifiants BDD, hosts autorisés) sont lues
depuis les variables d'environnement pour éviter toute fuite de secrets dans le code
source.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Répertoire racine du projet (dossier parent de config/)
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# Chargement du fichier .env situé à la racine du projet.
# Ce fichier contient les secrets (mots de passe BDD, clé Django, etc.)
# et ne doit JAMAIS être commité dans le dépôt.
load_dotenv(BASE_DIR / '.env')

# ---------------------------------------------------------------------------
# Sécurité : clé secrète Django
# ---------------------------------------------------------------------------
# Utilise la variable d'environnement DJANGO_SECRET_KEY si elle existe,
# sinon une valeur par défaut non sécurisée (à ne JAMAIS utiliser en prod).
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-dev-change-me')

# ---------------------------------------------------------------------------
# Mode débogage
# ---------------------------------------------------------------------------
# True en développement (affiche les erreurs détaillées, sert les fichiers statiques).
# Doit être False en production pour activer les protections HTTPS.
DEBUG = os.getenv('DJANGO_DEBUG', 'True') == 'True'

# ---------------------------------------------------------------------------
# Hôtes autorisés
# ---------------------------------------------------------------------------
# Liste des noms de domaine / adresses IP autorisés à servir l'application.
# Séparés par des virgules dans la variable d'environnement.
ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# ---------------------------------------------------------------------------
# Applications installées
# ---------------------------------------------------------------------------
# Applications Django de base (admin, auth, sessions, etc.) + nos 5 apps métier :
#   - accounts   : inscription, connexion, profil utilisateur
#   - demandes   : publication et catalogue de demandes informatiques
#   - propositions : propositions de prestataires et gestion des missions
#   - messagerie : messagerie sécurisée par mission
#   - admin_panel : back-office (stats, vérification prestataires)
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'apps.accounts',
    'apps.demandes',
    'apps.propositions',
    'apps.messagerie',
    'apps.admin_panel',
]

# ---------------------------------------------------------------------------
# Modèle utilisateur personnalisé
# ---------------------------------------------------------------------------
# On remplace le modèle User par défaut de Django par notre propre modèle
# (apps.accounts.User) qui gère les rôles client / prestataire.
AUTH_USER_MODEL = 'accounts.User'

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
# Pipeline de traitement des requêtes : sécurité (headers), sessions, CSRF,
# authentification, messages flash, protection clickjacking.
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ---------------------------------------------------------------------------
# URLs racine du projet
# ---------------------------------------------------------------------------
ROOT_URLCONF = 'config.urls'

# ---------------------------------------------------------------------------
# Templates (moteur de rendu Django)
# ---------------------------------------------------------------------------
# Les templates se trouvent dans /templates à la racine ET dans chaque app (APP_DIRS).
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# ---------------------------------------------------------------------------
# Point d'entrée WSGI
# ---------------------------------------------------------------------------
WSGI_APPLICATION = 'config.wsgi.application'

# ---------------------------------------------------------------------------
# Base de données — MySQL 8.0 (conteneur Docker)
# ---------------------------------------------------------------------------
# Tous les paramètres sont lus depuis les variables d'environnement (.env).
# Le conteneur Docker expose MySQL sur le port hôte 3307.
# Le charset utf8mb4 supporte les caractères Unicode (accentués, emojis).
# La connexion passe par PyMySQL (voir config/__init__.py pour install_as_MySQLdb).
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('DB_NAME', 'techconnect_benin'),
        'USER': os.getenv('DB_USER', 'techconnect_user'),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', '127.0.0.1'),
        'PORT': os.getenv('DB_PORT', '3307'),
        'OPTIONS': {
            'charset': 'utf8mb4',
        },
    }
}

# ---------------------------------------------------------------------------
# Validateurs de mot de passe
# ---------------------------------------------------------------------------
# Ces validateurs imposent des règles de sécurité sur les mots de passe :
#   - Similarité avec les attributs utilisateur (nom, email…)
#   - Longueur minimale
#   - Non-mot de passe commun
#   - Non-numérique uniquement
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# ---------------------------------------------------------------------------
# Localisation — Français Bénin
# ---------------------------------------------------------------------------
# Langue par défaut : français (France). L'interface sera traduite en français.
# Fuseau horaire : Africa/Porto-Novo (UTC+1, heure officielle du Bénin).
LANGUAGE_CODE = 'fr-fr'

TIME_ZONE = 'Africa/Porto-Novo'

# Activation de l'internationalisation (i18n) et du stockage horaire en UTC (TZ).
USE_I18N = True

USE_TZ = True

# ---------------------------------------------------------------------------
# Sécurité — headers et protection contre le sniffing MIME
# ---------------------------------------------------------------------------
# SECURE_CONTENT_TYPE_NOSNIFF : empêche le navigateur de deviner le type MIME
#   (protection contre les attaques par upload de fichier dangereux).
# SECURE_REFERRER_POLICY : limite les informations envoyées via le header Referrer.
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'

# ---------------------------------------------------------------------------
# Sécurité — HTTPS forcé en production (hors mode DEBUG)
# ---------------------------------------------------------------------------
# Lorsque DEBUG=False, on active :
#   - Cookies de session et CSRF en HTTPS uniquement
#   - Redirection automatique vers HTTPS
#   - HSTS (1 an, tous les sous-domaines) pour forcer le navigateur en HTTPS
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True

# ---------------------------------------------------------------------------
# Fichiers statiques (CSS, JS, images, fonts)
# ---------------------------------------------------------------------------
# STATIC_URL    : URL publique pour accéder aux fichiers statiques.
# STATICFILES_DIRS : dossiers source contenant les fichiers statiques du projet.
# STATIC_ROOT   : dossier de collecte (collectstatic) pour la production.
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# ---------------------------------------------------------------------------
# Fichiers médias (uploads utilisateurs : avatars, pièces jointes…)
# ---------------------------------------------------------------------------
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ---------------------------------------------------------------------------
# Type d'auto-field par défaut
# ---------------------------------------------------------------------------
# Utilise BigInt au lieu de Int pour les clés primaires auto-incrémentées :
# supporte un volume bien plus important de données.
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'