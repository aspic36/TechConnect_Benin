from django.core.cache import cache
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