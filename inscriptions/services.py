"""Règles d'inscription : capacité des classes, année clôturée, réinscription et passage de classe."""
from django.db import IntegrityError, transaction

from parametres.models import AnneeScolaire
from parametres.niveaux import cle_niveau, niveau_suivant
from .models import Inscription, StatutInscriptionChoices

# Décisions de conseil qui ne proposent aucune classe de destination.
_SANS_PASSAGE = ('EXCLUSION', 'ORIENTATION')


class InscriptionImpossible(ValueError):
    """Règle métier violée : année clôturée, classe complète, double inscription, classe étrangère."""


# ── Années ────────────────────────────────────────────────────────────────────

def annee_suivante(annee):
    """Première année scolaire de l'établissement qui commence après ``annee`` (None si elle n'existe pas encore)."""
    return (AnneeScolaire.objects.filter(etablissement=annee.etablissement, date_debut__gt=annee.date_debut)
            .order_by('date_debut').first())


def message_annee_cloturee(annee):
    """Message d'erreur si l'année est clôturée, sinon None."""
    if not annee.cloturee:
        return None
    return (f"L'année scolaire {annee.libelle} est clôturée : les inscriptions ne peuvent plus être créées ni "
            "modifiées. Un responsable peut la rouvrir dans Paramètres → Années scolaires.")


# ── Capacité ──────────────────────────────────────────────────────────────────

def effectif(classe, annee, exclure=None):
    """Inscriptions actives (hors abandon) de la classe pour l'année, ``exclure`` non comptée."""
    inscriptions = (Inscription.objects.filter(classe=classe, annee_scolaire=annee)
                    .exclude(statut=StatutInscriptionChoices.ABANDON))
    if exclure is not None and not exclure._state.adding:
        inscriptions = inscriptions.exclude(pk=exclure.pk)
    return inscriptions.count()


def message_classe_complete(classe, annee, exclure=None):
    """Message d'erreur si la classe a atteint sa capacité pour l'année, sinon None."""
    if not classe.capacite_max:
        return None
    occupe = effectif(classe, annee, exclure)
    if occupe < classe.capacite_max:
        return None
    return (f"Classe {classe.nom} complète : {occupe}/{classe.capacite_max} places occupées pour {annee.libelle}. "
            "Choisissez une autre classe ou augmentez la capacité dans Paramètres → Classes.")


# ── Décisions de conseil et classe proposée ───────────────────────────────────

def decisions_par_inscription(annee):
    """Dernière décision de conseil de classe de chaque inscription de l'année : {inscription_id: code}."""
    from viescolaire.models import DecisionConseil
    return dict(DecisionConseil.objects.filter(inscription__annee_scolaire=annee)
                .order_by('conseil__date_conseil', 'created_at').values_list('inscription_id', 'decision'))


def libelle_decision(code):
    from viescolaire.models import DecisionConseil
    return DecisionConseil.DecisionChoices(code).label if code else ''


def classe_proposee(inscription, decision, classes):
    """Classe de destination proposée parmi ``classes`` (classes actives de l'établissement, triées par niveau) :
    redoublement → même classe ; passage, rachat ou absence de décision → première classe du niveau supérieur ;
    exclusion ou réorientation → aucune."""
    if decision in _SANS_PASSAGE:
        return None
    if decision == 'REDOUBLEMENT':
        return next((c for c in classes if c.pk == inscription.classe_id), None)
    suivant = niveau_suivant(inscription.classe.niveau)
    if not suivant:
        return None
    return next((c for c in classes if cle_niveau(c.niveau) == suivant), None)


# ── Réinscription ─────────────────────────────────────────────────────────────

def reinscrire(inscription, classe, annee_cible, statut_eleve=None):
    """Inscrit l'élève de ``inscription`` dans ``classe`` pour ``annee_cible`` en reprenant son statut élève
    (donc ses tarifs) ; il est marqué redoublant s'il reste au même niveau. Exonération et bourses ne sont pas
    reconduites. Lève ``InscriptionImpossible`` si une règle s'y oppose."""
    if classe.etablissement_id != inscription.classe.etablissement_id:
        raise InscriptionImpossible("Cette classe n'appartient pas à votre établissement.")
    for message in (message_annee_cloturee(annee_cible), message_classe_complete(classe, annee_cible)):
        if message:
            raise InscriptionImpossible(message)
    eleve = inscription.eleve
    if Inscription.objects.filter(eleve=eleve, annee_scolaire=annee_cible).exists():
        raise InscriptionImpossible(f"{eleve.get_nom_complet()} est déjà inscrit(e) pour {annee_cible.libelle}.")
    redouble = cle_niveau(classe.niveau) == cle_niveau(inscription.classe.niveau)
    try:
        with transaction.atomic():
            nouvelle = Inscription.objects.create(
                eleve=eleve, annee_scolaire=annee_cible, classe=classe,
                statut=StatutInscriptionChoices.AFFECTE,
                statut_eleve=statut_eleve or inscription.statut_eleve,
                est_redoublant=redouble, classe_redoublee=inscription.classe.nom if redouble else '',
            )
    except IntegrityError as exc:
        raise InscriptionImpossible(f"{eleve.get_nom_complet()} est déjà inscrit(e) pour {annee_cible.libelle}.") from exc
    eleve.last_classe, eleve.last_annee = classe.nom, annee_cible.libelle
    eleve.save(update_fields=['last_classe', 'last_annee'])
    return nouvelle
