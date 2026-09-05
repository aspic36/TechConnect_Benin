# AGENTS.md — TechConnect Bénin

Guide de contexte pour les agents et développeurs travaillant sur ce projet.

## 🎯 Présentation

Plateforme béninoise de mise en relation entre **clients** (besoins informatiques) et **prestataires** (services informatiques). Un client publie une demande, les prestataires soumettent des propositions, une mission démarre quand une proposition est acceptée, avec messagerie sécurisée et évaluations.

Repo GitHub : `https://github.com/aspic36/TechConnect_Benin`

## ⚙️ Stack technique

| Composant | Technologie |
|---|---|
| Backend | Python 3.14 + Django 4.2 (templates + Jinja2) |
| Base de données | MySQL 8.0 (conteneur Docker `techconnect_db`, port hôte **3307**) |
| Connecteur BDD | PyMySQL (`config/__init__.py` → `install_as_MySQLdb()`) |
| Admin BDD (UI) | Adminer (conteneur `techconnect_adminer`, port **8081**) |
| Frontend | HTML5 / CSS3 / JS, design system maison « moderne & coloré » |
| Langue du site | Français (`fr-fr`), fuseau `Africa/Porto-Novo` |

## 🗂 Arborescence

```
TechConnect_Benin/
├── apps/
│   ├── accounts/       # User personnalisé, auth (inscription, connexion, profil)
│   ├── demandes/       # Categorie, Demande, catalogue, publication
│   ├── propositions/   # Proposition, Mission, Evaluation, Paiement
│   ├── messagerie/     # Message (fil par mission)
│   └── admin_panel/    # Back-office (stats, vérification prestataires)
├── config/             # settings.py, urls.py, wsgi/asgi, init PyMySQL
├── docs/               # architecture.md, maquettes/
├── static/css/         # style.css (design system)
├── templates/          # base.html + templates par app
├── media/              # uploads (avatars…)
├── docker-compose.yml  # conteneurs MySQL + Adminer
├── manage.py
├── requirements.txt
├── .env                # SECRETS — jamais commité (dans .gitignore)
└── .env.example        # modèle public des variables
```

## 🔑 Variables d'environnement (`.env`)

Copier `.env.example` → `.env` puis remplir. Variables utilisées par `config/settings.py` :
```
DB_NAME, DB_USER, DB_PASSWORD, DB_ROOT_PASSWORD, DB_HOST, DB_PORT
DJANGO_SECRET_KEY, DJANGO_DEBUG, DJANGO_ALLOWED_HOSTS
```
⚠️ Jamais committer `.env`. Les mots de passe réels restent locaux.

## 🛠 Commandes essentielles

```bash
# Lancer la BDD (conteneurs Docker)
docker compose up -d

# Serveur Django (depuis la racine)
python3 manage.py runserver            # http://127.0.0.1:8000
python3 manage.py check                # vérification config
python3 manage.py makemigrations       # générer les migrations
python3 manage.py migrate              # appliquer les migrations

# Superutilisateur
python3 manage.py createsuperuser

# Console
python3 manage.py shell
```

## 🧩 Règles métier

- **2 rôles uniquement** : `client` / `prestataire` (le rôle Admin a été supprimé — les accès admin passent par `is_staff`/`is_superuser`).
- **Confidentialité** : un client ne voit **que ses propres demandes** ; les prestataires voient le **catalogue public** (demandes `en_cours`).
- **Cycle de mission** : Demande → Propositions → Accepter (crée la mission, refuse les autres) → Messagerie → Clôture → Évaluation (note 1–5).
- Blocages par rôle : seul `client` publie, seul `prestataire` propose.
- Messagerie restreinte aux 2 parties de la mission.

## ✅ DÉJÀ FAIT (depuis le début)

1. **Dossier de conception** lu (`TechConnect_Benin_Dossier_Conception_v2.docx`) : stack validée, phases planifiées.
2. **Dépôt GitHub** créé + branche `main` liée.
3. **Étape 1 — Environnement** : `requirements.txt`, PyMySQL installé, `.gitignore`.
4. **Étape 2 — BDD** : conteneur Docker `techconnect_db` (MySQL 8.0, port 3307) + `techconnect_adminer` (8081), volume dédié, `.env` sécurisé, base `techconnect_benin` créée et testée.
   - Note infra : le MySQL système (host) et celui d'IT-Asset-Manager (port 3306) sont **intacts** ; TechConnect utilise son propre conteneur révélé.
5. **Étape 3 — Init Django** : `manage.py`, `settings.py` (MySQL via `.env`, `fr-fr`, `Africa/Porto-Novo`), PyMySQL branché.
6. **Étape 4-5 — Modèles + migrations** : 5 apps, 8 modèles métier, 17 tables en BDD, superutilisateur `admin` créé.
7. **Backend des vues** : accounts, demandes, propositions, messagerie, admin_panel — flux complet testé end-to-end (client de test Django), bug OneToOne corrigé.
8. **Maquettes/design** : design system « moderne & coloré », landing page, 16 templates refaits, responsive.
9. **Fix rôles** : rôle `Admin` retiré de l'inscription (migration `0002`), 2 rôles business uniquement.

## ✅ PROGRESSES (depuis la dernière étape)

10. **README.md** à la racine : présentation, fonctionnalités, installation, comptes de démo, cycle de vie, commandes, roadmap.
11. **Données de démo** : commande `python3 manage.py seed_demo` (7 catégories, 5 comptes démo, 7 demandes à tous les stades, propositions, 2 missions dont 1 évaluée, messages) — tests de navigation OK sur tous les rôles.

## 🔲 RESTE À FAIRE (roadmap)

**Logiciel (MVP)**
- [x] ~~Backend BDD + modèles + vues~~ (fait)
- [x] ~~README.md~~ (fait)
- [x] ~~Données de démo~~ (`python3 manage.py seed_demo`)
- [ ] Tests automatisés versionnés dans chaque app (`tests.py`)
- [ ] README.md à la racine (guide d'installation utilisateur)
- [ ] Formulaire profil (édition des infos, avatar, bio)
- [ ] Back-office : modération des demandes (validation `en_attente`), gestion des litiges
- [ ] Paiements : accord direct MVP → escrow / Mobile Money (Phase future, modèle `Paiement` prêt)

**Sécurité & production (Phases 5-6)**
- [ ] Renforcement : rates limites, protection brute force, validation fichiers upload (avatar)
- [ ] Déploiement Linux + Nginx + HTTPS
- [ ] Sauvegardes régulières MySQL configurées
- [ ] Phase bêta fermée avec premiers utilisateurs au Bénin

**Mobile (Phase 2)**
- [ ] Application Android/iOS avec Flutter (API REST Django à exposer)

## 🧪 Convention de commits

```
<type> <sujet concis>
ex : Feat backend : … | Fix auth : … | Style : … | Docs : …
```
Historique actuel : `fc9e230` (init) → `20edad3` (backend+BDD) → `770bc83` (vues) → `aad88d5` (design) → `7e08172` (fix rôles).