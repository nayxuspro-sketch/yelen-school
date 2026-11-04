"""Pré-inscriptions : synthèse par classe demandée (demandes, places) et conversion en élève + inscription."""
from django.db import transaction
from django.utils import timezone

from parametres.models import Classe

from . import services
from .models import Eleve, Inscription, PreInscription, StatutInscriptionChoices


def synthese_par_classe(etab, annee):
    """Par classe active : demandes en attente, acceptées, inscrites depuis une pré-inscription, effectif inscrit de
    l'année, capacité et places restantes (None si la capacité n'est pas renseignée)."""
    classes = Classe.objects.filter(etablissement=etab, actif=True).select_related('cycle').order_by('cycle__ordre', 'nom')
    demandes = {}
    for p in PreInscription.objects.filter(etablissement=etab, annee_scolaire=annee).values('classe_demandee_id', 'statut'):
        compteurs = demandes.setdefault(p['classe_demandee_id'], {s: 0 for s, _ in PreInscription.Statut.choices})
        compteurs[p['statut']] += 1
    lignes = []
    for classe in classes:
        compteurs = demandes.get(classe.pk, {s: 0 for s, _ in PreInscription.Statut.choices})
        if not any(compteurs.values()) and not classe.capacite_max:
            continue
        effectif = services.effectif(classe, annee)
        restantes = max(classe.capacite_max - effectif, 0) if classe.capacite_max else None
        lignes.append({'classe': classe, 'en_attente': compteurs['EN_ATTENTE'], 'acceptees': compteurs['ACCEPTEE'],
                       'inscrites': compteurs['INSCRITE'], 'refusees': compteurs['REFUSEE'], 'effectif': effectif,
                       'capacite': classe.capacite_max, 'restantes': restantes,
                       'tension': restantes is not None and compteurs['EN_ATTENTE'] + compteurs['ACCEPTEE'] > restantes})
    return lignes


def inscrire(pre, par):
    """Crée l'élève et son inscription (statut « Non affecté », à compléter) depuis la pré-inscription ; retourne
    (inscription, erreur). Refuse une année clôturée ou une classe complète ; idempotent une fois inscrite."""
    if pre.inscription_id:
        return pre.inscription, None
    erreur = services.message_annee_cloturee(pre.annee_scolaire) or services.message_classe_complete(pre.classe_demandee, pre.annee_scolaire)
    if erreur:
        return None, erreur
    if not pre.date_naissance:
        return None, "Renseignez la date de naissance avant d'inscrire l'élève."
    with transaction.atomic():
        eleve = Eleve(
            nom=pre.nom, prenom=pre.prenom, genre=pre.genre, date_naissance=pre.date_naissance,
            lieu_naissance=pre.lieu_naissance, etablissement_origine=pre.etablissement_origine, last_classe=pre.last_classe,
            nom_pere=pre.parent_nom, telephone_parent=pre.parent_telephone, photo='',
        )
        eleve._etablissement_code = pre.etablissement.code
        eleve.save()
        inscription = Inscription.objects.create(
            eleve=eleve, annee_scolaire=pre.annee_scolaire, classe=pre.classe_demandee,
            statut=StatutInscriptionChoices.NON_AFFECTE,
        )
        pre.inscription = inscription
        pre.statut = PreInscription.Statut.INSCRITE
        pre.decidee_par = par
        pre.decidee_le = timezone.now()
        pre.save(update_fields=['inscription', 'statut', 'decidee_par', 'decidee_le', 'updated_at'])
    return inscription, None
