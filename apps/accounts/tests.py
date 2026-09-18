from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .forms import InscriptionForm
from .models import Abonnement, Notification, Projet, User


class InscriptionTests(TestCase):

    def test_formulaire_limite_aux_deux_roles(self):
        form = InscriptionForm()
        roles = [valeur for valeur, _ in form.fields['role'].choices]
        self.assertEqual(roles, [User.Role.CLIENT, User.Role.PRESTATAIRE])

    def test_inscription_client(self):
        reponse = self.client.post(reverse('accounts:inscription'), {
            'username': 'nouvelclient',
            'password1': 'Passw0rd!',
            'password2': 'Passw0rd!',
            'role': User.Role.CLIENT,
            'phone': '97000011',
            'ville': 'Cotonou',
        })
        self.assertEqual(reponse.status_code, 302)
        utilisateur = User.objects.get(username='nouvelclient')
        self.assertEqual(utilisateur.role, User.Role.CLIENT)

    def test_inscription_prestataire(self):
        reponse = self.client.post(reverse('accounts:inscription'), {
            'username': 'nouveaupresta',
            'password1': 'Passw0rd!',
            'password2': 'Passw0rd!',
            'role': User.Role.PRESTATAIRE,
            'phone': '97000012',
        })
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(User.objects.get(username='nouveaupresta').role, User.Role.PRESTATAIRE)

    def test_inscription_sans_role_admin(self):
        self.client.post(reverse('accounts:inscription'), {
            'username': 'pasadmin',
            'password1': 'Passw0rd!',
            'password2': 'Passw0rd!',
            'role': 'admin',
        })
        self.assertFalse(User.objects.filter(username='pasadmin').exists())


class ConnexionTests(TestCase):

    def setUp(self):
        self.client_u = User.objects.create_user(
            username='client1', password='Passw0rd!', role=User.Role.CLIENT)
        self.presta = User.objects.create_user(
            username='presta1', password='Passw0rd!', role=User.Role.PRESTATAIRE)

    def test_connexion_valide(self):
        self.assertTrue(self.client.login(username='client1', password='Passw0rd!'))

    def test_connexion_invalide(self):
        self.assertFalse(self.client.login(username='client1', password='mauvais'))

    def test_accueil_anon(self):
        reponse = self.client.get(reverse('accounts:accueil'))
        self.assertEqual(reponse.status_code, 200)

    def test_anonyme_redirige_vers_la_page_de_connexion(self):
        reponse = self.client.get(reverse('accounts:abonnement'))
        self.assertRedirects(
            reponse, reverse('accounts:connexion') + '?next=/abonnement/')

    def test_accueil_redirige_client(self):
        self.client.login(username='client1', password='Passw0rd!')
        reponse = self.client.get(reverse('accounts:accueil'))
        self.assertRedirects(reponse, reverse('demandes:mes_demandes'))

    def test_accueil_redirige_prestataire(self):
        self.client.login(username='presta1', password='Passw0rd!')
        reponse = self.client.get(reverse('accounts:accueil'))
        self.assertRedirects(reponse, reverse('demandes:catalogue'))

    def test_profil_necessite_connexion(self):
        reponse = self.client.get(reverse('accounts:profil'))
        self.assertEqual(reponse.status_code, 302)

    def test_deconnexion(self):
        self.client.login(username='client1', password='Passw0rd!')
        self.client.get(reverse('accounts:deconnexion'))
        reponse = self.client.get(reverse('accounts:profil'))
        self.assertEqual(reponse.status_code, 302)

    def test_modification_profil(self):
        self.client.login(username='client1', password='Passw0rd!')
        reponse = self.client.post(reverse('accounts:modifier_profil'), {
            'email': 'nouveau@mail.org',
            'phone': '97000111',
            'ville': 'Cotonou',
            'bio': 'Une bio de test',
        })
        self.assertRedirects(reponse, reverse('accounts:profil'))
        self.client_u.refresh_from_db()
        self.assertEqual(self.client_u.bio, 'Une bio de test')
        self.assertEqual(self.client_u.ville, 'Cotonou')


