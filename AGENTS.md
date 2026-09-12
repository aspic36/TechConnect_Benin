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
12. **Tests automatisés** : suite complète dans chaque app (`tests.py`), 43 tests OK (auth, demandes, propositions, missions, évaluations, messagerie, back-office). Note infra : lancer `python3 manage.py test` (≈2 min) — si une exécution est interrompue, supprimer la base `test_techconnect_benin` dans le conteneur avant de relancer.
13. **Fin du logiciel MVP** :
    - **Formulaire profil** : édition (email, téléphone, ville, société, bio, avatar) + service des médias en dev.
    - **Modération des demandes** (back-office) : liste des demandes `en_attente`, validation → `en_cours`, suppression ; liens sur le tableau de bord.
    - **Gestion des litiges** (back-office) : liste des missions `litige`, clôture du litige (mission + demande → `cloturee`).
    - **Paiements (accord direct MVP)** : le client enregistre un paiement sur la mission (montant + méthode, statut `en_attente`), visible dans la page mission. Escrow / Mobile Money réel = Phase future.
    - Suite de tests portée à **50 tests OK**.
14. **Sécurité — renforcement n°1** :
    - **Anti brute-force** à la connexion (cache Django, 5 échecs → blocage 15 min, succès = réinitialisation).
    - **Validation des avatars** : extensions `jpg/jpeg/png/gif/webp` + taille max **5 Mo** (migration `0003`).
    - **Fix confidentialité** : un client ne peut plus voir la page d'une demande d'un **autre** client.
    - Réglages `settings.py` : `SECURE_CONTENT_TYPE_NOSNIFF`, `SECURE_REFERRER_POLICY`, et options HTTPS activées hors `DEBUG`.
    - `Pillow` déclaré dans `requirements.txt`. Suite portée à **57 tests OK**.
15. **Sauvegardes MySQL automatiques** :
    - Script `scripts/backup_db.sh` : `mysqldump` via `docker exec` (root, mot de passe lu dans `.env`), compression gzip, rotation **14 jours**.
    - Programmé par cron : **chaque nuit à 03h30** (`30 3 * * * bash .../scripts/backup_db.sh`), log dans `/tmp/techconnect_backup.log`.
    - Restauration testée avec succès (base de test temporaire). Le dossier `backups/` est ignoré par git (données sensibles).
16. **Monétisation — commission 10% + sanctions (accord direct)** :
    - Le client paie le prestataire à la fin ; à chaque clôture de mission, une **Commission** (10% du prix) est créée avec une **date limite de 7 jours** (`COMMISSION_DELAI_JOURS`).
    - Le prestataire déclare son règlement (`regler_commission`), l'**admin confirme** dans le back-office (`commissions/`).
    - Sanctions automatiques (commande `verifier_commissions`, cron **04h10**) : commission en retard → **suspension** (champ `suspendu` + middleware bloquant tout sauf la page de règlement) ; suspension de 7 jours → **bannissement** (`is_active = False`).
    - Commandes manuelles admin : `suspendre` / `bannir` / `reactiver` un prestataire (page `prestataires/`).
    - Suite portée à **68 tests OK**.
17. **Renforcement MVP (interface + anti-contournement)** :
    - Cartes du tableau de bord admin **cliquables** (liens vers les pages back-office / admin Django).
    - **Carte d'alerte « commissions déclarées à confirmer »** sur le dashboard + badge sur la page commissions.
    - **Anti-contournement messagerie** (`apps/messagerie/utils.py`) : détection des n° béninois (`+229`, formats nationaux) → message bloqué (protection de la commission 10%).
    - **Page CGU** (`/cgu/`) avec les règles (rôles, anti-contournement, commission, sanctions) + bannière de rappel dans la messagerie.
    - Suite portée à **78 tests OK**.
