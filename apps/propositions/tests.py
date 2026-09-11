from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Notification, User
from apps.demandes.models import Categorie, Demande
from apps.paiements.providers.base import ResultatCollecte, ResultatReversement

from .models import Commission, Evaluation, Mission, Paiement, Proposition


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

    def _payer(self, mission, statut=Paiement.Statut.PAYE,
               methode=Paiement.Methode.MTN_MOMO):
        """Marque la mission comme réglée (prix complet, par défaut payé)."""
        return Paiement.objects.create(
            mission=mission,
            montant=mission.proposition.prix,
            methode=methode,
            statut=statut,
        )


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


class QuotaPropositionTests(BaseTests):
    """Le plan Gratuit limite à 3 propositions/mois ; les plans payants lèvent la limite."""

    def _soumettre(self):
        return self.client.post(
            reverse('propositions:soumettre', args=[self.demande.pk]),
            {'prix': 100000, 'delais_jours': 10},
        )

    def test_quota_gratuit_bloque_la_quatrieme(self):
        self.client.login(username='presta', password='Passw0rd!')
        for _ in range(3):
            self._soumettre()
        self.assertEqual(Proposition.objects.count(), 3)
        reponse = self._soumettre()
        self.assertRedirects(reponse, reverse('accounts:abonnement'))
        self.assertEqual(Proposition.objects.count(), 3)

    def test_plan_standard_autorise_au_dela_de_trois(self):
        self.presta.plan = User.Plan.STANDARD
        self.presta.date_debut_plan = timezone.now() - timezone.timedelta(days=1)
        self.presta.date_fin_plan = timezone.now() + timezone.timedelta(days=29)
        self.presta.save()
        self.client.login(username='presta', password='Passw0rd!')
        for _ in range(4):
            self._soumettre()
        self.assertEqual(Proposition.objects.count(), 4)

    def test_plan_pro_illimite(self):
        self.presta.plan = User.Plan.PRO
        self.presta.date_fin_plan = timezone.now() + timezone.timedelta(days=20)
        self.presta.save()
        self.client.login(username='presta', password='Passw0rd!')
        for _ in range(5):
            self._soumettre()
        self.assertEqual(Proposition.objects.count(), 5)

    def test_plan_expire_bloque_a_trois(self):
        self.presta.plan = User.Plan.STANDARD
        self.presta.date_fin_plan = timezone.now() - timezone.timedelta(days=1)
        self.presta.save()
        self.client.login(username='presta', password='Passw0rd!')
        for _ in range(3):
            self._soumettre()
        self._soumettre()
        self.assertEqual(Proposition.objects.count(), 3)


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


@override_settings(FEDAPAY_SECRET_KEY='', FEDAPAY_BASE_URL='')
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
        self._payer(mission)
        self.client.login(username='client', password='Passw0rd!')
        self.client.get(reverse('propositions:clore', args=[mission.pk]))
        mission.refresh_from_db()
        self.demande.refresh_from_db()
        self.assertEqual(mission.statut, Mission.Statut.TERMINEE)
        self.assertEqual(self.demande.statut, Demande.Statut.CLOTUREE)


