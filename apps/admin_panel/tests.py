from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Abonnement, Notification, User
from apps.demandes.models import Demande


class AdminPanelTests(TestCase):

    def setUp(self):
        self.staff = User.objects.create_user(
            username='staff', password='Passw0rd!',
            role=User.Role.CLIENT, is_staff=True)
        self.client_u = User.objects.create_user(
            username='client', password='Passw0rd!', role=User.Role.CLIENT)
        User.objects.create_user(
            username='presta', password='Passw0rd!', role=User.Role.PRESTATAIRE)

    def test_dashboard_reserve_au_staff(self):
        self.client.login(username='client', password='Passw0rd!')
        reponse = self.client.get(reverse('admin_panel:dashboard'))
        self.assertNotEqual(reponse.status_code, 200)

    def test_dashboard_accessible_au_staff(self):
        self.client.login(username='staff', password='Passw0rd!')
        reponse = self.client.get(reverse('admin_panel:dashboard'))
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse.context['total_clients'], 2)
        self.assertEqual(reponse.context['total_prestataires'], 1)

    def test_liste_prestataires(self):
        User.objects.create_user(
            username='presta2', password='Passw0rd!', role=User.Role.PRESTATAIRE)
        self.client.login(username='staff', password='Passw0rd!')
        reponse = self.client.get(reverse('admin_panel:prestataires'))
        self.assertEqual(len(reponse.context['prestataires']), 2)

    def test_verification_prestataire(self):
        non_verifie = User.objects.create_user(
            username='presta3', password='Passw0rd!', role=User.Role.PRESTATAIRE)
        self.client.login(username='staff', password='Passw0rd!')
        self.client.get(reverse('admin_panel:verifier', args=[non_verifie.pk]))
        non_verifie.refresh_from_db()
        self.assertTrue(non_verifie.is_verified)

    def test_prestataires_a_verifier_comptes(self):
        User.objects.create_user(
            username='presta4', password='Passw0rd!', role=User.Role.PRESTATAIRE)
        self.client.login(username='staff', password='Passw0rd!')
        reponse = self.client.get(reverse('admin_panel:dashboard'))
        self.assertEqual(reponse.context['prestataires_a_verifier'], 2)


class ModerationTests(TestCase):

    def setUp(self):
        self.staff = User.objects.create_user(
            username='staff', password='Passw0rd!', role=User.Role.CLIENT, is_staff=True)
        self.client_u = User.objects.create_user(
            username='client', password='Passw0rd!', role=User.Role.CLIENT)
        self.demande = Demande.objects.create(
            client=self.client_u, titre='À valider', description='x',
            statut=Demande.Statut.EN_ATTENTE)

    def test_moderation_reservee_au_staff(self):
        self.client.login(username='client', password='Passw0rd!')
        reponse = self.client.get(reverse('admin_panel:demandes'))
        self.assertNotEqual(reponse.status_code, 200)

    def test_liste_seulement_en_attente(self):
        Demande.objects.create(client=self.client_u, titre='Déjà en cours', description='x',
                               statut=Demande.Statut.EN_COURS)
        self.client.login(username='staff', password='Passw0rd!')
        reponse = self.client.get(reverse('admin_panel:demandes'))
        self.assertEqual(len(reponse.context['demandes']), 1)

    def test_valider_demande(self):
        self.client.login(username='staff', password='Passw0rd!')
        self.client.get(reverse('admin_panel:valider_demande', args=[self.demande.pk]))
        self.demande.refresh_from_db()
        self.assertEqual(self.demande.statut, Demande.Statut.EN_COURS)

    def test_supprimer_demande(self):
        self.client.login(username='staff', password='Passw0rd!')
        self.client.get(reverse('admin_panel:refuser_demande', args=[self.demande.pk]))
        self.assertFalse(Demande.objects.filter(pk=self.demande.pk).exists())


