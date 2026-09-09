from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User

from .models import Categorie, Demande


class DemandeTests(TestCase):

    def setUp(self):
        self.client_u = User.objects.create_user(
            username='client', password='Passw0rd!', role=User.Role.CLIENT)
        self.client2 = User.objects.create_user(
            username='client2', password='Passw0rd!', role=User.Role.CLIENT)
        self.presta = User.objects.create_user(
            username='presta', password='Passw0rd!', role=User.Role.PRESTATAIRE)
        self.categorie = Categorie.objects.create(nom='Développement web', slug='developpement-web')
        self.demande = Demande.objects.create(
            client=self.client_u, categorie=self.categorie,
            titre='Site vitrine', description='Petit site vitrine',
            budget_min=50000, budget_max=100000, statut=Demande.Statut.EN_COURS,
        )

    def test_publication_refusee_aux_prestataires(self):
        self.client.login(username='presta', password='Passw0rd!')
        reponse = self.client.post(reverse('demandes:creation_demande'), {
            'titre': 'Triche', 'description': 'x',
        })
        self.assertEqual(reponse.status_code, 302)
        self.assertFalse(Demande.objects.filter(titre='Triche').exists())

    def test_creation_demande_en_attente(self):
        self.client.login(username='client', password='Passw0rd!')
        self.client.post(reverse('demandes:creation_demande'), {
            'titre': 'Nouvelle demande',
            'description': 'Un besoin à définir',
            'categorie': self.categorie.pk,
            'budget_min': 1000,
            'budget_max': 2000,
            'lieu': 'Cotonou',
        })
        demande = Demande.objects.get(titre='Nouvelle demande')
        self.assertEqual(demande.client, self.client_u)
        self.assertEqual(demande.statut, Demande.Statut.EN_ATTENTE)

    def test_client_ne_voit_que_ses_demandes(self):
        Demande.objects.create(client=self.client2, titre='Demande d\'autrui', description='x')
        self.client.login(username='client', password='Passw0rd!')
        reponse = self.client.get(reverse('demandes:mes_demandes'))
        self.assertContains(reponse, 'Site vitrine')
        self.assertNotContains(reponse, 'Demande d\'autrui')

    def test_catalogue_reserve_aux_en_cours(self):
        Demande.objects.create(client=self.client_u, titre='Non validee',
                               description='x', statut=Demande.Statut.EN_ATTENTE)
        self.client.login(username='presta', password='Passw0rd!')
        reponse = self.client.get(reverse('demandes:catalogue'))
        self.assertContains(reponse, 'Site vitrine')
        self.assertNotContains(reponse, 'Non validee')

    def test_catalogue_filtre_mot_cle(self):
        self.client.login(username='presta', password='Passw0rd!')
        reponse = self.client.get(reverse('demandes:catalogue'), {'q': 'vitrine'})
        self.assertEqual(len(reponse.context['demandes']), 1)

    def test_catalogue_filtre_categorie(self):
        self.client.login(username='presta', password='Passw0rd!')
        reponse = self.client.get(reverse('demandes:catalogue'), {'categorie': 'developpement-web'})
        self.assertEqual(len(reponse.context['demandes']), 1)

    def test_detail_accessible_aux_prestataires(self):
        self.client.login(username='presta', password='Passw0rd!')
        reponse = self.client.get(reverse('demandes:detail_demande', args=[self.demande.pk]))
        self.assertEqual(reponse.status_code, 200)

    def test_detail_cache_aux_autres_clients(self):
        self.client.login(username='client2', password='Passw0rd!')
        reponse = self.client.get(reverse('demandes:detail_demande', args=[self.demande.pk]))
        self.assertRedirects(reponse, reverse('demandes:mes_demandes'))

    def test_detail_demande_non_publique_bloque(self):
        privee = Demande.objects.create(client=self.client_u, titre='Privée',
                                        description='x', statut=Demande.Statut.EN_ATTENTE)
        self.client.login(username='presta', password='Passw0rd!')
        reponse = self.client.get(reverse('demandes:detail_demande', args=[privee.pk]))
        self.assertEqual(reponse.status_code, 302)

    def test_publication_notifie_le_staff(self):
        from apps.accounts.models import Notification, User
        staff = User.objects.create_user(
            username='staff', password='Passw0rd!',
            role=User.Role.CLIENT, is_staff=True)
        self.client.login(username='client', password='Passw0rd!')
        self.client.post(reverse('demandes:creation_demande'), {
            'titre': 'Nouvelle demande', 'description': 'Un besoin à définir',
            'categorie': self.categorie.pk, 'budget_min': 1000, 'budget_max': 2000,
        })
        self.assertTrue(Notification.objects.filter(
            destinataire=staff, type='demande').exists())