"""Règles de cohérence des directions et affectations du personnel."""
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def valider_directeur_general(membre):
    """Autorise au plus un directeur général actif par établissement."""
    if not membre.est_directeur or not membre.is_active or not membre.etablissement_id:
        return
    existe = membre.__class__.objects.filter(
        etablissement_id=membre.etablissement_id,
        est_directeur=True,
        is_active=True,
    ).exclude(pk=membre.pk).exists()
    if existe:
        raise ValidationError({
            'est_directeur': _(
                "Un directeur général est déjà désigné pour cet établissement. "
                "Les directeurs de cycle se désignent dans leur inscription annuelle."
            )
        })


def valider_inscription_personnel(inscription):
    """Vérifie l'unicité annuelle d'une affectation et la direction du cycle."""
    from .models import InscriptionPersonnel

    if inscription.est_actif and inscription.personnel_id and inscription.annee_scolaire_id and inscription.cycle_id:
        existe = InscriptionPersonnel.objects.filter(
            personnel=inscription.personnel,
            annee_scolaire=inscription.annee_scolaire,
            cycle=inscription.cycle,
            est_actif=True,
        ).exclude(pk=inscription.pk).exists()
        if existe:
            raise ValidationError(
                _("Ce personnel a déjà une inscription active pour %(cycle)s en %(annee)s")
                % {'cycle': inscription.cycle.nom, 'annee': inscription.annee_scolaire.libelle}
            )

    if not inscription.est_directeur_cycle:
        return

    erreurs = {}
    if inscription.poste_id and inscription.poste.categorie != 'DIRECTION':
        erreurs['poste'] = _("Le poste du directeur de cycle doit appartenir à la catégorie Direction.")
    if inscription.personnel_id and inscription.cycle_id:
        if inscription.personnel.etablissement_id != inscription.cycle.etablissement_id:
            erreurs['cycle'] = _("Le cycle doit appartenir au même établissement que le membre du personnel.")
    if inscription.personnel_id and inscription.annee_scolaire_id:
        if inscription.personnel.etablissement_id != inscription.annee_scolaire.etablissement_id:
            erreurs['annee_scolaire'] = _("L'année scolaire doit appartenir au même établissement que le membre du personnel.")
    if inscription.personnel_id and inscription.poste_id:
        if inscription.personnel.etablissement_id != inscription.poste.etablissement_id:
            erreurs['poste'] = _("Le poste doit appartenir au même établissement que le membre du personnel.")

    if inscription.is_active and inscription.est_actif and inscription.annee_scolaire_id and inscription.cycle_id:
        existe = InscriptionPersonnel.objects.filter(
            annee_scolaire=inscription.annee_scolaire,
            cycle=inscription.cycle,
            is_active=True,
            est_actif=True,
            est_directeur_cycle=True,
        ).exclude(pk=inscription.pk).exists()
        if existe:
            erreurs['est_directeur_cycle'] = _(
                "Un directeur de cycle actif est déjà désigné pour cette année scolaire."
            )

    if erreurs:
        raise ValidationError(erreurs)
