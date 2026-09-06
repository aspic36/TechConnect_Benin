from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.demandes.models import Categorie, Demande

from .models import Evaluation, Mission, Paiement, Proposition


class BaseTests(TestCase):

    def setUp(self):
        self.client_u = User.objects.create_user(
            username='client', password='Passw0rd!', role=User.Role.CLIENT)
        self.presta = User.objects.create_user(
            username='presta', password='Passw0rd!', role=User.Role.PRESTATAIRE)
        self.presta2 = User.objects.create_user(
            username='presta2', password='Passw0rd!', role=User.Role.PRESTATAIRE)
        categorie = Categorie.objects.create(nom='Développement web', slug='developpement-web')
        self.demande = Demande.objects.create(
            client=self.client_u, categorie=categorie,
            titre='Site vitrine', description='x', statut=Demande.Statut.EN_COURS,
        )

    def _proposition(self, prestataire=None):
        return Proposition.objects.create(
            demande=self.demande,
            prestataire=prestataire or self.presta,
            prix=100000,
            delais_jours=10,
        )

    def _mission(self):
        proposition = self._proposition()
        proposition.statut = Proposition.Statut.ACCEPTEE
        proposition.save()
        mission = Mission.objects.create(
            demande=self.demande,
            proposition=proposition,
            client=self.client_u,
            prestataire=self.presta,
        )
        return mission


class SoumissionTests(BaseTests):

    def test_soumettre_reserve_aux_prestataires(self):
        self.client.login(username='client', password='Passw0rd!')
        reponse = self.client.post(
            reverse('propositions:soumettre', args=[self.demande.pk]),
            {'prix': 100000, 'delais_jours': 10},
        )
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(Proposition.objects.count(), 0)

    def test_soumettre_valide(self):
        self.client.login(username='presta', password='Passw0rd!')
        self.client.post(
            reverse('propositions:soumettre', args=[self.demande.pk]),
            {'prix': 100000, 'delais_jours': 10, 'message': 'Je peux le faire'},
        )
        proposition = Proposition.objects.get()
        self.assertEqual(proposition.prestataire, self.presta)
        self.assertEqual(proposition.statut, Proposition.Statut.ENVOYEE)

    def test_soumettre_refusee_sur_demande_cloturee(self):
        self.demande.statut = Demande.Statut.CLOTUREE
        self.demande.save()
        self.client.login(username='presta', password='Passw0rd!')
        self.client.post(
            reverse('propositions:soumettre', args=[self.demande.pk]),
            {'prix': 100000, 'delais_jours': 10},
        )
        self.assertFalse(Proposition.objects.exists())


class ListeTests(BaseTests):

    def test_mes_propositions_filtre_par_prestataire(self):
        self._proposition(self.presta)
        self._proposition(self.presta2)
        self.client.login(username='presta', password='Passw0rd!')
        reponse = self.client.get(reverse('propositions:mes_propositions'))
        self.assertEqual(len(reponse.context['propositions']), 1)

    def test_propositions_demande_visible_par_le_client(self):
        self._proposition()
        self.client.login(username='client', password='Passw0rd!')
        reponse = self.client.get(reverse('propositions:propositions_demande', args=[self.demande.pk]))
        self.assertEqual(len(reponse.context['propositions']), 1)

    def test_propositions_demande_cachee_aux_autres(self):
        self._proposition()
        self.client.login(username='presta', password='Passw0rd!')
        reponse = self.client.get(reverse('propositions:propositions_demande', args=[self.demande.pk]))
        self.assertEqual(reponse.status_code, 404)


