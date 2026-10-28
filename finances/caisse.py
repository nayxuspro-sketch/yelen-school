"""Journal de caisse et arrêté de caisse par caissier : opérations d'une journée, totaux par mode, verrou des
saisies antidatées une fois la caisse arrêtée."""
from decimal import Decimal

from django.db.models import Sum

from .models import ClotureCaisse, ModePaiement, Paiement, Remboursement


def paiements_du_jour(etab, jour, caissier=None):
    qs = (Paiement.objects.filter(inscription__classe__etablissement=etab, date_paiement=jour)
          .select_related('inscription__eleve', 'inscription__classe', 'rubrique', 'encaisse_par')
          .order_by('created_at'))
    return qs.filter(encaisse_par=caissier) if caissier else qs


def remboursements_du_jour(etab, jour, caissier=None):
    qs = (Remboursement.objects.filter(paiement__inscription__classe__etablissement=etab, date_remboursement=jour,
                                       is_active=True)
          .select_related('paiement__inscription__eleve', 'paiement__rubrique', 'rembourse_par')
          .order_by('created_at'))
    return qs.filter(rembourse_par=caissier) if caissier else qs


def totaux_journee(paiements, remboursements):
    """Totaux par mode, total encaissé, remboursements (espèces) et espèces théoriques en caisse."""
    par_mode = {code: Decimal('0') for code, _ in ModePaiement.choices}
    for ligne in paiements.order_by().values('mode_paiement').annotate(s=Sum('montant')):
        par_mode[ligne['mode_paiement']] = ligne['s'] or Decimal('0')
    total_rembourse = remboursements.aggregate(s=Sum('montant'))['s'] or Decimal('0')
    total = sum(par_mode.values(), Decimal('0'))
    return {
        'par_mode': [(label, par_mode[code]) for code, label in ModePaiement.choices],
        'especes': par_mode[ModePaiement.ESPECES],
        'mobile_money': par_mode[ModePaiement.MOBILE_MONEY],
        'cheque': par_mode[ModePaiement.CHEQUE],
        'virement': par_mode[ModePaiement.VIREMENT],
        'total': total,
        'nb_operations': paiements.count() + remboursements.count(),
        'total_rembourse': total_rembourse,
        'especes_theoriques': par_mode[ModePaiement.ESPECES] - total_rembourse,
    }


def caissiers_du_jour(etab, jour):
    """Utilisateurs ayant encaissé ou remboursé ce jour-là, triés par nom."""
    ids = set(paiements_du_jour(etab, jour).exclude(encaisse_par=None).values_list('encaisse_par_id', flat=True))
    ids |= set(remboursements_du_jour(etab, jour).exclude(rembourse_par=None).values_list('rembourse_par_id', flat=True))
    from accounts.models import User
    return list(User.objects.filter(pk__in=ids).order_by('last_name', 'first_name'))


def arreter_caisse(etab, jour, caissier, montant_compte, observation, par):
    """Fige les totaux de la journée du caissier et enregistre les espèces comptées ; lève ValueError si la
    caisse est déjà arrêtée."""
    if ClotureCaisse.objects.filter(etablissement=etab, date=jour, caissier=caissier).exists():
        raise ValueError(f"La caisse de {caissier.get_full_name()} du {jour:%d/%m/%Y} est déjà arrêtée.")
    t = totaux_journee(paiements_du_jour(etab, jour, caissier), remboursements_du_jour(etab, jour, caissier))
    return ClotureCaisse.objects.create(
        etablissement=etab, date=jour, caissier=caissier, nb_operations=t['nb_operations'],
        total_especes=t['especes'], total_mobile_money=t['mobile_money'], total_cheque=t['cheque'],
        total_virement=t['virement'], total_rembourse=t['total_rembourse'], montant_compte=montant_compte,
        ecart=montant_compte - t['especes_theoriques'], observation=(observation or '')[:200], cloture_par=par,
    )


def message_caisse_arretee(etab, caissier, jour):
    """Message de refus si le caissier a déjà arrêté sa caisse pour ``jour`` ou un jour postérieur, sinon None."""
    if etab is None or caissier is None:
        return None
    cloture = (ClotureCaisse.objects.filter(etablissement=etab, caissier=caissier, date__gte=jour)
               .order_by('-date').first())
    if cloture is None:
        return None
    return (f"Votre caisse est arrêtée jusqu'au {cloture.date:%d/%m/%Y} : aucune opération datée du "
            f"{jour:%d/%m/%Y} ne peut plus être saisie. Un responsable peut rouvrir la caisse "
            "(Finances → Journal de caisse).")
