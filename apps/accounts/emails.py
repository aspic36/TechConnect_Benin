"""
Envoi des e-mails transactionnels de la plateforme.

S'appuie sur ``EmailMultiAlternatives`` pour produire des messages HTML
gracieux (gabarit ``templates/emails/base_email.html``) avec une version
texte de secours (HTML détaché).

En développement, si aucune variable SMTP n'est présente dans ``.env``,
l'envoi est routé vers la console (les e-mails s'affichent dans les logs)
et ne fait jamais échouer une action métier.
"""

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags


def envoyer_email(destinataires, sujet, message, bouton=None, lien=None):
    """Envoie un e-mail transactionnel HTML à une liste d'utilisateurs.

    Les destinataires n'ayant pas renseigné d'adresse e-mail sont ignorés
    silencieusement.  Retourne le nombre d'adresses réellement ciblées.

    :param destinataires: itérable de modèles ``User``.
    :param sujet: objet de l'e-mail.
    :param message: corps du message (HTML autorisé).
    :param bouton: libellé du bouton d'action (``None`` pour le masquer).
    :param lien: URL cible du bouton d'action.
    """
    adresses = [u.email for u in destinataires if getattr(u, 'email', None)]
    if not adresses:
        return 0
    corps_html = render_to_string('emails/base_email.html', {
        'sujet': sujet,
        'contenu': message,
        'bouton': bouton,
        'lien': lien,
    })
    email = EmailMultiAlternatives(
        subject=sujet,
        body=strip_tags(message),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=adresses,
    )
    email.attach_alternative(corps_html, 'text/html')
    email.send(fail_silently=True)
    return len(adresses)