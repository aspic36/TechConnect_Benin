# TechConnect Bénin — Architecture Technique

## 1. Vue d'ensemble

Plateforme béninoise de mise en relation entre **clients** (besoins informatiques) et **prestataires** (services informatiques). Application web Django + MySQL, déployée via Docker en développement.

```
                        ┌─────────────────────────────┐
                        │      Navigateur (Web)       │
                        │      HTML / CSS / JS        │
                        └──────────────┬──────────────┘
                                       │ HTTP (HTTPS en prod)
                                       ▼
                        ┌─────────────────────────────┐
                        │   Django (Python 3.14)      │
                        │  Templates + API REST      │
                        └──────────────┬──────────────┘
                                      │ PyMySQL (utf8mb4)
                                       ▼
                        ┌─────────────────────────────┐
                        │      MySQL 8.0 (Docker)     │
                        │   conteneur techconnect_db  │
                        │   port 3307 (hôte)          │
                        └─────────────────────────────┘
```

## 2. Stack technique

| Composant | Technologie | Version |
|---|---|---|
| Frontend | HTML5, CSS3, JavaScript (templates Django + Jinja2) | — |
| Backend | Python + Django (API REST) | Python 3.14 / Django 4.2 |
| Base de données | MySQL (conteneur Docker) | 8.0 |
| Connecteur BDD | PyMySQL | 1.2 |
| Admin BDD (dev) | Adminer (conteneur Docker) | port 8081 |
| Auth | Sessions / JWT, hachage des mots de passe (PBKDF2) | — |
| Déploiement (prod) | Linux, Nginx, HTTPS, sauvegardes MySQL | — |
| Mobile (Phase 2) | Flutter (Android/iOS) | — |

## 3. Schéma de la base de données

Base unique : **`techconnect_benin`** (jeu de caractères `utf8mb4`).

### 3.1 Entités et relations

```
┌──────────────┐       ┌──────────────────┐
│   accounts_user      │  demandes_categorie│
│  (User custom) │       └──────────────────┘
│   role         │             ▲
│   phone        │             │ FK categorie
│   ville        │             │ (SET_NULL)
│   is_verified  │       ┌──────────────────┐
└──────┬───────-─┘       │ demandes_demande  │
       │                 │ client -> User FK │
       │                 │ budget_min/max    │
       │                 │ lieu / a_distance │
       │                 │ urgence           │
       │                 │ statut            │
       │                 └───────┬───────────┘
       │                    FK demande │ (1 proposition)
       │                 ┌────────────▼──────────┐
       │                 │ propositions_proposition│
       │                 │ prestataire -> User FK │
       │                 │ prix / delais_jours    │
       │                 │ message / statut       │
       │                 └────────────┬───────────┘
       │                    FK proposition (1 mission)
       │                 ┌────────────▼──────────┐
       │                 │  propositions_mission  │
       │                 │ client / prestataire   │
       │                 │ statut                 │
       │                 └───────┬──────────┬─────┘
       │                         │          │
       │            FK mission   │          │ FK mission
       │       ┌─────────────────▼──┐   ┌───▼────────────────┐
       │       │ propositions_evaluation│  │ propositions_paiement│
       │       │ auteur / cible -> User │  │ montant / méthode    │
       │       │ note 1-5 / commentaire │  │ statut               │
       │       └─────────────────────┘   └──────────────────────┘
       │                     FK mission (messages)
       │                 ┌────────────▼──────────┐
       └────────────────►│  messagerie_message    │
                         │ expediteur -> User FK  │
                         │ contenu / lu           │
                         └────────────────────────┘
```

### 3.2 Détail des tables

#### accounts_user
| Champ | Type | Contraintes |
|---|---|---|
| hérite de AbstractUser | — | username, email, password (haché) |
| role | Char(20) | `client` / `prestataire` / `admin` |
| phone | Char(20) | unique, nullable (vérification téléphone) |
| company_name | Char(150) | blank |
| ville | Char(100) | blank |
| bio | Text | blank |
| avatar | ImageField | upload → avatars/ |
| is_verified | Bool | validation administrateur |

#### demandes_categorie
| Champ | Type | Contraintes |
|---|---|---|
| nom | Char(100) | unique |
| slug | SlugField(120) | unique |

