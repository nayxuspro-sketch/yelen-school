"""Paie du mois : préparation en masse des salaires (un brouillon par agent à partir de son dernier bulletin),
validation groupée, livre de paie (récapitulatif mensuel) et bulletins du mois en un seul PDF."""
from decimal import Decimal

from django.db import transaction

from .models import AbsencePersonnel, MembrePersonnel, SalairePersonnel
from .selectors import filtrer_par_membres_visibles, membres_visibles

MOIS = dict(SalairePersonnel.MOIS_CHOICES)


def salaires_du_mois(etab, mois, annee, request=None):
    queryset = SalairePersonnel.objects.filter(personnel__etablissement=etab, mois=mois, annee=annee)
    queryset = filtrer_par_membres_visibles(queryset, request)
    return queryset.select_related('personnel', 'annee_scolaire').order_by('personnel__nom', 'personnel__prenom')


def agents_a_payer(etab, request=None):
    """Agents permanents accessibles de l'établissement (actifs, non vacataires)."""
    queryset = MembrePersonnel.objects.filter(etablissement=etab, is_active=True, est_vacataire=False)
    queryset = membres_visibles(request, queryset)
    return queryset.order_by('nom', 'prenom')


def preparer(etab, mois, annee, annee_scolaire, par, request=None):
    """Crée un brouillon pour chaque agent à payer sans bulletin ce mois-ci : salaire de base, indemnités et retenues
    CNSS / IUTS repris de son dernier bulletin, prime d'ancienneté recalculée, primes exceptionnelles à zéro et
    retenue proposée pour les jours d'absence non justifiés du mois (1/30e du salaire de base par jour).
    Retourne (bulletins créés, agents sans bulletin de référence — à saisir à la main)."""
    deja = set(SalairePersonnel.objects.filter(personnel__etablissement=etab, mois=mois, annee=annee)
               .values_list('personnel_id', flat=True))
    crees, sans_reference = [], []
    with transaction.atomic():
        for membre in agents_a_payer(etab, request=request).exclude(pk__in=deja):
            dernier = SalairePersonnel.objects.filter(personnel=membre).order_by('-annee', '-mois').first()
            if dernier is None:
                sans_reference.append(membre)
                continue
            jours = AbsencePersonnel.jours_retenus(membre, mois, annee, request=request)
            retenue = (dernier.salaire_base / 30 * jours).quantize(Decimal('1')) if jours else Decimal('0')
            salaire = SalairePersonnel(
                personnel=membre, annee_scolaire=annee_scolaire, mois=mois, annee=annee,
                salaire_base=dernier.salaire_base, indemnite_transport=dernier.indemnite_transport,
                indemnite_logement=dernier.indemnite_logement,
                prime_anciennete=SalairePersonnel.calculer_prime_anciennete(membre, dernier.salaire_base),
                autres_primes=Decimal('0'), retenue_cnss=dernier.retenue_cnss, retenue_iuts=dernier.retenue_iuts,
                autres_retenues=retenue, statut=SalairePersonnel.StatutChoices.BROUILLON, created_by=par,
                observations=f"Retenue absences : {jours} jour(s) non justifié(s) (1/30e du salaire de base par jour)." if jours else '',
            )
            salaire.save()
            crees.append(salaire)
    return crees, sans_reference


def valider_brouillons(etab, mois, annee, request=None):
    """BROUILLON → VALIDE pour le périmètre accessible ; retourne le nombre de bulletins validés."""
    return salaires_du_mois(etab, mois, annee, request=request).filter(
        statut=SalairePersonnel.StatutChoices.BROUILLON
    ).update(statut=SalairePersonnel.StatutChoices.VALIDE)


def livre(etab, mois, annee, request=None):
    """Livre de paie du mois limité aux agents accessibles, avec les totaux et agents sans bulletin."""
    salaires = list(salaires_du_mois(etab, mois, annee, request=request))
    totaux = {cle: Decimal('0') for cle in ('base', 'indemnites', 'primes', 'brut', 'cnss', 'iuts', 'autres_retenues',
                                            'retenues', 'net')}
    par_statut = {code: 0 for code, _ in SalairePersonnel.StatutChoices.choices}
    for s in salaires:
        totaux['base'] += s.salaire_base
        totaux['indemnites'] += s.indemnite_transport + s.indemnite_logement
        totaux['primes'] += s.prime_anciennete + s.autres_primes
        totaux['brut'] += s.salaire_brut
        totaux['cnss'] += s.retenue_cnss
        totaux['iuts'] += s.retenue_iuts
        totaux['autres_retenues'] += s.autres_retenues
        totaux['retenues'] += s.total_retenues
        totaux['net'] += s.salaire_net
        par_statut[s.statut] += 1
    payes = {s.personnel_id for s in salaires}
    sans_bulletin = [m for m in agents_a_payer(etab, request=request) if m.pk not in payes]
    return {'salaires': salaires, 'totaux': totaux, 'par_statut': par_statut, 'sans_bulletin': sans_bulletin,
            'mois': mois, 'annee': annee, 'libelle_mois': MOIS[mois]}
