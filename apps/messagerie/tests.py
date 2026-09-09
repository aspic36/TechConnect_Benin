from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.demandes.models import Categorie, Demande
from apps.propositions.models import Mission, Proposition

from .models import Message


class MessagerieTests(TestCase):

    def setUp(self):
        self.client_u = User.objects.create_user(
            username='client', password='Passw0rd!', role=User.Role.CLIENT)
        self.presta = User.objects.create_user(
            username='presta', password='Passw0rd!', role=User.Role.PRESTATAIRE)
        self.autre = User.objects.create_user(
            username='autre', password='Passw0rd!', role=User.Role.PRESTATAIRE)
        categorie = Categorie.objects.create(nom='Développement web', slug='developpement-web')
        demande = Demande.objects.create(client=self.client_u, categorie=categorie,
                                         titre='Site', description='x')
        proposition = Proposition.objects.create(
            demande=demande, prestataire=self.presta, prix=100000, delais_jours=10)
        self.mission = Mission.objects.create(
            demande=demande, proposition=proposition,
            client=self.client_u, prestataire=self.presta,
        )

    def test_fil_restreint_aux_participants(self):
        self.client.login(username='autre', password='Passw0rd!')
        reponse = self.client.get(reverse('messagerie:fil', args=[self.mission.pk]))
        self.assertRedirects(reponse, reverse('propositions:liste_missions'))

    def test_envoi_de_message(self):
        self.client.login(username='client', password='Passw0rd!')
        self.client.post(reverse('messagerie:fil', args=[self.mission.pk]),
                         {'contenu': 'Bonjour, on démarre quand ?'})
        message = Message.objects.get()
        self.assertEqual(message.expediteur, self.client_u)
        self.assertEqual(message.contenu, 'Bonjour, on démarre quand ?')

    def test_post_ignoré_si_contenu_vide(self):
        self.client.login(username='client', password='Passw0rd!')
        self.client.post(reverse('messagerie:fil', args=[self.mission.pk]),
                         {'contenu': '   '})
        self.assertEqual(Message.objects.count(), 0)

    def test_message_marque_lu_pour_le_destinataire(self):
        Message.objects.create(mission=self.mission, expediteur=self.presta,
                               contenu='Salut', lu=False)
        self.client.login(username='client', password='Passw0rd!')
        self.client.get(reverse('messagerie:fil', args=[self.mission.pk]))
        self.assertTrue(Message.objects.get().lu)

    def test_bloque_un_numero_international(self):
        self.client.login(username='client', password='Passw0rd!')
        self.client.post(reverse('messagerie:fil', args=[self.mission.pk]),
                         {'contenu': 'Appelle-moi au +229 97 10 22 33 svp'})
        self.assertEqual(Message.objects.count(), 0)

    def test_bloque_un_numero_national(self):
        self.client.login(username='presta', password='Passw0rd!')
        self.client.post(reverse('messagerie:fil', args=[self.mission.pk]),
                         {'contenu': 'Mon phone c 01 90 12 34 56'})
        self.assertEqual(Message.objects.count(), 0)

    def test_autorise_un_message_sans_coordonnees(self):
        self.client.login(username='client', password='Passw0rd!')
        self.client.post(reverse('messagerie:fil', args=[self.mission.pk]),
                         {'contenu': 'Le livrable sera prêt vendredi à Cotonou.'})
        self.assertEqual(Message.objects.count(), 1)


class DetectionNumeroTests(TestCase):

    def test_detecte_les_formats_beninois(self):
        from .utils import detecter_numero_telephone
        self.assertTrue(detecter_numero_telephone('+22997102233'))
        self.assertTrue(detecter_numero_telephone('+229 97 10 22 33'))
        self.assertTrue(detecter_numero_telephone('97 10 22 33'))
        self.assertTrue(detecter_numero_telephone('0190223344'))
        self.assertTrue(detecter_numero_telephone('66 22 33 44'))

    def test_ne_detecte_pas_un_simple_texte(self):
        from .utils import detecter_numero_telephone
        self.assertFalse(detecter_numero_telephone('Rendez-vous à 14h au marché Dantokpa.'))
        self.assertFalse(detecter_numero_telephone(''))