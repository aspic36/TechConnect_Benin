# 💼 TechConnect Bénin

Plateforme béninoise de mise en relation entre **clients** (besoins informatiques) et **prestataires** (services informatiques).

> Un client publie une demande, les prestataires soumettent leurs propositions, la mission démarre quand une proposition est acceptée — avec messagerie sécurisée et évaluations.

## ✨ Fonctionnalités

**🟢 Client**
- Publier une demande (budget, lieu, catégorie, urgence)
- Recevoir et comparer les propositions des prestataires
- Accepter / refuser une proposition → démarrage de la mission
- Suivre ses missions et évaluer le prestataire (note 1–5)

**🟣 Prestataire**
- Explorer le catalogue des demandes publiques (recherche + filtre par catégorie)
- Soumettre une proposition (prix, délais, message)
- Suivre ses propositions et ses missions
- Recevoir les évaluations des clients
- Régler ses commissions (10% du prix des missions clôturées)

**🔵 Commun**
- Messagerie intégrée par mission (restreinte aux 2 parties)
- Profil avec informations et badge de vérification

**🛠 Back-office (admin)**
- Tableau de bord (stats clients, prestataires, demandes, missions)
- Vérification des comptes prestataires
- Confirmation des règlements de commission (avec prolongation possible)
- Sanctions manuelles : suspendre / bannir / réactiver un prestataire

## 🧱 Stack technique

| Composant | Technologie |
|---|---|
| Backend | Python 3.14 + Django 4.2 (templates Jinja2) |
| Base de données | MySQL 8.0 (Docker, port 3307) |
| Frontend | HTML / CSS / JS, design system maison « moderne & coloré » |
| Langue | Français (`fr-fr`) · Fuseau `Africa/Porto-Novo` |

## 📁 Structure du projet

```
TechConnect_Benin/
├── apps/
│   ├── accounts/       # User personnalisé, auth, profil
│   ├── demandes/       # Catégories, Demandes, catalogue
│   ├── propositions/   # Propositions, Missions, Évaluations, Paiements
│   ├── messagerie/     # Messages
│   └── admin_panel/    # Back-office
├── config/             # settings.py, urls.py, wsgi/asgi
├── docs/               # architecture.md (schéma BDD, cycle de vie)
├── static/             # CSS du design system
├── templates/          # Templates par app
├── docker-compose.yml  # MySQL + Adminer
├── requirements.txt
├── .env                # ⚠️ secrets — jamais commité
└── .env.example        # modèle à copier
```

## 🚀 Installation (développement)

**Prérequis** : Docker, Python 3.12+ (testé avec 3.14).

```bash
# 1. Cloner le dépôt
git clone https://github.com/aspic36/TechConnect_Benin.git
cd TechConnect_Benin

# 2. Configurer les variables d'environnement
cp .env.example .env
#   → remplir DB_PASSWORD, DB_ROOT_PASSWORD, DJANGO_SECRET_KEY
#   → DB_HOST=127.0.0.1, DB_PORT=3307 (conteneur Docker)

# 3. Lancer la base de données (MySQL 8.0 + Adminer)
docker compose up -d

# 4. Installer les dépendances Python
pip install -r requirements.txt

# 5. Appliquer les migrations
python3 manage.py migrate

# 6. (Optionnel) Données de démonstration
python3 manage.py seed_demo

# 7. Créer un premier admin
python3 manage.py createsuperuser

# 8. Lancer le serveur
python3 manage.py runserver
# → http://127.0.0.1:8000
```

## 👤 Comptes de démonstration

Après avoir lancé `seed_demo`, connecte-toi avec le mot de passe **`Demo@2026!`** :

| Utilisateur | Rôle | Détail |
|---|---|---|
| `amina` | Client | Salon de coiffure (Cotonou) |
| `codjo` | Client | Association (Porto-Novo) |
| `yves` | Prestataire | Développeur web/mobile · vérifié · **plan Pro** |
| `farida` | Prestataire | Webdesigner · vérifiée |
| `nassirou` | Prestataire | Ingénieur réseaux · **abonnement Standard à confirmer** (vois le back-office) |

Le compte admin (`createsuperuser`) donne accès à `/admin/` et `/back-office/`.

## 🧩 Cycle de vie d'une mission

```
Demande publiée (en_attente)
   → validée (en_cours)  → catalogue visible
   → propositions des prestataires
   → le client accepte  → MISSION créée (+ demande "mission_active")
   → messagerie + suivi
   → clôture de la mission
   → évaluation du prestataire / du client (1–5)
```

## 🛠 Commandes utiles

```bash
docker compose up -d                 # démarrer MySQL + Adminer
python3 manage.py runserver          # serveur de dev (port 8000)
python3 manage.py seed_demo          # données de démonstration
python3 manage.py check              # vérifier la configuration
python3 manage.py makemigrations     # générer des migrations
python3 manage.py migrate            # appliquer les migrations
python3 manage.py shell              # console interactive
```

- **Adminer** (base de données) : http://127.0.0.1:8081 — serveur `db`, identifiants du `.env`.

## 📚 Documentation

- `docs/architecture.md` — schéma de la base de données, sécurité, contraintes.

## 🗺 Feuille de route

- [x] Backend complet (BDD, modèles, vues, flux métier)
- [x] Design moderne & coloré (16 pages, responsive)
- [x] Données de démonstration (`seed_demo`)
- [x] Tests automatisés (`tests.py` dans chaque app)
- [x] Édition du profil (avatar, bio, coordonnées)
- [x] Back-office : modération des demandes et gestion des litiges
- [x] Paiements (accord direct ; escrow / Mobile Money en Phase future)
- [x] Sécurité : anti brute-force connexion, validation des avatars
- [x] Sauvegardes MySQL automatiques (cron, rotation 14 jours)
- [x] Monétisation : commission 10% + sanctions (suspension → bannissement)
- [x] Monétisation : abonnements prestataires (Gratuit 3 propositions/mois, Standard 15, Pro illimité)
- [ ] Déploiement production (Linux + Nginx + HTTPS)
- [ ] API REST + application mobile (Flutter)

## 🔒 Sécurité

- `.env` contient les secrets (mots de passe BDD, clé Django) et **ne doit jamais être commité** (dans `.gitignore`).
- L'accès admin repose sur `is_staff` / `is_superuser` ; les rôles métier sont `client` / `prestataire`.

---
Made with 🇧🇯 pour les besoins informatiques du Bénin.