class AcceptationTests(BaseTests):

    def test_accepter_cree_une_mission_et_refuse_les_autres(self):
        p1 = self._proposition(self.presta)
        p2 = self._proposition(self.presta2)
        self.client.login(username='client', password='Passw0rd!')
        self.client.get(reverse('propositions:accepter', args=[p1.pk]))
        p1.refresh_from_db()
        p2.refresh_from_db()
        self.demande.refresh_from_db()
        self.assertEqual(p1.statut, Proposition.Statut.ACCEPTEE)
        self.assertEqual(p2.statut, Proposition.Statut.REFUSEE)
        self.assertEqual(Mission.objects.count(), 1)
        self.assertEqual(Mission.objects.get().prestataire, self.presta)
        self.assertEqual(self.demande.statut, Demande.Statut.MISSION_ACTIVE)

    def test_impossible_d_accepter_deux_fois(self):
        p1 = self._proposition(self.presta)
        p2 = self._proposition(self.presta2)
        self.client.login(username='client', password='Passw0rd!')
        self.client.get(reverse('propositions:accepter', args=[p1.pk]))
        self.client.get(reverse('propositions:accepter', args=[p2.pk]))
        self.assertEqual(Mission.objects.count(), 1)

    def test_refuser_une_proposition(self):
        proposition = self._proposition()
        self.client.login(username='client', password='Passw0rd!')
        self.client.get(reverse('propositions:refuser', args=[proposition.pk]))
        proposition.refresh_from_db()
        self.assertEqual(proposition.statut, Proposition.Statut.REFUSEE)


class MissionTests(BaseTests):

    def test_liste_missions_reservee_aux_participants(self):
        mission = self._mission()
        self.client.login(username='presta2', password='Passw0rd!')
        reponse = self.client.get(reverse('propositions:liste_missions'))
        self.assertNotIn(mission, list(reponse.context['missions']))

    def test_detail_mission_restreint(self):
        mission = self._mission()
        self.client.login(username='presta2', password='Passw0rd!')
        reponse = self.client.get(reverse('propositions:detail_mission', args=[mission.pk]))
        self.assertRedirects(reponse, reverse('propositions:liste_missions'))

    def test_clore_termine_mission_et_demande(self):
        mission = self._mission()
        self.client.login(username='client', password='Passw0rd!')
        self.client.get(reverse('propositions:clore', args=[mission.pk]))
        mission.refresh_from_db()
        self.demande.refresh_from_db()
        self.assertEqual(mission.statut, Mission.Statut.TERMINEE)
        self.assertEqual(self.demande.statut, Demande.Statut.CLOTUREE)


class EvaluationTests(BaseTests):

    def test_evaluation_impossible_avant_terminaison(self):
        mission = self._mission()
        self.client.login(username='client', password='Passw0rd!')
        self.client.post(
            reverse('propositions:evaluer', args=[mission.pk]),
            {'note': 5, 'commentaire': 'top'},
        )
        self.assertEqual(Evaluation.objects.count(), 0)

    def test_evaluation_apres_terminaison(self):
        mission = self._mission()
        self.client.login(username='client', password='Passw0rd!')
        self.client.get(reverse('propositions:clore', args=[mission.pk]))
        self.client.post(
            reverse('propositions:evaluer', args=[mission.pk]),
            {'note': 5, 'commentaire': 'Excellent travail'},
        )
        evaluation = Evaluation.objects.get()
        self.assertEqual(evaluation.note, 5)
        self.assertEqual(evaluation.cible, self.presta)
        self.assertEqual(evaluation.auteur, self.client_u)

    def test_note_limitee_de_1_a_5(self):
        self.assertEqual(Proposition.objects.filter().count(), 0)
        from .forms import EvaluationForm
        form_invalide = EvaluationForm(data={'note': 6, 'commentaire': 'x'})
        self.assertFalse(form_invalide.is_valid())


class PaiementTests(BaseTests):

    def test_seul_le_client_peut_enregistrer(self):
        mission = self._mission()
        self.client.login(username='presta', password='Passw0rd!')
        reponse = self.client.post(
            reverse('propositions:paiement', args=[mission.pk]),
            {'montant': 100000, 'methode': 'especes'},
        )
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(mission.paiements.count(), 0)

    def test_enregistrer_un_paiement(self):
        mission = self._mission()
        self.client.login(username='client', password='Passw0rd!')
        self.client.post(
            reverse('propositions:paiement', args=[mission.pk]),
            {'montant': 100000, 'methode': 'mobile_money'},
        )
        paiement = mission.paiements.get()
        self.assertEqual(paiement.montant, 100000)
        self.assertEqual(paiement.methode, Paiement.Methode.MOBILE_MONEY)
        self.assertEqual(paiement.statut, Paiement.Statut.EN_ATTENTE)