from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
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