18. **Monétisation — abonnements prestataires (freemium)** :
    - Plans : **Gratuit** (0 FCFA, 3 propositions/mois), **Standard** (2 000 FCFA, 15/mois), **Pro** (5 000 FCFA, illimité) — constantes `PLAN_*` + `ABONNEMENT_DUREE_JOURS=30`.
    - Modèle `Abonnement` (accounts) avec statuts `en_attente`/`actif`/`refuse` (migration `0005`) : le prestataire demande un plan + déclare son paiement (`/abonnement/`), l'**admin confirme** dans le back-office (`abonnements/`).
    - Activation : `User.plan` + `date_debut_plan` + `date_fin_plan` (période 30 j) ; `plan_effectif()` retombe sur Gratuit si la période est expirée ; quota mensuel via `propositions_du_mois()`.
    - **Blocage du quota** dans `soumettre_proposition` (3/mois en Gratuit) avec redirection vers la page abonnement ; badges plan sur profil/prestataires ; carte alerte « Abonnements à confirmer » sur le dashboard ; CGU §5 bis.
    - seed_demo : yves (Pro actif) + nassirou (demande Standard en attente). Suite portée à **91 tests OK**.
19. **Renforcement UX & notifications** :
    - **Cartes d'abonnement cliquables** (sélection du plan par carte, radio cachée) ; quota **fixe par plan** (Gratuit = 3) ; recharge affichée **le 1er du mois** (`User.prochaine_recharge()`) ; formulaire masqué si Pro actif ; bandeau quota + recharge sur le catalogue.
    - **Barre latérale verticale fixe** pour toutes les pages connectées (pleine hauteur, type Gemini : sidebar à gauche + contenu à droite ; par rôle, active link ; drawer latéral sur mobile via `sidebar-toggle`/`sidebar-scrim`, bouton ☰) ; header réduit (logo, rôle, 🔔, déconnexion).
    - **Système de notifications** (`Notification` accounts, helper `creer_notification`/`notifier_staff`, context processor `nb_notifications`) : cloche + compteur + page `/notifications/`. Déclencheurs : abonnement confirmé/refusé, commission confirmée (→ prestataire) ; proposition acceptée (→ prestataire) ; demande validée/supprimée (→ client) ; nouvelle demande d'abonnement, commission déclarée, prestataire à vérifier, demande à modérer (→ staff). seed_demo : notification pour nassirou.
    - **« Espèces » retiré** des moyens de paiement (abonnement ET paiement mission → Mobile Money / Virement uniquement).
    - Suite portée à **106 tests OK**.

20. **P0 — Mobile Money FedaPay (escrow, P0 terminé)** :
    - Nouvelle app **`apps/paiements/`** : provider abstraction (`providers/base.py`), implémentation FedaPay sandbox (`providers/fedapay.py` — collecte via redirection `payment_url`, reversement via `/payouts`, webhook `X-FEDAPAY-SIGNATURE` HMAC-SHA256).
    - Clés sandbox (`FEDAPAY_*`) dans `.env` (jamais commité) ; `FEDAPAY_MODES_OPERATEURS` : `mtn_momo`→`mtn_open`, `moov`→`moov`, `celtis`→`sbin`.
    - 11 tests unitaires (mock) + vérification live sandbox : transaction créée + `payment_url` récupérée + statut `pending`.
    - Prochaine étape = P1 (commission **5 %**, modèle `Paiement` enrichi, clôture & payout).
    - Suite portée à **118 tests OK**.

21. **P1 — Commission 5 % + modèle Paiement escrow (terminé)** :
    - `COMMISSION_POURCENT = 5` (settings) ; texte 10% → 5% partout (CGU, dashboard, messagerie, back-office, docstrings).
    - Modèle `Paiement` enrichi : méthodes `mtn_momo` / `moov` / `celtis` / `virement`, statuts `en_cours` / `en_attente` / `paye` / `echec`, `reference_txn` (unique) et `donnees_webhook` (JSON) ; `Commission.reference_payout` (reversement FedaPay).
    - Migration `0004` incluant une **data migration** : `mobile_money`/`especes` → `mtn_momo`/`virement`.
    - seed_demo : commission calculée via `settings.COMMISSION_POURCENT`. Suite toujours à **118 tests OK**.
    - Prochaine étape = P2 : flux escrow (initier_paiement remplace enregistrer_paiement, clore bloque si impayé, payout 95 % → commission payée automatiquement).

