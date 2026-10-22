"""
Import des notes d'une classe depuis le fichier existant de l'école : une ligne
par élève, une colonne par matière, pour un trimestre et un type d'évaluation.

Chaque colonne de matière devient une évaluation (réutilisée si une évaluation
du même titre existe déjà pour la matière et le trimestre, ce qui rend un
second import du même fichier sans effet de bord) ; chaque cellule devient une
note (créée ou remplacée). Les cellules vides ne touchent à rien.
"""
from dataclasses import dataclass, field

from django.db import transaction

from core.importation import (
    Champ, cle_nom_complet, cle_personne, en_note, initiales, nombre, normaliser, separer_nom_prenom, texte,
)
from .models import Evaluation, Note

CHAMPS_ELEVE = (
    Champ('matricule', 'Matricule',
          ('matricule', 'matricule eleve', 'n matricule', 'numero matricule', 'num matricule', 'identifiant',
           'id eleve', 'code eleve', 'id')),
    Champ('nom', 'Nom', ('nom', 'noms', 'nom de famille', 'nom eleve', 'nom de l eleve', 'last name')),
    Champ('prenom', 'Prénom(s)', ('prenom', 'prenoms', 'prenom s', 'prenoms s', 'prenom eleve', 'first name')),
    Champ('nom_complet', 'Nom et prénom(s) — une seule colonne',
          ('nom et prenom', 'nom et prenoms', 'noms et prenoms', 'nom prenom', 'nom prenoms', 'noms prenoms',
           'nom complet', 'eleve', 'eleves', 'nom et prenom s', 'nom prenom s', 'nom et prenoms de l eleve')),
)

# Entêtes qui ne sont jamais des matières.
_HORS_MATIERES = frozenset({
    'n', 'no', 'num', 'numero', 'rang', 'rg', 'moyenne', 'moy', 'moyenne generale', 'total', 'tot', 'observation',
    'observations', 'obs', 'appreciation', 'appreciations', 'mention', 'decision', 'sexe', 'genre', 's',
    'date de naissance', 'classe', 'coef', 'coefficient', 'points', 'total points', 'absences', 'abs',
})


def detecter_matieres(entetes, enseignements, colonnes_prises) -> dict:
    """index de colonne → enseignement, par rapprochement du libellé avec la matière.

    Égalité avec le nom, le nom complet ou le code de la matière, puis début
    commun d'au moins trois lettres (« Math » ↔ « Mathématiques »), puis
    initiales (« SVT », « HG », « PC »). Une matière n'est attribuée qu'une fois.
    """
    libres = [(i, normaliser(e)) for i, e in enumerate(entetes)
              if i not in colonnes_prises and normaliser(e) and normaliser(e) not in _HORS_MATIERES]
    cles = []
    for ens in enseignements:
        matiere = ens.matiere
        cles.append((ens, {normaliser(matiere.nom), normaliser(matiere.nom_complet), normaliser(matiere.code)} - {''},
                     initiales(matiere.nom)))
    correspondance, attribues = {}, set()

    def attribuer(index, ens):
        correspondance[index] = ens
        attribues.add(ens.pk)

    for index, libelle in libres:
        for ens, exacts, _ in cles:
            if ens.pk not in attribues and libelle in exacts:
                attribuer(index, ens)
                break
    for index, libelle in libres:
        if index in correspondance:
            continue
        for ens, exacts, ini in cles:
            if ens.pk in attribues:
                continue
            if any(len(libelle) >= 3 and (e.startswith(libelle) or libelle.startswith(e)) for e in exacts) \
                    or (' ' not in libelle and len(libelle) >= 2 and libelle == ini):
                attribuer(index, ens)
                break
    return correspondance


def verifier_correspondance(correspondance_eleve: dict, matieres: dict) -> list:
    messages = []
    if not ({'matricule', 'nom_complet'} & set(correspondance_eleve)) and \
            not ('nom' in correspondance_eleve and 'prenom' in correspondance_eleve):
        messages.append("Désignez la colonne qui identifie l'élève : matricule, nom et prénom, "
                        "ou une colonne unique « Nom et prénom(s) ».")
    if not matieres:
        messages.append("Désignez au moins une colonne de matière.")
    return messages


@dataclass
class LigneNotes:
    numero: int
    identite: str
    inscription_id: object
    notes: dict = field(default_factory=dict)   # enseignement.pk → (valeur, absent)


@dataclass
class AnalyseNotes:
    lignes: list = field(default_factory=list)
    erreurs: list = field(default_factory=list)     # (numéro de ligne, identité, motif)
    bloquants: list = field(default_factory=list)   # motifs qui empêchent tout import
    nb_notes: int = 0
    nb_remplacees: int = 0

    @property
    def nb_eleves(self):
        return len(self.lignes)


def _index_inscriptions(inscriptions):
    """Clés de reconnaissance → inscription ; une clé portée par deux élèves est ambiguë (None)."""
    index = {}

    def poser(cle, inscription):
        if not cle or cle == '|':
            return
        index[cle] = None if cle in index and index[cle] is not inscription else inscription

    for inscription in inscriptions:
        eleve = inscription.eleve
        poser('m:' + normaliser(eleve.matricule), inscription)
        poser('p:' + cle_personne(eleve.nom, eleve.prenom), inscription)
        poser('c:' + cle_nom_complet(eleve.nom, eleve.prenom), inscription)
        poser('c:' + cle_nom_complet(eleve.prenom, eleve.nom), inscription)
    return index


