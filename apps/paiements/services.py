"""Couche de service métier du flux escrow TechConnect (FedaPay).

Logique de paiement indépendante des vues : collecte à l'avance du prix de la
mission (fonds bloqués sur le compte plateforme), confirmation par le
fournisseur, puis reversement du solde au prestataire à la clôture avec
règlement automatique de la commission (``COMMISSION_POURCENT`` %).
"""

from django.conf import settings
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from apps.accounts.notifications import creer_notification, notifier_staff
from apps.propositions.models import Commission, Paiement

from .models import EvenementWebhook
from .providers import get_provider
from .providers.fedapay import ErreurFedaPay, PaiementNonAutorise

import hashlib
import json
import re


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


def normaliser_telephone(numero):
    """Normalise un n° béninois au format international ``+229XXXXXXXX``.

    FedaPay exige un numéro complet avec indicatif (les transactions créées
    avec un numéro local étaient rejetées à la page de paiement sandbox).
    Exemples : ``'97 10 22 33'`` → ``'+22997102233'``, ``'+22997102233'`` → inchangé.
    """
    chiffres = re.sub(r'\D', '', numero or '')
    chiffres = chiffres.lstrip('0')
    if chiffres.startswith('229'):
        chiffres = chiffres[3:]
    if not chiffres:
        return ''
    return '+229' + chiffres


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
            telephone=normaliser_telephone(client.phone),
            callback_url=callback_url,
            reference=reference,
            mode=settings.FEDAPAY_MODES_OPERATEURS.get(methode, 'mtn_open'),
            prenom=client.first_name or client.username,
            nom=client.last_name or '',
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
    telephone = normaliser_telephone(prestataire.phone)
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


# ---------------------------------------------------------------------------
# Webhooks FedaPay (confirmation automatique des paiements)
# ---------------------------------------------------------------------------

def _entite_evenement(evenement):
    """Entité concernée par un événement FedaPay (transaction ou payout)."""
    return (evenement.get('entity') or evenement.get('transaction')
            or evenement.get('payout') or {})


def _cle_idempotence(evenement):
    """Clé stable identifiant un événement (id d'entité sinon empreinte)."""
    entite = _entite_evenement(evenement)
    nom = evenement.get('name', '')
    identifiant = entite.get('reference') or str(entite.get('id', ''))
    if nom and identifiant:
        return f'{nom}:{identifiant}'
    corps = json.dumps(evenement, sort_keys=True).encode('utf-8')
    return hashlib.sha256(corps).hexdigest()


def _traiter_evenement_transaction(entite, nom):
    """Confirme ou annule le paiement correspondant à la transaction."""
    reference_ou_id = entite.get('reference') or str(entite.get('id', ''))
    if not reference_ou_id:
        return
    if str(entite.get('id', '')).isdigit():
        paiement = Paiement.objects.filter(
            reference_txn=str(entite.get('id'))).first()
        if paiement is None and reference_ou_id != str(entite.get('id')):
            paiement = Paiement.objects.filter(
                donnees_webhook__reference=reference_ou_id).first()
    else:
        paiement = Paiement.objects.filter(
            donnees_webhook__reference=reference_ou_id).first()
    if paiement is None:
        return
    donnees = dict(paiement.donnees_webhook or {})
    donnees.update({'dernier_evenement': nom, 'statut_fedapay': entite.get('status')})
    paiement.donnees_webhook = donnees
    paiement.save(update_fields=['donnees_webhook'])
    statut = entite.get('status') or nom.rsplit('.', 1)[-1]
    if statut == 'approved':
        confirmer_paiement(paiement)
    elif statut in ('declined', 'canceled', 'cancelled', 'failed', 'expired'):
        eclater_paiement(paiement)


def _traiter_evenement_payout(entite, nom):
    """Enregistre l'issue d'un reversement FedaPay sur la commission."""
    reference = entite.get('reference') or str(entite.get('id', ''))
    if not reference:
        return
    commission = Commission.objects.filter(reference_payout=reference).first()
    if commission is None and str(entite.get('id', '')).isdigit():
        commission = Commission.objects.filter(
            reference_payout=str(entite.get('id'))).first()
    if commission is None:
        return
    statut = entite.get('status') or nom.rsplit('.', 1)[-1]
    if statut in ('failed', 'declined'):
        commission.statut = Commission.Statut.EN_ATTENTE
        commission.date_paiement = None
        commission.save(update_fields=['statut', 'date_paiement'])
        notifier_staff(
            f'Le reversement FedaPay {reference} a échoué pour '
            f'{commission.mission.prestataire.username} : commission à traiter '
            'manuellement.',
            'systeme', reverse('admin_panel:commissions'))


def traiter_webhook(evenement):
    """Traite un événement FedaPay de façon idempotente.

    Retourne ``'deja_traite'`` si l'événement a déjà été reçu, ``'traite'``
    sinon. L'écriture du journal et le traitement sont atomiques : un échec
    annule tout, ce qui autorise le renvoi par FedaPay.
    """
    nom = evenement.get('name', '')
    cle = _cle_idempotence(evenement)
    with transaction.atomic():
        if EvenementWebhook.objects.filter(reference=cle).exists():
            return 'deja_traite'
        if nom.startswith('transaction.'):
            _traiter_evenement_transaction(_entite_evenement(evenement), nom)
        elif nom.startswith('payout.'):
            _traiter_evenement_payout(_entite_evenement(evenement), nom)
        EvenementWebhook.objects.create(
            reference=cle, type=nom, donnees=evenement)
    return 'traite'