22. **P2 — Flux escrow complet (paiement à l'avance, terminé)** :
    - **`apps/paiements/services.py`** : `prix_a_payer`, `mission_payee`, `initier_collecte_mission` (collecte FedaPay → `payment_url`, ou virement/repli local en `en_attente`), `confirmer_paiement`/`eclater_paiement` (statuts via vérification), `reverser_prestataire` (payout 95 % → `Commission` payée auto avec `reference_payout` ; repli manuel si reversement indisponible).
    - Vue `initier_paiement` (remplace `enregistrer_paiement`) : choix opérateur (MTN/Moov/Celtis/Virement), redirection vers la page de paiement FedaPay ; vue `verifier_paiement` (interroge FedaPay, `approved` → `paye`, `failed` → `echec`) ; page de retour `paiements/retour/` (app `apps/paiements/urls.py`).
    - **Clôture bloquée** si mission non réglée ; à la clôture : reversement du solde + commission payée automatiquement (message à l'équipe si reversement impossible).
    - **Back-office** : page `paiements/` + confirmation des paiements `en_attente` (virement/repli) → `paye` + notification prestataire ; carte dashboard « Paiements à confirmer ».
    - seed_demo : paiement escrow payé sur la mission m7 ; formulaire `PaiementForm` supprimé. Suite portée à **127 tests OK**.
    - Prochaine étape = P3 : webhook FedaPay signé + idempotence pour confirmation automatique.

23. **P3 — Webhook FedaPay signé + idempotence (terminé)** :
    - Modèle **`EvenementWebhook`** (`apps/paiements/`) : journal de réception (clé unique stable → **anti double-traitement**) — migration `0001_initial`, migration appliquée.
    - Extension du provider : `verifier_webhook(corps, signature)` (schéma `t=<ts>,v1=<hmac sha256>`, anti-rejeu 5 min, `FEDAPAY_WEBHOOK_SECRET`).
    - Endpoint `POST /paiements/webhook/` (`csrf_exempt`, aucune session) : vérifie la signature → `400` si invalide, traite l'événement atomiquement (journal + action dans la même transaction, échec = rollback + renvoi autorisé).
    - `services.traiter_webhook(evenement)` : événements `transaction.approved` → `confirmer_paiement` (statut `paye` + notification prestataire) ; `transaction.declined/canceled/…` → `eclater_paiement` (`echec`) ; `payout.failed` → commission remise en `en_attente` + alerte staff ; événement inconnu ou transaction inconnue → journalisé et accepté (200, évite les renvois inutiles).
    - Suite portée à **133 tests OK**. ⚠️ Config à terminer côté FedaPay : pointer le webhook du dashboard vers `/paiements/webhook/` et renseigner `FEDAPAY_WEBHOOK_SECRET` dans `.env`.
    - Correctif : `initier_collecte` envoie désormais `customer.firstname`/`lastname` (prénom/nom du client ; repli sur le username, sinon « Client TechConnect ») — la page de paiement FedaPay sandbox exigeait ces champs et les transactions étaient rejetées. `seed_demo` remplit aussi prénom/nom des comptes de démo.
    - Prochaine étape = P4 : retrait du flux de commission manuel (déjà automatique à la clôture).

## 🔲 RESTE À FAIRE (roadmap)

**Logiciel (MVP)**
- [x] ~~Backend BDD + modèles + vues~~ (fait)
- [x] ~~README.md~~ (fait)
- [x] ~~Données de démo~~ (`python3 manage.py seed_demo`)
- [x] ~~Tests automatisés~~ (43 tests OK : accounts, demandes, propositions, messagerie, admin_panel)
- [x] ~~Formulaire profil~~ (édition des infos, avatar, bio)
- [x] ~~Back-office : modération des demandes (validation `en_attente`), gestion des litiges~~
- [x] ~~Paiements~~ (accord direct MVP : enregistrement d'un paiement par le client) — escrow / Mobile Money en Phase future

**Sécurité & production (Phases 5-6)**
- [x] ~~Renforcement n°1 : anti brute-force connexion, validation uploads (avatar)~~
- [x] ~~Sauvegardes régulières MySQL (cron 03h30, rotation 14 jours)~~
- [ ] Déploiement Linux + Nginx + HTTPS
- [ ] Phase bêta fermée avec premiers utilisateurs au Bénin

**Mobile (Phase 2)**
- [ ] Application Android/iOS avec Flutter (API REST Django à exposer)

## 🧪 Convention de commits

```
<type> <sujet concis>
ex : Feat backend : … | Fix auth : … | Style : … | Docs : …
```
Historique actuel : `fc9e230` (init) → `20edad3` (backend+BDD) → `770bc83` (vues) → `aad88d5` (design) → `7e08172` (fix rôles).