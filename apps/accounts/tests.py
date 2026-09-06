from django.test import TestCase
from django.urls import reverse

from .forms import InscriptionForm
from .models import User


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