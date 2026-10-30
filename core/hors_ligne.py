"""Saisie hors réseau (notes, appels).

Un formulaire soumis alors que le serveur est injoignable est conservé par le navigateur
(Service Worker, ``static/js/sw_saisies.js``) puis rejoué à l'identique au retour sur le réseau.
Le rejeu porte l'en-tête ``X-Saisie-Differee`` : la vue répond alors en JSON — et non par une
redirection — pour que le navigateur sache si la saisie a été acceptée, et avec quels messages.
"""
from functools import wraps

from django.contrib import messages
from django.contrib.messages import get_messages
from django.http import JsonResponse
from django.http.response import HttpResponseRedirectBase

EN_TETE = 'X-Saisie-Differee'
EN_TETE_UTILISATEUR = 'X-Saisie-Utilisateur'


def saisie_differee(vue):
    """À poser au-dessus de ``@login_required`` : une session expirée est signalée (401) au lieu
    d'être confondue avec une redirection de succès. Sans l'en-tête, la vue est inchangée."""
    @wraps(vue)
    def enveloppe(request, *args, **kwargs):
        differee = request.method == 'POST' and bool(request.headers.get(EN_TETE))
        if differee and not request.user.is_authenticated:
            return JsonResponse({'ok': False, 'code': 'connexion'}, status=401)
        if differee and request.headers.get(EN_TETE_UTILISATEUR, '') not in ('', str(request.user.pk)):
            return JsonResponse({'ok': False, 'code': 'utilisateur'}, status=403)   # saisie d'un autre compte
        reponse = vue(request, *args, **kwargs)
        if not differee:
            return reponse
        recues = list(get_messages(request))        # consommés : ils n'apparaîtront pas sur la page suivante
        acceptee = isinstance(reponse, HttpResponseRedirectBase) and all(m.level < messages.ERROR for m in recues)
        return JsonResponse({'ok': acceptee, 'messages': [{'niveau': m.level_tag, 'texte': str(m)} for m in recues]})
    return enveloppe
