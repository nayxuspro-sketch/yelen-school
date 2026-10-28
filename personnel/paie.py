"""Paie du mois : préparation en masse des salaires (un brouillon par agent à partir de son dernier bulletin),
validation groupée, livre de paie (récapitulatif mensuel) et bulletins du mois en un seul PDF."""
from decimal import Decimal

from django.db import transaction

from .models import MembrePersonnel, SalairePersonnel

MOIS = dict(SalairePersonnel.MOIS_CHOICES)


def salaires_du_mois(etab, mois, annee):
    return (SalairePersonnel.objects.filter(personnel__etablissement=etab, mois=mois, annee=annee)
            .select_related('personnel', 'annee_scolaire').order_by('personnel__nom', 'personnel__prenom'))


def agents_a_payer(etab):
    """Agents permanents de l'établissement (actifs, non vacataires : les vacataires relèvent des bulletins de vacation)."""
    return MembrePersonnel.objects.filter(etablissement=etab, is_active=True, est_vacataire=False).order_by('nom', 'prenom')


def preparer(etab, mois, annee, annee_scolaire, par):
    """Crée un brouillon pour chaque agent à payer sans bulletin ce mois-ci : salaire de base, indemnités et retenues
    CNSS / IUTS repris de son dernier bulletin, prime d'ancienneté recalculée, primes et retenues exceptionnelles à
    zéro. Retourne (bulletins créés, agents sans bulletin de référence — à saisir à la main)."""
    deja = set(SalairePersonnel.objects.filter(personnel__etablissement=etab, mois=mois, annee=annee)
               .values_list('personnel_id', flat=True))
    crees, sans_reference = [], []
    with transaction.atomic():
        for membre in agents_a_payer(etab).exclude(pk__in=deja):
            dernier = SalairePersonnel.objects.filter(personnel=membre).order_by('-annee', '-mois').first()
            if dernier is None:
                sans_reference.append(membre)
                continue
            salaire = SalairePersonnel(
                personnel=membre, annee_scolaire=annee_scolaire, mois=mois, annee=annee,
                salaire_base=dernier.salaire_base, indemnite_transport=dernier.indemnite_transport,
                indemnite_logement=dernier.indemnite_logement,
                prime_anciennete=SalairePersonnel.calculer_prime_anciennete(membre, dernier.salaire_base),
                autres_primes=Decimal('0'), retenue_cnss=dernier.retenue_cnss, retenue_iuts=dernier.retenue_iuts,
                autres_retenues=Decimal('0'), statut=SalairePersonnel.StatutChoices.BROUILLON, created_by=par,
            )
            salaire.save()
            crees.append(salaire)
    return crees, sans_reference


def valider_brouillons(etab, mois, annee):
    """BROUILLON → VALIDE pour tout le mois ; retourne le nombre de bulletins validés."""
    return salaires_du_mois(etab, mois, annee).filter(statut=SalairePersonnel.StatutChoices.BROUILLON).update(
        statut=SalairePersonnel.StatutChoices.VALIDE)


def livre(etab, mois, annee):
    """Livre de paie du mois : une ligne par bulletin (brut, retenues, net) et les totaux, agents sans bulletin."""
    salaires = list(salaires_du_mois(etab, mois, annee))
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
    sans_bulletin = [m for m in agents_a_payer(etab) if m.pk not in payes]
    return {'salaires': salaires, 'totaux': totaux, 'par_statut': par_statut, 'sans_bulletin': sans_bulletin,
            'mois': mois, 'annee': annee, 'libelle_mois': MOIS[mois]}
