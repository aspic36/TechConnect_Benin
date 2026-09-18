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


class CatalogueFiltresEtPaginationTests(TestCase):

    def setUp(self):
        self.client_u = User.objects.create_user(
            username='client', password='Passw0rd!', role=User.Role.CLIENT)
        self.presta = User.objects.create_user(
            username='presta', password='Passw0rd!', role=User.Role.PRESTATAIRE)
        self.categorie = Categorie.objects.create(nom='Développement web', slug='developpement-web')
        self.client.login(username='presta', password='Passw0rd!')

    def _demande(self, titre='Site', budget_min=50000, budget_max=100000,
                 lieu='Cotonou', a_distance=False):
        return Demande.objects.create(
            client=self.client_u, categorie=self.categorie, titre=titre,
            description='Un besoin', budget_min=budget_min, budget_max=budget_max,
            lieu=lieu, a_distance=a_distance, statut=Demande.Statut.EN_COURS)

    def test_filtre_ville(self):
        self._demande(titre='Sur place')
        self._demande(titre='Autre ville', lieu='Parakou')
        reponse = self.client.get(reverse('demandes:catalogue'), {'ville': 'cotonou'})
        self.assertEqual(len(reponse.context['demandes']), 1)

    def test_filtre_budget_selectionne_le_recouvrement(self):
        self._demande(titre='Dans la fourchette')
        self._demande(titre='Hors budget', budget_min=300000, budget_max=400000)
        reponse = self.client.get(reverse('demandes:catalogue'), {
            'budget_min': '60000', 'budget_max': '200000',
        })
        self.assertEqual(len(reponse.context['demandes']), 1)

    def test_filtre_a_distance(self):
        self._demande(titre='Sur place')
        self._demande(titre='À distance', a_distance=True)
        reponse = self.client.get(reverse('demandes:catalogue'), {'a_distance': '1'})
        self.assertEqual(len(reponse.context['demandes']), 1)

    def test_montant_invalide_ignore_le_filtre(self):
        self._demande()
        self._demande(titre='Seconde')
        reponse = self.client.get(reverse('demandes:catalogue'), {'budget_min': 'abc'})
        self.assertEqual(len(reponse.context['demandes']), 2)

    def test_pagination_treize_demandes_deux_pages(self):
        for i in range(13):
            self._demande(titre=f'Demande {i}')
        reponse = self.client.get(reverse('demandes:catalogue'))
        self.assertEqual(len(reponse.context['demandes']), 12)
        page2 = self.client.get(reverse('demandes:catalogue'), {'page': 2})
        self.assertEqual(len(page2.context['demandes']), 1)


class FavorisDemandeTests(TestCase):

    def setUp(self):
        self.client_u = User.objects.create_user(
            username='client', password='Passw0rd!', role=User.Role.CLIENT)
        self.presta = User.objects.create_user(
            username='presta', password='Passw0rd!', role=User.Role.PRESTATAIRE)
        self.categorie = Categorie.objects.create(nom='Développement web', slug='developpement-web')
        self.demande = Demande.objects.create(
            client=self.client_u, categorie=self.categorie, titre='Site vitrine',
            description='Petit site', statut=Demande.Statut.EN_COURS)

    def test_ajout_puis_retrait_du_favori(self):
        from .models import FavorisDemande
        self.client.login(username='presta', password='Passw0rd!')
        url = reverse('demandes:basculer_favori', args=[self.demande.pk])
        self.client.get(url)
        self.assertTrue(FavorisDemande.objects.filter(
            prestataire=self.presta, demande=self.demande).exists())
        self.client.get(url)
        self.assertFalse(FavorisDemande.objects.filter(
            prestataire=self.presta, demande=self.demande).exists())

    def test_client_interdit_de_mettre_en_favori(self):
        from .models import FavorisDemande
        self.client.login(username='client', password='Passw0rd!')
        reponse = self.client.get(reverse('demandes:basculer_favori', args=[self.demande.pk]))
        self.assertRedirects(reponse, reverse('demandes:catalogue'))
        self.assertFalse(FavorisDemande.objects.filter(demande=self.demande).exists())

    def test_page_mes_favoris_affiche_les_demandes(self):
        from .models import FavorisDemande
        FavorisDemande.objects.create(prestataire=self.presta, demande=self.demande)
        self.client.login(username='presta', password='Passw0rd!')
        reponse = self.client.get(reverse('demandes:mes_favoris'))
        self.assertContains(reponse, 'Site vitrine')