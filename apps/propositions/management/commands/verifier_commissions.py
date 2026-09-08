"""
Commande de management : verifier_commissions.

Applique automatiquement les sanctions économiques décidées par les règles
de la plateforme, à lancer chaque nuit (cron) :

1. Une commission impayée après sa date limite → suspension du prestataire.
2. Une suspension dépassant COMMISSION_SUSPENSION_JOURS → bannissement.

La commande est idempotente : elle peut être relancée sans effet de bord.
"""

from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import User
from apps.propositions.models import Commission


class Command(BaseCommand):
    """Commande Django : application automatique des sanctions de la plateforme."""

    help = 'Vérifie les commissions impayées et applique suspensions / bannissements.'

    def handle(self, *args, **options):
        """Applique les sanctions selon les deux règles métier de la plateforme."""
        maintenant = timezone.now()

        # --- 1. Commission impayée après la date limite → suspension ---
        en_retard = Commission.objects.filter(
            statut=Commission.Statut.EN_ATTENTE,
            date_limite__lt=maintenant,
        ).select_related('mission__prestataire')
        suspendus = 0
        for commission in en_retard:
            prestataire = commission.mission.prestataire
            # Évite de ré-appliquer une sanction déjà en place ou un ban définitif.
            if prestataire.is_active and not prestataire.suspendu:
                prestataire.suspendu = True
                prestataire.date_suspension = maintenant
                prestataire.save()
                suspendus += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'Suspension : {prestataire.username} '
                        f'(commission {commission.montant} FCFA impayée).'
                    )
                )

        # --- 2. Suspension trop longue → bannissement définitif ---
        borne_bannissement = maintenant - timedelta(days=settings.COMMISSION_SUSPENSION_JOURS)
        a_bannir = User.objects.filter(
            role=User.Role.PRESTATAIRE,
            suspendu=True,
            is_active=True,
            date_suspension__lt=borne_bannissement,
        )
        bannis = 0
        for prestataire in a_bannir:
            prestataire.suspendu = False
            prestataire.is_active = False
            prestataire.save()
            bannis += 1
            self.stdout.write(self.style.ERROR(f'Bannissement : {prestataire.username}.'))

        self.stdout.write(self.style.SUCCESS(
            f'Vérification terminée : {suspendus} suspension(s), {bannis} bannissement(s).'
        ))