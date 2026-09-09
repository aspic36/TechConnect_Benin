"""
Outils de prévention du contournement de la plateforme.

TechConnect prélève une commission de 10% sur chaque mission : échanger des
coordonnées directes (téléphone, WhatsApp…) dans la messagerie permet de
poursuivre en direct hors plateforme. Ce module détecte les numéros
béninois (format international ``+229`` ou national) pour les bloquer.
"""

import re


def detecter_numero_telephone(texte):
    """Retourne True si le texte contient un numéro de téléphone béninois.

    Les numéros sont détectés après suppression des espaces, points, tirets
    et parenthèses pour tolérer toutes les écritures usuelles :
    ``+229 97 10 22 33``, ``0190 12 34 56``, ``97 10 22 33``…
    """
    if not texte:
        return False
    # On normalise la saisie : suppression des séparateurs courants.
    normalise = texte.translate(str.maketrans('', '', ' .-_()'))
    motifs = (
        re.compile(r'\+229\d{8}'),        # international  (229 = Bénin)
        re.compile(r'(?<!\d)0\d{9}(?!\d)'),  # national 10 chiffres
        re.compile(r'(?<!\d)9\d{7}(?!\d)'),  # mobile national 8 chiffres (90-99)
        re.compile(r'(?<!\d)6\d{7}(?!\d)'),  # 60-69
        re.compile(r'(?<!\d)5\d{7}(?!\d)'),  # 50-59
    )
    return any(motif.search(normalise) for motif in motifs)