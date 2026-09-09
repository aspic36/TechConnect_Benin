"""
Commande de management : seed_demo.

Peuple la base de données avec des donnees de demonstration realistes
(cinq utilisateurs, sept categories, sept demandes a differents stades,
propositions, missions, messages et evaluations) afin de pouvoir tester
l'ensemble des fonctionnalites de TechConnect Benin sans saisie manuelle.

Utilisation :
    python3 manage.py seed_demo

Attention : la commande supprime d'abord les comptes de démo existants
puis recree l'ensemble des objets.
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import Abonnement, User
from apps.demandes.models import Categorie, Demande
from apps.messagerie.models import Message
from apps.propositions.models import Commission, Evaluation, Mission, Proposition

# Mot de passe unique pour tous les comptes de demonstration
MOT_DE_PASSE = 'Demo@2026!'

# Categories de services proposées sur la plateforme
CATEGORIES = [
    ('Développement web', 'developpement-web'),
    ('Développement mobile', 'developpement-mobile'),
    ('Réseau & Infrastructure', 'reseau-infrastructure'),
    ('Automatisation', 'automatisation'),
    ('Sécurité informatique', 'securite'),
    ('Maintenance & Support', 'maintenance'),
    ('Design & Communication', 'design-communication'),
]

# Logins des utilisateurs de démonstration
UTILISATEURS_DEMO = [
    'amina', 'codjo', 'yves', 'farida', 'nassirou',
]


class Command(BaseCommand):
    """Commande de management Django : generation de donnees de demonstration."""

    help = 'Crée des données de démonstration (utilisateurs, demandes, propositions, missions…).'

    def handle(self, *args, **options):
        """Point d'entree de la commande seed_demo.

        La methode suit l'ordre logique du cycle metier :
        1. Nettoyage des anciennes donnees de démo
        2. Creation / obtain des categories
        3. Creation des utilisateurs (2 clients, 3 prestataires)
        4. Creation des demandes a differents statuts
        5. Creation des propositions
        6. Creation des missions (en cours + terminee)
        7. Creation de messages de messagerie
        8. Creation d'evaluations croisees
        """
        # --- 1. Nettoyage ---
        self.stdout.write('Nettoyage des données de démo existantes…')
        User.objects.filter(username__in=UTILISATEURS_DEMO).delete()

        # --- 2. Categories (get_or_create pour idempotence) ---
        for nom, slug in CATEGORIES:
            Categorie.objects.get_or_create(nom=nom, slug=slug)
        self.stdout.write('Catégories prêtes.')

        # --- 3. Utilisateurs de démo ---
        maintenant = timezone.now()
        amina = User.objects.create_user(
            username='amina', password=MOT_DE_PASSE, role=User.Role.CLIENT,
            phone='97 10 22 33', ville='Cotonou',
            company_name='', bio='Gérante d\'un salon de coiffure à Cotonou.',
        )
        codjo = User.objects.create_user(
            username='codjo', password=MOT_DE_PASSE, role=User.Role.CLIENT,
            phone='95 44 55 66', ville='Porto-Novo',
            company_name='Association Espoir', bio='Secrétaire général de l\'association Espoir.',
        )
        yves = User.objects.create_user(
            username='yves', password=MOT_DE_PASSE, role=User.Role.PRESTATAIRE,
            phone='91 88 99 00', ville='Abomey-Calavi', company_name='Yves Tech Services',
            bio='Développeur web et mobile, 6 ans d\'expérience.', is_verified=True,
            plan=User.Plan.PRO, date_debut_plan=maintenant - timedelta(days=5),
            date_fin_plan=maintenant + timedelta(days=25),
        )
        farida = User.objects.create_user(
            username='farida', password=MOT_DE_PASSE, role=User.Role.PRESTATAIRE,
            phone='90 12 34 56', ville='Cotonou', company_name='Farida Digital',
            bio='Webdesigner et intégratrice, passionnée de UI/UX.', is_verified=True,
        )
        nassirou = User.objects.create_user(
            username='nassirou', password=MOT_DE_PASSE, role=User.Role.PRESTATAIRE,
            phone='94 56 78 90', ville='Parakou', company_name='Nassirou Réseaux',
            bio='Ingénieur réseaux et télécoms.',
        )
        # nassirou a demandé un plan Standard (demande laissée en attente pour le back-office).
        Abonnement.objects.create(
            prestataire=nassirou, plan=User.Plan.STANDARD, montant=2000,
            methode=Abonnement.Methode.MOBILE_MONEY,
            date_demande=maintenant - timedelta(days=1),
        )
        self.stdout.write('Utilisateurs de démo créés.')

        # --- 4. Recuperation des categories par slug ---
        web = Categorie.objects.get(slug='developpement-web')
        mobile = Categorie.objects.get(slug='developpement-mobile')
        securite = Categorie.objects.get(slug='securite')
        maintenance = Categorie.objects.get(slug='maintenance')
        automatisation = Categorie.objects.get(slug='automatisation')

        # --- 5. Demandes a differents statuts du cycle de vie ---
        d1 = Demande.objects.create(
            client=amina, categorie=web,
            titre='Création d\'un site vitrine pour mon salon de coiffure',
            description='Je veux un site élégant qui présente mes services (coupe, tresses, soins), '
                        'mes tarifs et un formulaire de réservation en ligne. Style moderne et coloré.',
            budget_min=80000, budget_max=150000, lieu='Cotonou', statut=Demande.Statut.EN_COURS,
        )
        d2 = Demande.objects.create(
            client=amina, categorie=securite,
            titre='Audit de sécurité du réseau de notre cabinet médical',
            description='Nous souhaitons un audit complet de notre réseau local, la sécurisation du Wi-Fi '
                        'et une formation des employés aux bonnes pratiques.',
            budget_min=150000, budget_max=250000, lieu='Cotonou', statut=Demande.Statut.EN_ATTENTE,
        )
        d3 = Demande.objects.create(
            client=codjo, categorie=web,
            titre='Refonte d\'une boutique e-commerce avec paiement MTN MoMo',
            description='Refonte complète de notre boutique en ligne : catalogue, panier, paiement Mobile '
                        'Money (MTN MoMo / Moov), gestion de stock et livraison à Cotonou.',
            budget_min=300000, budget_max=600000, lieu='Cotonou', a_distance=True,
            statut=Demande.Statut.EN_COURS,
        )
        d4 = Demande.objects.create(
            client=codjo, categorie=maintenance,
            titre='Maintenance de 20 postes informatiques (association)',
            description='Installation Windows, mise à jour, nettoyage antivirus et maintenance préventive '
                        'de 20 postes au siège de l\'association à Porto-Novo.',
            budget_min=50000, budget_max=100000, lieu='Porto-Novo', statut=Demande.Statut.EN_COURS,
        )
        d5 = Demande.objects.create(
            client=codjo, categorie=automatisation,
            titre='Automatiser la facturation avec Excel / Power Query',
            description='Créer un modèle de facturation automatique (n° de facture, TVA, totaux) et '
                        'l\'automatisation des suivis mensuels. Travail à distance possible.',
            budget_min=60000, budget_max=120000, a_distance=True, statut=Demande.Statut.EN_COURS,
        )
        d6 = Demande.objects.create(
            client=amina, categorie=mobile,
            titre='Développer une application mobile de gestion de stock',
            description='Application Android simple pour suivre mes produits (photos, quantités, alertes de '
                        'rupture) dans mes deux boutiques.',
            budget_min=400000, budget_max=700000, lieu='Cotonou', statut=Demande.Statut.MISSION_ACTIVE,
        )
        d7 = Demande.objects.create(
            client=codjo, categorie=web,
            titre='Site vitrine pour une vendeuse de jus naturels',
            description='Petit site vitrine avec menu des jus, tarifs et contact WhatsApp. Livré en 10 jours.',
            budget_min=80000, budget_max=120000, lieu='Porto-Novo', statut=Demande.Statut.CLOTUREE,
        )
        self.stdout.write('Demandes de démo créées.')

        # --- 6. Propositions soumises par les prestataires ---
        p1a = Proposition.objects.create(
            demande=d1, prestataire=yves, prix=135000, delais_jours=15,
            message='Je peux livrer un site vitrine moderne avec réservation en ligne dans les 2 semaines.',
        )
        p1b = Proposition.objects.create(
            demande=d1, prestataire=farida, prix=120000, delais_jours=20,
            message='Design élégant et coloré, intégration d\'un formulaire de réservation, hébergement inclus.',
        )
        p3a = Proposition.objects.create(
            demande=d3, prestataire=yves, prix=550000, delais_jours=45,
            message='Refonte complète avec paiement MTN MoMo intégré (API). Expérience en e-commerce.',
        )
        p3b = Proposition.objects.create(
            demande=d3, prestataire=nassirou, prix=420000, delais_jours=60,
            message='Je propose une solution e-commerce avec paiement par carte et Mobile Money.',
        )
        p4a = Proposition.objects.create(
            demande=d4, prestataire=farida, prix=90000, delais_jours=10,
            message='Intervention sur place à Porto-Novo, diagnostic et nettoyage complet des 20 postes.',
        )
        p5a = Proposition.objects.create(
            demande=d5, prestataire=yves, prix=80000, delais_jours=7,
            message='Je peux réaliser le modèle de facturation et l\'automatisation sous Excel (Power Query).',
        )
        # Proposals acceptees : ces prestataires declenchent la creation de missions
        p6a = Proposition.objects.create(
            demande=d6, prestataire=yves, prix=450000, delais_jours=30,
            message='Application Android de gestion de stock avec alertes de rupture. Je suis disponible.',
            statut=Proposition.Statut.ACCEPTEE,
        )
        p7a = Proposition.objects.create(
            demande=d7, prestataire=farida, prix=100000, delais_jours=10,
            message='Site vitrine simple avec menu des jus et contact WhatsApp.',
            statut=Proposition.Statut.ACCEPTEE,
        )
        self.stdout.write('Propositions de démo créées.')

        # --- 7. Missions (une en cours, une terminee avec evaluee) ---
        maintenant = timezone.now()
        m6 = Mission.objects.create(
            demande=d6, proposition=p6a, client=amina, prestataire=yves,
            statut=Mission.Statut.EN_COURS, date_debut=maintenant - timedelta(days=4),
        )
        m7 = Mission.objects.create(
            demande=d7, proposition=p7a, client=codjo, prestataire=farida,
            statut=Mission.Statut.TERMINEE,
            date_debut=maintenant - timedelta(days=40), date_fin=maintenant - timedelta(days=28),
        )
        self.stdout.write('Missions de démo créées.')

        # --- 8. Messages de messagerie (fil de conversation) ---
        Message.objects.create(
            mission=m6, expediteur=amina, contenu='Bonjour Yves, quand peux-tu commencer ?',
        )
        Message.objects.create(
            mission=m6, expediteur=yves,
            contenu='Bonjour Amina, je commence demain. Je te ferai un point d\'avancement chaque semaine.',
            lu=True,
        )
        Message.objects.create(
            mission=m6, expediteur=amina,
            contenu='Parfait, merci ! N\'oublie pas l\'alerte de rupture de stock, c\'est essentiel.',
            lu=True,
        )
        self.stdout.write('Messages de démo créés.')

        # --- 9. Evaluations croisees (client <-> prestataire) ---
        Evaluation.objects.create(
            mission=m7, auteur=codjo, cible=farida, note=5,
            commentaire='Excellent travail, site livré en avance et très soigné. Je recommande !',
        )
        Evaluation.objects.create(
            mission=m7, auteur=farida, cible=codjo, note=5,
            commentaire='Client très agréable et précis dans ses besoins.',
        )
        self.stdout.write('Évaluations de démo créées.')

        # --- 10. Commission plateforme (10% de la mission terinée m7) ---
        # Montant : 10% de 100000 FCFA = 10000 FCFA, à régler sous 7 jours.
        Commission.objects.create(
            mission=m7,
            montant=p7a.prix * 10 // 100,
            methode='virement',
            date_limite=maintenant + timedelta(days=2),
        )
        self.stdout.write('Commission de démo créée.')

        # --- 11. Notifications de démo (cloche) ---
        from apps.accounts.models import Notification
        Notification.objects.create(
            destinataire=nassirou,
            type=Notification.Type.ABONNEMENT,
            message='Ta demande d’abonnement Standard est en attente de confirmation.',
            lien='/abonnement/',
        )
        self.stdout.write('Notification de démo créée.')

        # --- 12. Message de succes ---
        self.stdout.write(self.style.SUCCESS(
            'Données de démo prêtes ! Comptes (mot de passe "Demo@2026!") : '
            'amina (client), codjo (client), yves (prestataire, plan Pro), '
            'farida (prestataire), nassirou (prestataire, abonnement Standard en attente).'
        ))