@override_settings(FEDAPAY_SECRET_KEY='', FEDAPAY_BASE_URL='')
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
        self._payer(mission)
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

    def test_methode_especes_refusee(self):
        self.client.login(username='client', password='Passw0rd!')
        mission = self._mission()
        self.client.post(
            reverse('propositions:paiement', args=[mission.pk]),
            {'montant': 100000, 'methode': 'especes'},
        )
        self.assertEqual(mission.paiements.count(), 0)

    def test_enregistrer_virement_en_attente(self):
        mission = self._mission()
        self.client.login(username='client', password='Passw0rd!')
        self.client.post(
            reverse('propositions:paiement', args=[mission.pk]),
            {'methode': 'virement'},
        )
        paiement = mission.paiements.get()
        self.assertEqual(paiement.montant, 100000)
        self.assertEqual(paiement.methode, Paiement.Methode.VIREMENT)
        self.assertEqual(paiement.statut, Paiement.Statut.EN_ATTENTE)

    @override_settings(FEDAPAY_SECRET_KEY='', FEDAPAY_BASE_URL='')
    def test_mobile_sans_fedapay_repli_local(self):
        mission = self._mission()
        self.client.login(username='client', password='Passw0rd!')
        self.client.post(
            reverse('propositions:paiement', args=[mission.pk]),
            {'methode': 'mtn_momo'},
        )
        paiement = mission.paiements.get()
        self.assertEqual(paiement.methode, Paiement.Methode.MTN_MOMO)
        self.assertEqual(paiement.statut, Paiement.Statut.EN_ATTENTE)

    def test_mobile_avec_fedapay_redirige_vers_la_page_de_paiement(self):
        mission = self._mission()
        url = 'https://sandbox-process.fedapay.com/jeton'
        class _Fake:
            def initier_collecte(self, **kwargs):
                return ResultatCollecte('77', 'trx_abc', url, 'pending')
        with patch('apps.paiements.services.get_provider', return_value=_Fake()):
            self.client.login(username='client', password='Passw0rd!')
            reponse = self.client.post(
                reverse('propositions:paiement', args=[mission.pk]),
                {'methode': 'mtn_momo'},
            )
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(reponse.url, url)
        paiement = mission.paiements.get()
        self.assertEqual(paiement.reference_txn, '77')
        self.assertEqual(paiement.statut, Paiement.Statut.EN_COURS)

    def test_verifier_paiement_confirme_en_approved(self):
        mission = self._mission()
        self._payer(mission, statut=Paiement.Statut.EN_COURS, methode=Paiement.Methode.MOOV)
        mission.paiements.update(reference_txn='42')
        class _Fake:
            def verifier_transaction(self, transaction_id):
                return 'approved'
        with patch('apps.paiements.services.get_provider', return_value=_Fake()):
            self.client.login(username='client', password='Passw0rd!')
            reponse = self.client.get(
                reverse('propositions:verifier_paiement', args=[mission.pk]))
        self.assertRedirects(reponse, reverse('propositions:detail_mission', args=[mission.pk]))
        mission.paiements.get().refresh_from_db()
        self.assertEqual(mission.paiements.get().statut, Paiement.Statut.PAYE)
        self.assertTrue(Notification.objects.filter(
            destinataire=self.presta, type='mission').exists())

    def test_verifier_paiement_echec_sur_refus(self):
        mission = self._mission()
        self._payer(mission, statut=Paiement.Statut.EN_COURS, methode=Paiement.Methode.CELTIS)
        mission.paiements.update(reference_txn='43')
        class _Fake:
            def verifier_transaction(self, transaction_id):
                return 'failed'
        with patch('apps.paiements.services.get_provider', return_value=_Fake()):
            self.client.login(username='client', password='Passw0rd!')
            self.client.get(reverse('propositions:verifier_paiement', args=[mission.pk]))
        self.assertEqual(mission.paiements.get().statut, Paiement.Statut.ECHEC)