def _evaluation_existante(enseignement, trimestre, type_evaluation, titre):
    """L'évaluation que l'import alimente si elle existe déjà (la plus ancienne en cas d'homonymes)."""
    return Evaluation.objects.filter(
        enseignement=enseignement, trimestre=trimestre, type_evaluation=type_evaluation, titre=titre,
    ).order_by('date_planifiee', 'pk').first()


def analyser(feuille, correspondance_eleve: dict, matieres: dict, inscriptions, bareme, trimestre,
             type_evaluation, titre) -> AnalyseNotes:
    """Reconnaît chaque ligne parmi les élèves de la classe et convertit les notes, sans rien écrire."""
    analyse = AnalyseNotes()
    index = _index_inscriptions(inscriptions)
    vues = {}

    def cellule(ligne, code):
        i = correspondance_eleve.get(code)
        return ligne[i] if i is not None and i < len(ligne) else None

    # Évaluations déjà existantes (import précédent) : notes qui seront remplacées, barème incompatible.
    existantes = {}
    for ens in matieres.values():
        evaluation = _evaluation_existante(ens, trimestre, type_evaluation, titre)
        if evaluation is not None:
            existantes[ens.pk] = evaluation
    for ens_pk, ev in existantes.items():
        if ev.bareme != bareme:
            matiere = next(e.matiere.nom for e in matieres.values() if e.pk == ens_pk)
            analyse.bloquants.append(
                f"Une évaluation « {titre} » existe déjà en {matiere} pour ce trimestre avec un barème de "
                f"{nombre(ev.bareme)} : reprenez ce barème ou changez le titre.")
    deja_notees = set(Note.objects.filter(evaluation__in=existantes.values())
                      .values_list('inscription_id', 'evaluation__enseignement_id'))

    for numero, ligne in zip(feuille.numeros, feuille.lignes):
        matricule = texte(cellule(ligne, 'matricule'))
        if 'nom' in correspondance_eleve or 'prenom' in correspondance_eleve:
            nom, prenom = texte(cellule(ligne, 'nom')), texte(cellule(ligne, 'prenom'))
        else:
            nom, prenom = separer_nom_prenom(cellule(ligne, 'nom_complet'))
        identite = f'{nom} {prenom}'.strip() or matricule
        if not identite:
            continue

        inscription = None
        cles = []
        if matricule:
            cles.append('m:' + normaliser(matricule))
        if nom or prenom:
            cles += ['p:' + cle_personne(nom, prenom), 'c:' + cle_nom_complet(nom, prenom)]
        for cle in cles:
            if cle in index:
                inscription = index[cle]
                if inscription is None:
                    analyse.erreurs.append((numero, identite, 'homonymes dans la classe : ajoutez la colonne Matricule'))
                break
        if inscription is None:
            if not any(cle in index for cle in cles):
                analyse.erreurs.append((numero, identite, 'élève introuvable parmi les inscrits de la classe'))
            continue
        if inscription.pk in vues:
            analyse.erreurs.append((numero, identite, f'déjà présent à la ligne {vues[inscription.pk]}'))
            continue
        vues[inscription.pk] = numero

        notes = {}
        for index_colonne, ens in matieres.items():
            valeur = ligne[index_colonne] if index_colonne < len(ligne) else None
            try:
                note = en_note(valeur, bareme)
            except ValueError as exc:
                analyse.erreurs.append((numero, identite, f'{ens.matiere.nom} : {exc}'))
                continue
            if note is None:
                continue
            notes[ens.pk] = note
            if (inscription.pk, ens.pk) in deja_notees:
                analyse.nb_remplacees += 1
        if notes:
            analyse.nb_notes += len(notes)
            analyse.lignes.append(LigneNotes(numero=numero, identite=identite, inscription_id=inscription.pk,
                                             notes=notes))
    return analyse


@dataclass
class ResultatNotes:
    evaluations_creees: int = 0
    notes_creees: int = 0
    notes_remplacees: int = 0


def importer(analyse: AnalyseNotes, matieres: dict, trimestre, type_evaluation, titre, bareme, date_evaluation):
    """Crée les évaluations manquantes puis enregistre toutes les notes, en une seule transaction."""
    resultat = ResultatNotes()
    with transaction.atomic():
        evaluations = {}
        for ens in matieres.values():
            evaluation = _evaluation_existante(ens, trimestre, type_evaluation, titre)
            if evaluation is None:
                evaluation = Evaluation.objects.create(
                    enseignement=ens, trimestre=trimestre, type_evaluation=type_evaluation, titre=titre,
                    date_planifiee=date_evaluation, date_effectuee=date_evaluation, bareme=bareme,
                    statut=Evaluation.StatutChoices.TERMINEE,
                )
                resultat.evaluations_creees += 1
            evaluations[ens.pk] = evaluation
        for ligne in analyse.lignes:
            for ens_pk, (valeur, absent) in ligne.notes.items():
                note, creee = Note.objects.get_or_create(
                    inscription_id=ligne.inscription_id, evaluation=evaluations[ens_pk],
                    defaults={'valeur': valeur, 'observation': 'ABS' if absent else ''},
                )
                if creee:
                    resultat.notes_creees += 1
                    continue
                note.valeur = valeur
                if absent:
                    note.observation = 'ABS'
                elif note.observation == 'ABS':
                    note.observation = ''
                note.save()
                resultat.notes_remplacees += 1
    return resultat