class ValidationAvatarTests(TestCase):

    def setUp(self):
        self.utilisateur = User.objects.create_user(
            username='testavatar', password='Passw0rd!', role=User.Role.CLIENT)
        self.client.login(username='testavatar', password='Passw0rd!')

    def _poster_avatar(self, nom, contenu, type_mime):
        from django.core.files.uploadedfile import SimpleUploadedFile
        return self.client.post(reverse('accounts:modifier_profil'), {
            'avatar': SimpleUploadedFile(nom, contenu, content_type=type_mime),
        })

    def test_extension_interdite_refusee(self):
        reponse = self._poster_avatar('fichier.exe', b'non-une-image', 'application/x-msdownload')
        self.assertEqual(reponse.status_code, 200)
        self.utilisateur.refresh_from_db()
        self.assertFalse(self.utilisateur.avatar)

    def test_image_valide_acceptee(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image
        from io import BytesIO
        buffer = BytesIO()
        Image.new('RGB', (10, 10), 'indigo').save(buffer, format='PNG')
        reponse = self.client.post(reverse('accounts:modifier_profil'), {
            'avatar': SimpleUploadedFile('avatar.png', buffer.getvalue(), content_type='image/png'),
        })
        self.assertRedirects(reponse, reverse('accounts:profil'))
        self.utilisateur.refresh_from_db()
        self.assertTrue(self.utilisateur.avatar)

    def test_avatar_trop_lourd_refuse(self):
        from django.core.exceptions import ValidationError
        from .validators import TAILLE_MAX_AVATAR_OCTETS, valider_taille_avatar

        class Fichier:
            def __init__(self, size):
                self.size = size

        with self.assertRaises(ValidationError):
            valider_taille_avatar(Fichier(TAILLE_MAX_AVATAR_OCTETS + 1))
        valider_taille_avatar(Fichier(TAILLE_MAX_AVATAR_OCTETS))


class ProtectionBruteForceTests(TestCase):

    def setUp(self):
        cache.clear()
        User.objects.create_user(
            username='victime', password='Passw0rd!', role=User.Role.CLIENT)

    def tearDown(self):
        cache.clear()

    def _tentative(self, password):
        return self.client.post(reverse('accounts:connexion'), {
            'username': 'victime', 'password': password,
        })

    def test_connexion_bloquee_apres_cinq_echecs(self):
        for _ in range(5):
            self._tentative('mauvais')
        response = self._tentative('Passw0rd!')
        self.assertNotContains(response, 'Content de te revoir')
        self.assertContains(response, 'Trop de tentatives échouées')

    def test_succes_reinitialise_le_compteur(self):
        self._tentative('mauvais')
        self._tentative('Passw0rd!')
        reponse = self.client.get(reverse('accounts:profil'))
        self.assertEqual(reponse.status_code, 200)

    def test_utilisateur_authentifie_ignore(self):
        self.client.login(username='victime', password='Passw0rd!')
        reponse = self.client.post(reverse('accounts:connexion'), {
            'username': 'victime', 'password': 'Passw0rd!',
        })
        self.assertEqual(reponse.status_code, 302)


class AbonnementTests(TestCase):

    def setUp(self):
        self.prestataire = User.objects.create_user(
            username='presta', password='Passw0rd!', role=User.Role.PRESTATAIRE)
        self.client_ = User.objects.create_user(
            username='client', password='Passw0rd!', role=User.Role.CLIENT)

    def _post_demande(self, plan='standard', methode='mobile_money'):
        return self.client.post(reverse('accounts:abonnement'), {
            'plan': plan, 'methode': methode,
        })

    def test_page_abonnement_reservee_prestataire(self):
        self.client.login(username='client', password='Passw0rd!')
        reponse = self.client.get(reverse('accounts:abonnement'))
        self.assertRedirects(reponse, reverse('demandes:mes_demandes'))

    def test_page_abonnement_accessible_prestataire(self):
        self.client.login(username='presta', password='Passw0rd!')
        reponse = self.client.get(reverse('accounts:abonnement'))
        self.assertEqual(reponse.status_code, 200)

    def test_demander_abonnement_cree_demande_en_attente(self):
        self.client.login(username='presta', password='Passw0rd!')
        reponse = self._post_demande()
        self.assertEqual(reponse.status_code, 302)
        demande = Abonnement.objects.get(prestataire=self.prestataire)
        self.assertEqual(demande.statut, Abonnement.Statut.EN_ATTENTE)
        self.assertEqual(demande.montant, 2000)
        self.assertEqual(demande.plan, User.Plan.STANDARD)

    def test_une_seule_demande_en_attente_possible(self):
        self.client.login(username='presta', password='Passw0rd!')
        self._post_demande()
        self._post_demande(plan='pro')
        self.assertEqual(Abonnement.objects.filter(prestataire=self.prestataire).count(), 1)

    def test_plan_pro_quota_illimite(self):
        self.prestataire.plan = User.Plan.PRO
        self.prestataire.date_debut_plan = timezone.now()
        self.prestataire.date_fin_plan = timezone.now() + timezone.timedelta(days=30)
        self.prestataire.save()
        self.assertEqual(self.prestataire.plan_effectif(), User.Plan.PRO)
        self.assertIsNone(self.prestataire.quota_mensuel())
        autorise, _, quota = self.prestataire.peut_proposer()
        self.assertTrue(autorise)
        self.assertIsNone(quota)

    def test_plan_expire_retombe_sur_gratuit(self):
        self.prestataire.plan = User.Plan.PRO
        self.prestataire.date_debut_plan = timezone.now() - timezone.timedelta(days=40)
        self.prestataire.date_fin_plan = timezone.now() - timezone.timedelta(days=10)
        self.prestataire.save()
        self.assertEqual(self.prestataire.plan_effectif(), User.Plan.GRATUIT)
        self.assertEqual(self.prestataire.quota_mensuel(), 3)

    def test_plan_standard_quota_quinze(self):
        self.prestataire.plan = User.Plan.STANDARD
        self.prestataire.date_fin_plan = timezone.now() + timezone.timedelta(days=10)
        self.prestataire.save()
        self.assertEqual(self.prestataire.quota_mensuel(), 15)

    def test_demande_en_attente_visible_sur_page(self):
        Abonnement.objects.create(
            prestataire=self.prestataire, plan=User.Plan.PRO, montant=5000,
            methode=Abonnement.Methode.VIREMENT)
        self.client.login(username='presta', password='Passw0rd!')
        reponse = self.client.get(reverse('accounts:abonnement'))
        self.assertContains(reponse, 'en attente')
        self.assertNotContains(reponse, 'Changer de plan')

    def test_page_gratuit_affiche_trois_propositions(self):
        self.client.login(username='presta', password='Passw0rd!')
        reponse = self.client.get(reverse('accounts:abonnement'))
        self.assertContains(reponse, '3 propositions par mois')

    def test_plan_pro_cache_le_formulaire(self):
        self.prestataire.plan = User.Plan.PRO
        self.prestataire.date_debut_plan = timezone.now()
        self.prestataire.date_fin_plan = timezone.now() + timezone.timedelta(days=20)
        self.prestataire.save()
        self.client.login(username='presta', password='Passw0rd!')
        reponse = self.client.get(reverse('accounts:abonnement'))
        self.assertContains(reponse, 'déjà sur le plan Pro')
        self.assertNotContains(reponse, 'Changer de plan')

    def test_demande_abonnement_notifie_le_staff(self):
        staff = User.objects.create_user(
            username='staff', password='Passw0rd!', role=User.Role.CLIENT, is_staff=True)
        self.client.login(username='presta', password='Passw0rd!')
        self._post_demande()
        self.assertTrue(Notification.objects.filter(
            destinataire=staff, type='abonnement').exists())


class NotificationTests(TestCase):

    def setUp(self):
        self.client_u = User.objects.create_user(
            username='client', password='Passw0rd!', role=User.Role.CLIENT)
        self.presta = User.objects.create_user(
            username='presta', password='Passw0rd!', role=User.Role.PRESTATAIRE)

    def test_creer_notification(self):
        from .notifications import creer_notification
        creer_notification([self.presta, self.client_u], 'Message', 'systeme')
        self.assertEqual(Notification.objects.count(), 2)

    def test_notifier_staff(self):
        staff = User.objects.create_user(
            username='staff', password='Passw0rd!', role=User.Role.CLIENT, is_staff=True)
        from .notifications import notifier_staff
        notifier_staff('Alerte interne', 'systeme')
        self.assertEqual(Notification.objects.filter(destinataire=staff).count(), 1)

    def test_page_notifications_liste_et_compteur(self):
        Notification.objects.create(destinataire=self.client_u, message='Nouvelle alerte', type='systeme')
        self.client.login(username='client', password='Passw0rd!')
        reponse = self.client.get(reverse('accounts:notifications'))
        self.assertContains(reponse, 'Nouvelle alerte')
        self.assertEqual(reponse.context['nb_notifications'], 1)

    def test_marquer_toutes_lues(self):
        Notification.objects.create(destinataire=self.client_u, message='x', type='systeme')
        self.client.login(username='client', password='Passw0rd!')
        self.client.get(reverse('accounts:marquer_lues'))
        self.client_u.refresh_from_db()
        self.assertTrue(Notification.objects.filter(destinataire=self.client_u).filter(est_lue=True).count() == 1)


class PortfolioTests(TestCase):

    def setUp(self):
        self.presta = User.objects.create_user(
            username='presta', password='Passw0rd!', role=User.Role.PRESTATAIRE)
        self.client_ = User.objects.create_user(
            username='client', password='Passw0rd!', role=User.Role.CLIENT)

    def test_page_portfolio_reservee_prestataire(self):
        self.client.login(username='client', password='Passw0rd!')
        reponse = self.client.get(reverse('accounts:portfolio'))
        self.assertRedirects(reponse, reverse('demandes:catalogue'))

    def test_ajouter_projet_au_portfolio(self):
        self.client.login(username='presta', password='Passw0rd!')
        reponse = self.client.post(reverse('accounts:portfolio'), {
            'titre': 'Site vitrine pour une PME',
            'description': 'Réalisé en Django',
            'url': 'https://example.com',
        })
        self.assertRedirects(reponse, reverse('accounts:portfolio'))
        projet = Projet.objects.get(prestataire=self.presta)
        self.assertEqual(projet.titre, 'Site vitrine pour une PME')

    def test_supprimer_projet(self):
        projet = Projet.objects.create(
            prestataire=self.presta, titre='Ancien projet')
        self.client.login(username='presta', password='Passw0rd!')
        self.client.get(reverse('accounts:supprimer_projet', args=[projet.pk]))
        self.assertFalse(Projet.objects.filter(pk=projet.pk).exists())

    def test_page_profil_public_prestataire(self):
        from apps.demandes.models import Categorie
        categorie = Categorie.objects.create(nom='Web', slug='web')
        self.presta.competences.add(categorie)
        self.client.login(username='client', password='Passw0rd!')
        reponse = self.client.get(reverse('accounts:profil_prestataire', args=[self.presta.pk]))
        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, 'Web')

    def test_note_moyenne_calculee(self):
        from apps.demandes.models import Categorie, Demande
        from apps.propositions.models import Evaluation, Mission, Proposition
        categorie = Categorie.objects.create(nom='Web', slug='web')
        demande = Demande.objects.create(
            client=self.client_, categorie=categorie, titre='Site',
            description='x', statut=Demande.Statut.EN_COURS)
        proposition = Proposition.objects.create(
            demande=demande, prestataire=self.presta, prix=50000,
            delais_jours=5, statut=Proposition.Statut.ACCEPTEE)
        mission = Mission.objects.create(
            demande=demande, proposition=proposition, client=self.client_,
            prestataire=self.presta, statut=Mission.Statut.TERMINEE)
        Evaluation.objects.create(mission=mission, auteur=self.client_, cible=self.presta, note=5)
        Evaluation.objects.create(mission=mission, auteur=self.client_, cible=self.presta, note=3)
        self.assertEqual(self.presta.note_moyenne(), 4.0)

    def test_competences_modifiables_depuis_le_profil(self):
        from apps.demandes.models import Categorie
        categorie = Categorie.objects.create(nom='Mobile', slug='mobile')
        self.client.login(username='presta', password='Passw0rd!')
        reponse = self.client.post(reverse('accounts:modifier_profil'), {
            'phone': '97000333',
            'ville': 'Cotonou',
            'competences': [categorie.pk],
        })
        self.assertRedirects(reponse, reverse('accounts:profil'))
        self.assertEqual(list(self.presta.competences.all()), [categorie])


class EmailsTransactionnelsTests(TestCase):

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_inscription_envoie_un_email_de_bienvenue(self):
        from django.core import mail
        reponse = self.client.post(reverse('accounts:inscription'), {
            'username': 'avecemail',
            'email': 'nouveau@mail.fr',
            'password1': 'Passw0rd!',
            'password2': 'Passw0rd!',
            'role': User.Role.CLIENT,
            'phone': '97000444',
        })
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Bienvenue sur TechConnect Bénin', mail.outbox[0].subject)
        self.assertEqual(mail.outbox[0].to, ['nouveau@mail.fr'])

    def test_envoyer_email_ignore_les_utilisateurs_sans_adresse(self):
        from .emails import envoyer_email
        sans_email = User.objects.create_user(
            username='sansmail', password='Passw0rd!', role=User.Role.CLIENT)
        self.assertEqual(envoyer_email([sans_email], 'Sujet', 'Contenu'), 0)