@override_settings(FEDAPAY_SECRET_KEY='', FEDAPAY_BASE_URL='')
class CommissionTests(BaseTests):

    def test_clore_mission_cree_commission_du_pourcentage_configure(self):
        from django.conf import settings
        mission = self._mission()
        self._payer(mission)
        self.client.login(username='client', password='Passw0rd!')
        self.client.get(reverse('propositions:clore', args=[mission.pk]))
        commission = Commission.objects.get(mission=mission)
        # Pourcentage configuré appliqué au prix de la proposition acceptée.
        self.assertEqual(commission.montant,
                         mission.proposition.prix * settings.COMMISSION_POURCENT // 100)
        # Sans clés FedaPay ni reversement disponible, la commission reste due.
        self.assertEqual(commission.statut, Commission.Statut.EN_ATTENTE)
        delai = (commission.date_limite - mission.date_creation).days
        self.assertEqual(delai, settings.COMMISSION_DELAI_JOURS)

    def test_clore_mission_bloque_sans_paiement(self):
        mission = self._mission()
        self.client.login(username='client', password='Passw0rd!')
        reponse = self.client.get(reverse('propositions:clore', args=[mission.pk]))
        self.assertRedirects(reponse, reverse('propositions:detail_mission', args=[mission.pk]))
        mission.refresh_from_db()
        self.assertEqual(mission.statut, Mission.Statut.EN_COURS)
        self.assertFalse(Commission.objects.filter(mission=mission).exists())

    def test_clore_mission_ne_cree_pas_de_double_commission(self):
        mission = self._mission()
        self._payer(mission)
        self.client.login(username='client', password='Passw0rd!')
        self.client.get(reverse('propositions:clore', args=[mission.pk]))
        self.client.get(reverse('propositions:clore', args=[mission.pk]))
        self.assertEqual(Commission.objects.filter(mission=mission).count(), 1)

    def test_clore_reverse_et_paye_la_commission_automatiquement(self):
        mission = self._mission()
        self._payer(mission)
        class _Fake:
            def initier_reversement(self, **kwargs):
                return ResultatReversement('8', 'pout_demo', 'pending')
            def envoyer_reversement(self, payout_id, telephone=None):
                return 'sent'
        with patch('apps.paiements.services.get_provider', return_value=_Fake()):
            self.client.login(username='client', password='Passw0rd!')
            self.client.get(reverse('propositions:clore', args=[mission.pk]))
        commission = Commission.objects.get(mission=mission)
        self.assertEqual(commission.statut, Commission.Statut.PAYEE)
        self.assertEqual(commission.reference_payout, 'pout_demo')
        self.assertIsNotNone(commission.date_paiement)
        self.assertTrue(Notification.objects.filter(
            destinataire=self.presta, type='mission',
            message__contains='Reversement').exists())

    def test_mes_commissions_reservees_aux_prestataires(self):
        mission = self._mission()
        mission.statut = Mission.Statut.TERMINEE
        mission.save()
        Commission.objects.create(
            mission=mission, montant=10000,
            date_limite=timezone.now(),
        )
        self.client.login(username='client', password='Passw0rd!')
        reponse = self.client.get(reverse('propositions:mes_commissions'))
        self.assertRedirects(reponse, reverse('propositions:liste_missions'))

    def test_regler_commission_cree_declaration(self):
        mission = self._mission()
        mission.statut = Mission.Statut.TERMINEE
        mission.save()
        commission = Commission.objects.create(
            mission=mission, montant=10000,
            date_limite=timezone.now(),
        )
        self.client.login(username='presta', password='Passw0rd!')
        self.client.post(
            reverse('propositions:regler_commission', args=[commission.pk]),
            {'methode': 'mtn_momo'},
        )
        commission.refresh_from_db()
        self.assertIsNotNone(commission.date_declaration)
        self.assertEqual(commission.statut, Commission.Statut.EN_ATTENTE)


class SanctionsAutomatiquesTests(BaseTests):

    def test_verifier_commissions_suspend_apres_la_date_limite(self):
        from django.core.management import call_command
        mission = self._mission()
        Commission.objects.create(
            mission=mission, montant=10000,
            date_limite=timezone.now() - timezone.timedelta(days=1),
        )
        call_command('verifier_commissions')
        self.presta.refresh_from_db()
        self.assertTrue(self.presta.suspendu)

    def test_verifier_commissions_ignore_les_commissions_a_jour(self):
        from django.core.management import call_command
        mission = self._mission()
        Commission.objects.create(
            mission=mission, montant=10000,
            date_limite=timezone.now() + timezone.timedelta(days=5),
        )
        call_command('verifier_commissions')
        self.presta.refresh_from_db()
        self.assertFalse(self.presta.suspendu)

    def test_verifier_commissions_bannit_apres_la_suspension_limite(self):
        from django.conf import settings
        from django.core.management import call_command
        mission = self._mission()
        Commission.objects.create(
            mission=mission, montant=10000,
            date_limite=timezone.now() - timezone.timedelta(days=1),
        )
        self.presta.suspendu = True
        self.presta.date_suspension = timezone.now() - timezone.timedelta(
            days=settings.COMMISSION_SUSPENSION_JOURS + 1)
        self.presta.save()
        call_command('verifier_commissions')
        self.presta.refresh_from_db()
        self.assertFalse(self.presta.is_active)
        self.assertFalse(self.presta.suspendu)

    def test_middleware_redirige_le_prestataire_suspendu(self):
        mission = self._mission()
        Commission.objects.create(
            mission=mission, montant=10000,
            date_limite=timezone.now() - timezone.timedelta(days=1),
        )
        self.presta.suspendu = True
        self.presta.save()
        self.client.login(username='presta', password='Passw0rd!')
        # Une page normale est bloquée par le middleware…
        reponse = self.client.get(reverse('propositions:mes_propositions'))
        self.assertRedirects(reponse, reverse('propositions:mes_commissions'))
        # …mais la page de règlement reste accessible.
        reponse = self.client.get(reverse('propositions:mes_commissions'))
        self.assertEqual(reponse.status_code, 200)


class NotificationDeclenchementTests(BaseTests):
    """Les actions métier clés créent des notifications aux bons destinataires."""

    def test_proposition_acceptee_notifie_le_prestataire(self):
        from apps.accounts.models import Notification
        proposition = self._proposition()
        self.client.login(username='client', password='Passw0rd!')
        self.client.get(reverse('propositions:accepter', args=[proposition.pk]))
        self.assertTrue(Notification.objects.filter(
            destinataire=self.presta, type='mission').exists())

    def test_reglement_commission_notifie_le_staff(self):
        from apps.accounts.models import Notification, User
        staff = User.objects.create_user(
            username='staff', password='Passw0rd!',
            role=User.Role.CLIENT, is_staff=True)
        mission = self._mission()
        commission = Commission.objects.create(
            mission=mission, montant=10000,
            date_limite=timezone.now() + timezone.timedelta(days=5))
        self.client.login(username='presta', password='Passw0rd!')
        self.client.post(
            reverse('propositions:regler_commission', args=[commission.pk]),
            {'methode': 'virement'},
        )
        self.assertTrue(Notification.objects.filter(
            destinataire=staff, type='commission').exists())