#### demandes_demande
| Champ | Type | Contraintes |
|---|---|---|
| client | FK → accounts_user | CASCADE, related = `demandes` |
| categorie | FK → demandes_categorie | SET_NULL, nullable |
| titre | Char(200) | — |
| description | Text | — |
| budget_min / budget_max | Decimal(12) | nullable, FCFA |
| lieu | Char(100) | blank |
| a_distance | Bool | travail à distance |
| urgence | Bool | — |
| statut | Char(20) | en_attente / en_cours / mission_active / cloturee |
| date_creation | DateTime | auto |

#### propositions_proposition
| Champ | Type | Contraintes |
|---|---|---|
| demande | FK → demandes_demande | CASCADE, related = `propositions` |
| prestataire | FK → accounts_user | CASCADE, related = `propositions` |
| prix | Decimal(12) | FCFA |
| delais_jours | PositiveInt | — |
| message | Text | blank |
| statut | Char(20) | envoyee / acceptee / refusee |

#### propositions_mission
| Champ | Type | Contraintes |
|---|---|---|
| demande | OneToOne → demandes_demande | lié à la demande retenue |
| proposition | OneToOne → propositions_proposition | proposition acceptée |
| client | FK → accounts_user | related = `missions_client` |
| prestataire | FK → accounts_user | related = `missions_prestataire` |
| statut | Char(20) | en_cours / terminee / cloturee / litige |
| date_debut / date_fin | DateTime | nullable |

#### propositions_evaluation
| Champ | Type | Contraintes |
|---|---|---|
| mission | FK → propositions_mission | CASCADE, related = `evaluations` |
| auteur | FK → accounts_user | l'évaluateur |
| cible | FK → accounts_user | l'évalué |
| note | PositiveSmallInt | CHECK 1-5 (`note_1_5`) |
| commentaire | Text | blank |

#### propositions_paiement
| Champ | Type | Contraintes |
|---|---|---|
| mission | FK → propositions_mission | CASCADE, related = `paiements` |
| montant | Decimal(12) | FCFA |
| methode | Char(20) | mobile_money / virement / especes |
| statut | Char(20) | en_attente / paye |

#### messagerie_message
| Champ | Type | Contraintes |
|---|---|---|
| mission | FK → propositions_mission | CASCADE, related = `messages` |
| expediteur | FK → accounts_user | related = `messages_envoyes` |
| contenu | Text | — |
| lu | Bool | défaut False |
| date_creation | DateTime | auto |

## 4. Cycle de vie d'une mission

```
Demande (en_attente)
   │ validation
   ▼
Demande (en_cours) ────► Propositions reçues (envoyee)
   │                          │
   │                    acceptee / refusee
   ▼                          ▼
Mission créée (en_cours) ◄── Proposition acceptée
   │ messagerie liée
   ├─ terminee  ──►  Évaluations (note 1-5)
   ├─ cloturee
   └─ litige  ───► médiation admin (Phase back-office)

Paiements : accord direct MVP / escrow Phase future
```

## 5. Règles métier clés

1. **Confidentialité** : un client ne voit **que ses propres demandes** ; les prestataires voient **toutes** les demandes publiques du catalogue (sans données personnelles du client).
2. **Rôles** : imposés à l'inscription (client ≠ prestataire). Un seul compte = un seul rôle principal.
3. **Accès mission** : la messagerie n'est accessible qu'aux parties d'une mission.
4. **Évaluation** : uniquement après une mission (note 1 à 5 + commentaire).
5. **Vérification** : prestataires vérifiés par l'admin (`is_verified`) avant mise en avant.

## 6. Sécurité

- Mots de passe hachés (PBKDF2 par défaut Django)
- Protection CSRF (middleware Django)
- Protection injections SQL (ORM / requêtes paramétrées)
- Échappement XSS (templates Django auto-escape)
- HTTPS obligatoire en production + Nginx
- Sauvegardes régulières de MySQL (volumes Docker)
- Secrets dans `.env` uniquement (jamais commités — `.gitignore`)

## 7. Configuration de connexion (développement)

| Paramètre | Valeur |
|---|---|
| Moteur | `django.db.backends.mysql` (via PyMySQL) |
| Base | `techconnect_benin` |
| Utilisateur | `techconnect_user` |
| Hôte | `127.0.0.1` |
| Port | `3307` (mappé → 3306 du conteneur) |
| Charset | `utf8mb4` |

Variable d'environnement : `config/__init__.py` appelle `pymysql.install_as_MySQLdb()` pour brancher PyMySQL sur l'interface MySQLdb de Django.