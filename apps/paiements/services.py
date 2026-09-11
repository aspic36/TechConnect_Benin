"""Couche de service métier du flux escrow TechConnect (FedaPay).

Logique de paiement indépendante des vues : collecte à l'avance du prix de la
mission (fonds bloqués sur le compte plateforme), confirmation par le
fournisseur, puis reversement du solde au prestataire à la clôture avec
règlement automatique de la commission (``COMMISSION_POURCENT`` %).
"""

from django.conf import settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.notifications import creer_notification, notifier_staff
from apps.propositions.models import Commission, Paiement

from .providers import get_provider
from .providers.fedapay import ErreurFedaPay, PaiementNonAutorise


def montant_commission(prix):
    """Part de la plateforme (``COMMISSION_POURCENT`` %) sur un prix donné."""
    return prix * settings.COMMISSION_POURCENT // 100


def prix_a_payer(mission):
    """Reste à régler : prix convenu moins les paiements déjà confirmés."""
    prix = mission.proposition.prix
    regle = sum(mission.paiements.filter(statut=Paiement.Statut.PAYE).values_list('montant', flat=True))
    reste = prix - regle
    return max(reste, 0)


def mission_payee(mission):
    """Indique si le prix de la mission est intégralement couvert par des
    paiements confirmés (statut ``paye``)."""
    return prix_a_payer(mission) <= 0


def _mode_operateur(telephone):
    """Devine le mode FedaPay à partir du préfixe du n° béninois (défaut MTN)."""
    tel = (telephone or '').replace(' ', '').replace('-', '')
    tel = tel[4:] if tel.startswith('+229') else tel
    if tel.startswith('02'):
        return 'moov'
    if tel.startswith('03'):
        return 'sbin'
    return 'mtn_open'


def initier_collecte_mission(mission, client, methode, callback_url, reference):
    """Crée le paiement + la transaction FedaPay et renvoie le lien de paiement.

    Retourne ``(paiement, url)``. ``url`` est ``None`` lorsque le paiement est
    enregistré localement (virement bancaire, ou Mobile Money sans clés FedaPay
    configurées → confirmation manuelle par l'équipe).
    """
    reste = prix_a_payer(mission)
    if reste <= 0:
        return None, None

    # Virement bancaire : repli hors FedaPay, confirmation par l'équipe.
    if methode == Paiement.Methode.VIREMENT or not settings.FEDAPAY_SECRET_KEY:
        paiement = Paiement.objects.create(
            mission=mission, montant=reste, methode=methode,
            statut=Paiement.Statut.EN_ATTENTE)
        notifier_staff(
            f'Paiement de {reste} FCFA à confirmer sur « {mission.demande.titre} » '
            f'({paiement.get_methode_display()}).',
            'systeme', reverse('admin_panel:paiements'))
        return paiement, None

    try:
        provider = get_provider()
        resultat = provider.initier_collecte(
            montant=int(reste),
            description=f'Mission {mission.pk} — {mission.demande.titre}',
            email=client.email or 'client@techconnect.bj',
            telephone=client.phone or '',
            callback_url=callback_url,
            reference=reference,
            mode=settings.FEDAPAY_MODES_OPERATEURS.get(methode, 'mtn_open'),
        )
    except (ErreurFedaPay, PaiementNonAutorise) as exc:
        notifier_staff(
            f'Échec de création du paiement FedaPay sur '
            f'« {mission.demande.titre} » : {exc}',
            'systeme', reverse('admin_panel:paiements'))
        raise

    paiement = Paiement.objects.create(
        mission=mission, montant=reste, methode=methode,
        statut=Paiement.Statut.EN_COURS,
        reference_txn=resultat.transaction_id,
        donnees_webhook={'reference': resultat.reference,
                         'url_paiement': resultat.url})
    return paiement, resultat.url


def confirmer_paiement(paiement):
    """Marque un paiement comme confirmé et notifie le prestataire."""
    if paiement.statut == Paiement.Statut.PAYE:
        return
    paiement.statut = Paiement.Statut.PAYE
    paiement.save(update_fields=['statut'])
    creer_notification(
        [paiement.mission.prestataire],
        f'Le paiement de {paiement.montant} FCFA sur '
        f'« {paiement.mission.demande.titre} » a été confirmé. '
        'Le solde te sera reversé à la clôture.',
        'mission', reverse('propositions:detail_mission', args=[paiement.mission.pk]))


def eclater_paiement(paiement):
    """Marque un paiement en échec (transaction refusée/annulée)."""
    if paiement.statut == Paiement.Statut.PAYE:
        return
    paiement.statut = Paiement.Statut.ECHEC
    paiement.save(update_fields=['statut'])


def creer_commission_si_absente(mission):
    """Crée la commission de clôture si elle n'existe pas encore (idempotent)."""
    commission, creee = Commission.objects.get_or_create(
        mission=mission,
        defaults={
            'montant': montant_commission(mission.proposition.prix),
            'date_limite': timezone.now()
            + timezone.timedelta(days=settings.COMMISSION_DELAI_JOURS),
        })
    return commission, creee


def reverser_prestataire(mission, commission):
    """Reversement du solde (prix − commission) au prestataire à la clôture.

    En cas de succès, la commission est marquée payée automatiquement avec la
    référence FedaPay du reversement. Si le reversement est indisponible
    (capabilité non activée, clés absentes…), la commission reste due
    manuellement et l'équipe est prévenue.
    """
    prestataire = mission.prestataire
    solde = int(mission.proposition.prix - commission.montant)
    telephone = prestataire.phone or ''
    try:
        provider = get_provider()
        resultat = provider.initier_reversement(
            montant=solde,
            prenom=prestataire.first_name or prestataire.username,
            nom=prestataire.last_name or '',
            email=prestataire.email or 'prestataire@techconnect.bj',
            telephone=telephone,
            reference=f'M{mission.pk}',
            mode=_mode_operateur(telephone),
        )
        provider.envoyer_reversement(resultat.payout_id, telephone=telephone or None)
    except (ErreurFedaPay, PaiementNonAutorise, NotImplementedError) as exc:
        notifier_staff(
            f'Reversement de {solde} FCFA impossible pour '
            f'{prestataire.username} (mission {mission.pk}) : {exc}. '
            'Régler la commission manuellement.',
            'systeme', reverse('admin_panel:commissions'))
        return False

    commission.reference_payout = resultat.reference or resultat.payout_id
    commission.statut = Commission.Statut.PAYEE
    commission.date_paiement = timezone.now()
    commission.save()
    creer_notification(
        [prestataire],
        f'Reversement de {solde} FCFA effectué pour la mission '
        f'« {mission.demande.titre} » (commission {commission.montant} FCFA réglée).',
        'mission', reverse('propositions:detail_mission', args=[mission.pk]))
    return True