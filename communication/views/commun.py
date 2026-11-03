"""Utilitaires partagés des vues de communication."""


def _get_etab(request):
    return getattr(request.user, 'etablissement', None)


def _sigle(etab):
    from parametres.models import IdentiteEtablissement
    identite = IdentiteEtablissement.objects.filter(etablissement=etab).first()
    return (identite.sigle or identite.nom_etablissement) if identite else (etab.nom if etab else '')