class CommissionSanctionsTests(TestCase):

    def setUp(self):
        from apps.demandes.models import Categorie
        self.staff = User.objects.create_user(
            username='staff', password='Passw0rd!',
            role=User.Role.CLIENT, is_staff=True)
        self.client_u = User.objects.create_user(
            username='client', password='Passw0rd!', role=User.Role.CLIENT)
        self.presta = User.objects.create_user(
            username='presta', password='Passw0rd!', role=User.Role.PRESTATAIRE)
        categorie = Categorie.objects.create(nom='Web', slug='web')
        self.demande = Demande.objects.create(
            client=self.client_u, categorie=categorie, titre='Site',
            description='x', statut=Demande.Statut.EN_COURS)

    def _mission_terminee(self):
        from apps.propositions.models import Commission, Mission, Proposition
        proposition = Proposition.objects.create(
            demande=self.demande, prestataire=self.presta,
            prix=100000, delais_jours=10, statut=Proposition.Statut.ACCEPTEE)
        mission = Mission.objects.create(
            demande=self.demande, proposition=proposition,
            client=self.client_u, prestataire=self.presta,
            statut=Mission.Statut.TERMINEE)
        commission = Commission.objects.create(
            mission=mission, montant=10000, date_limite=timezone.now())
        return mission, commission

    def test_confirm_commission_reactive_prestataire(self):
        mission, commission = self._mission_terminee()
        self.presta.suspendu = True
        self.presta.date_suspension = timezone.now()
        self.presta.save()
        self.client.login(username='staff', password='Passw0rd!')
        self.client.get(reverse('admin_panel:confirmer_commission', args=[commission.pk]))
        commission.refresh_from_db()
        self.presta.refresh_from_db()
        self.assertEqual(commission.statut, 'payee')
        self.assertFalse(self.presta.suspendu)

    def test_suspendre_et_bannir_prestataire(self):
        self.client.login(username='staff', password='Passw0rd!')
        self.client.get(reverse('admin_panel:suspendre', args=[self.presta.pk]))
        self.presta.refresh_from_db()
        self.assertTrue(self.presta.suspendu)
        self.client.get(reverse('admin_panel:bannir', args=[self.presta.pk]))
        self.presta.refresh_from_db()
        self.assertFalse(self.presta.is_active)

    def test_reactiver_prestataire_banni(self):
        self.presta.suspendu = True
        self.presta.is_active = False
        self.presta.save()
        self.client.login(username='staff', password='Passw0rd!')
        self.client.get(reverse('admin_panel:reactiver', args=[self.presta.pk]))
        self.presta.refresh_from_db()
        self.assertTrue(self.presta.is_active)
        self.assertFalse(self.presta.suspendu)

    def test_dashboard_compte_les_commissions_a_confirmer(self):
        mission, commission = self._mission_terminee()
        commission.date_limite = timezone.now() + timezone.timedelta(days=5)
        commission.date_declaration = timezone.now()
        commission.save()
        self.client.login(username='staff', password='Passw0rd!')
        reponse = self.client.get(reverse('admin_panel:dashboard'))
        self.assertEqual(reponse.context['commissions_a_confirmer'], 1)
        self.assertEqual(reponse.context['commissions_en_retard'], 0)


