"""
Middleware de restriction des comptes suspendus.

Un prestataire suspendu (commission impayée) ne peut plus naviguer librement :
il est redirigé vers sa page de règlement de commission tant que la sanction
n'est pas levée par un administrateur.
"""

from django.shortcuts import redirect


# Préfixes d'URL toujours accessibles même en cas de suspension (ne pas les
# bloquer pour éviter de piéger l'utilisateur dans une impasse).
URLS_AUTORISEES = (
    '/connexion/',
    '/deconnexion/',
    '/inscription/',
    '/profil/',
    '/propositions/mes-commissions',
    '/propositions/commission/',
    '/back-office/',
    '/admin/',
    '/media/',
    '/static/',
)


class SuspensionMiddleware:
    """Redirige vers la page de règlement de commission tout utilisateur suspendu."""

    def __init__(self, get_response):
        """Stocke la fonction suivante du pipeline de middleware."""
        self.get_response = get_response

    def __call__(self, request):
        """Bloque l'accès aux URLs non autorisées pour un utilisateur suspendu."""
        user = getattr(request, 'user', None)
        if user is not None and user.is_authenticated and user.suspendu:
            # Un admin suspendu ne doit pas perdre l'accès au back-office : la
            # liste URLS_AUTORISEES le couvre déjà (préfixe /back-office/).
            if not request.path.startswith(URLS_AUTORISEES):
                return redirect('propositions:mes_commissions')
        return self.get_response(request)