class AbonnementBackOfficeTests(TestCase):

    def setUp(self):
        self.staff = User.objects.create_user(
            username='staff', password='Passw0rd!',
            role=User.Role.CLIENT, is_staff=True)
        self.client_u = User.objects.create_user(
            username='client', password='Passw0rd!', role=User.Role.CLIENT)
        self.presta = User.objects.create_user(
            username='presta', password='Passw0rd!', role=User.Role.PRESTATAIRE)
        self.abonnement = Abonnement.objects.create(
            prestataire=self.presta, plan=User.Plan.STANDARD, montant=2000,
            methode=Abonnement.Methode.MOBILE_MONEY)

    def test_liste_abonnements_reservee_au_staff(self):
        self.client.login(username='client', password='Passw0rd!')
        reponse = self.client.get(reverse('admin_panel:abonnements'))
        self.assertNotEqual(reponse.status_code, 200)

    def test_confirmer_abonnement_active_le_plan(self):
        self.client.login(username='staff', password='Passw0rd!')
        self.client.get(reverse('admin_panel:confirmer_abonnement', args=[self.abonnement.pk]))
        self.abonnement.refresh_from_db()
        self.presta.refresh_from_db()
        self.assertEqual(self.abonnement.statut, Abonnement.Statut.ACTIF)
        self.assertEqual(self.presta.plan, User.Plan.STANDARD)
        self.assertIsNotNone(self.presta.date_debut_plan)
        self.assertIsNotNone(self.abonnement.date_confirmation)
        self.assertLess(
            (self.presta.date_fin_plan - self.presta.date_debut_plan).days, 31)

    def test_refuser_abonnement_laisse_le_plan(self):
        self.client.login(username='staff', password='Passw0rd!')
        self.client.get(reverse('admin_panel:refuser_abonnement', args=[self.abonnement.pk]))
        self.abonnement.refresh_from_db()
        self.presta.refresh_from_db()
        self.assertEqual(self.abonnement.statut, Abonnement.Statut.REFUSE)
        self.assertEqual(self.presta.plan, User.Plan.GRATUIT)

    def test_dashboard_compte_les_abonnements_a_confirmer(self):
        self.client.login(username='staff', password='Passw0rd!')
        reponse = self.client.get(reverse('admin_panel:dashboard'))
        self.assertEqual(reponse.context['abonnements_a_confirmer'], 1)

    def test_confirmer_deux_fois_n_etend_pas_la_periode(self):
        self.client.login(username='staff', password='Passw0rd!')
        self.client.get(reverse('admin_panel:confirmer_abonnement', args=[self.abonnement.pk]))
        self.abonnement.refresh_from_db()
        date_fin = self.abonnement.date_fin
        self.client.get(reverse('admin_panel:confirmer_abonnement', args=[self.abonnement.pk]))
        self.abonnement.refresh_from_db()
        self.assertEqual(self.abonnement.date_fin, date_fin)

    def test_confirmer_abonnement_notifie_le_prestataire(self):
        self.client.login(username='staff', password='Passw0rd!')
        self.client.get(reverse('admin_panel:confirmer_abonnement', args=[self.abonnement.pk]))
        notification = Notification.objects.get(destinataire=self.presta)
        self.assertEqual(notification.type, 'abonnement')
        self.assertFalse(notification.est_lue)

    def test_refuser_abonnement_notifie_le_prestataire(self):
        self.client.login(username='staff', password='Passw0rd!')
        self.client.get(reverse('admin_panel:refuser_abonnement', args=[self.abonnement.pk]))
        notification = Notification.objects.get(destinataire=self.presta)
        self.assertEqual(notification.type, 'abonnement')

    def test_valider_demande_notifie_le_client(self):
        demande = Demande.objects.create(
            client=self.client_u, titre='À valider', description='x',
            statut=Demande.Statut.EN_ATTENTE)
        self.client.login(username='staff', password='Passw0rd!')
        self.client.get(reverse('admin_panel:valider_demande', args=[demande.pk]))
        notification = Notification.objects.get(destinataire=self.client_u)
        self.assertEqual(notification.type, 'demande')

    def test_confirmer_commission_notifie_le_prestataire(self):
        from apps.demandes.models import Categorie
        from apps.propositions.models import Commission, Mission, Proposition
        categorie = Categorie.objects.create(nom='Web', slug='web')
        demande = Demande.objects.create(
            client=self.client_u, categorie=categorie, titre='Site',
            description='x', statut=Demande.Statut.EN_COURS)
        proposition = Proposition.objects.create(
            demande=demande, prestataire=self.presta,
            prix=100000, delais_jours=10, statut=Proposition.Statut.ACCEPTEE)
        mission = Mission.objects.create(
            demande=demande, proposition=proposition,
            client=self.client_u, prestataire=self.presta,
            statut=Mission.Statut.TERMINEE)
        commission = Commission.objects.create(
            mission=mission, montant=10000, date_limite=timezone.now())
        self.client.login(username='staff', password='Passw0rd!')
        self.client.get(reverse('admin_panel:confirmer_commission', args=[commission.pk]))
        notification = Notification.objects.get(destinataire=self.presta)
        self.assertEqual(notification.type, 'commission')