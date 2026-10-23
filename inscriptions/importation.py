"""
Import d'élèves (et de leurs parents) depuis le fichier existant de l'école :
champs reconnus, analyse des lignes, création des élèves et de leurs inscriptions.

Règles :
- un élève est reconnu (et non recréé) par son matricule, sinon par
  nom + prénom(s) + date de naissance ; sa fiche n'est pas modifiée ;
- l'inscription dans la classe de l'année choisie est créée si elle n'existe pas ;
- une ligne en erreur n'empêche pas l'import des autres : elle est rapportée
  avec son numéro et son motif, le fichier corrigé peut être réimporté tel quel.
"""
from collections import Counter
from dataclasses import dataclass, field

from django.db import transaction
from django.db.models import Q

from core.importation import (
    Champ, cle_personne, en_booleen, en_date, en_genre, en_telephone, normaliser, separer_nom_prenom, texte,
)
from .models import Eleve, Inscription

CHAMPS = (
    Champ('matricule', 'Matricule',
          ('matricule', 'matricule eleve', 'n matricule', 'numero matricule', 'num matricule', 'identifiant',
           'id eleve', 'code eleve', 'id'),
          aide="Conservé tel quel ; généré automatiquement s'il manque."),
    Champ('nom', 'Nom',
          ('nom', 'noms', 'nom de famille', 'nom eleve', 'nom de l eleve', 'nom famille', 'last name', 'surname',
           'patronyme'), obligatoire=True),
    Champ('prenom', 'Prénom(s)',
          ('prenom', 'prenoms', 'prenom s', 'prenoms s', 'prenom eleve', 'prenoms eleve', 'prenom de l eleve',
           'prenoms de l eleve', 'first name'), obligatoire=True),
    Champ('nom_complet', 'Nom et prénom(s) — une seule colonne',
          ('nom et prenom', 'nom et prenoms', 'noms et prenoms', 'nom prenom', 'nom prenoms', 'noms prenoms',
           'nom complet', 'eleve', 'eleves', 'nom et prenom s', 'nom et prenoms de l eleve', 'nom prenom s',
           'nom et prenom de l eleve', 'nom et prenoms eleve'),
          aide='Le nom en MAJUSCULES, puis les prénoms : « OUEDRAOGO Abdoul Kader ».'),
    Champ('genre', 'Genre (M/F)', ('genre', 'sexe', 's', 'sex', 'm f', 'g f', 'f m', 'h f', 'genre m f', 'sexe m f'),
          obligatoire=True),
    Champ('date_naissance', 'Date de naissance',
          ('date de naissance', 'date naissance', 'ne e le', 'ne le', 'nee le', 'naissance', 'ddn', 'date naiss',
           'date de naiss', 'dn', 'date of birth', 'birth date', 'birthday'), obligatoire=True),
    Champ('lieu_naissance', 'Lieu de naissance',
          ('lieu de naissance', 'lieu naissance', 'lieu naiss', 'lieu de naiss', 'ne e a', 'ne a', 'nee a', 'lieu',
           'birthplace', 'place of birth')),
    Champ('classe', 'Classe',
          ('classe', 'classes', 'class', 'classe actuelle', 'niveau classe', 'salle', 'classe frequentee'),
          aide='Les libellés du fichier seront rapprochés des classes de YELEN SCHOOL à l\'étape suivante.'),
    Champ('redoublant', 'Redoublant (Oui/Non)',
          ('redoublant', 'redoublant e', 'redouble', 'red', 'doublant', 'statut redoublant', 'redoublement',
           'redoublant oui non')),
    Champ('nationalite', 'Nationalité', ('nationalite', 'nationality')),
    Champ('telephone_parent', 'Téléphone des parents',
          ('telephone parent', 'telephone parents', 'tel parent', 'tel parents', 'contact parent', 'contact parents',
           'telephone des parents', 'telephone du parent', 'numero parent', 'numero parents', 'telephone', 'tel',
           'contact', 'contacts', 'numero', 'numero de telephone', 'portable', 'gsm', 'cellulaire', 'phone')),
    Champ('nom_pere', 'Nom du père',
          ('nom du pere', 'nom pere', 'pere', 'nom complet du pere', 'nom et prenom du pere', 'nom et prenoms du pere',
           'pere nom')),
    Champ('profession_pere', 'Profession du père',
          ('profession du pere', 'profession pere', 'metier du pere', 'fonction du pere')),
    Champ('nom_mere', 'Nom de la mère',
          ('nom de la mere', 'nom mere', 'mere', 'nom complet de la mere', 'nom et prenom de la mere',
           'nom et prenoms de la mere', 'mere nom')),
    Champ('profession_mere', 'Profession de la mère',
          ('profession de la mere', 'profession mere', 'metier de la mere', 'fonction de la mere')),
    Champ('tuteur_nom', 'Nom du tuteur',
          ('tuteur', 'nom du tuteur', 'nom tuteur', 'tuteur legal', 'responsable', 'responsable legal',
           'nom du responsable', 'parent tuteur', 'tuteur trice', 'nom tuteur trice', 'nom du parent',
           'nom parent', 'parent')),
    Champ('tuteur_telephone', 'Téléphone du tuteur',
          ('telephone tuteur', 'tel tuteur', 'contact tuteur', 'telephone du tuteur', 'telephone responsable',
           'contact responsable', 'numero tuteur')),
    Champ('tuteur_adresse', 'Adresse',
          ('adresse tuteur', 'adresse du tuteur', 'adresse', 'domicile', 'adresse parents', 'adresse des parents')),
    Champ('telephone_urgence', "Téléphone d'urgence",
          ('telephone urgence', 'telephone d urgence', 'contact urgence', 'contact d urgence', 'urgence',
           'numero urgence', 'numero d urgence')),
    Champ('email', 'Email', ('email', 'e mail', 'courriel', 'mail', 'adresse email', 'adresse e mail')),
    Champ('lieu_residence', 'Lieu de résidence',
          ('lieu de residence', 'residence', 'lieu d habitation', 'village', 'quartier', 'secteur', 'ville',
           'village ville', 'localite')),
    Champ('etablissement_origine', "Établissement d'origine",
          ('etablissement d origine', 'ecole d origine', 'etablissement origine', 'ecole precedente', 'provenance',
           'ancien etablissement', 'ecole de provenance', 'etablissement precedent', 'etablissement de provenance')),
)
CHAMPS_PAR_CODE = {c.code: c for c in CHAMPS}

# Colonnes recopiées telles quelles dans la fiche (texte), avec leur longueur maximale.
_CHAMPS_TEXTE = {
    'lieu_naissance': 200, 'nationalite': 100, 'nom_pere': 150, 'profession_pere': 100, 'nom_mere': 150,
    'profession_mere': 100, 'tuteur_nom': 150, 'tuteur_adresse': 2000, 'email': 254, 'lieu_residence': 150,
    'etablissement_origine': 200,
}
_CHAMPS_TELEPHONE = ('telephone_parent', 'tuteur_telephone', 'telephone_urgence')


def verifier_correspondance(correspondance: dict) -> list:
    """Messages bloquants si les colonnes indispensables ne sont pas désignées."""
    messages = []
    if 'nom_complet' not in correspondance and not ('nom' in correspondance and 'prenom' in correspondance):
        messages.append("Désignez la colonne du nom et celle du prénom, ou une colonne unique « Nom et prénom(s) ».")
    if 'genre' not in correspondance:
        messages.append("Désignez la colonne du genre (M/F).")
    if 'date_naissance' not in correspondance:
        messages.append("Désignez la colonne de la date de naissance.")
    return messages


@dataclass
class LigneEleve:
    numero: int
    nom: str
    prenom: str
    genre: str
    date_naissance: object
    matricule: str
    classe_libelle: str
    redoublant: bool
    champs: dict = field(default_factory=dict)
    existant_id: object = None       # élève déjà présent (matricule ou identité)

    @property
    def identite(self):
        return f'{self.nom} {self.prenom}'.strip()


@dataclass
class Analyse:
    lignes: list = field(default_factory=list)       # lignes importables (nouveaux + existants)
    erreurs: list = field(default_factory=list)      # (numéro de ligne, identité, motif)
    classes: Counter = field(default_factory=Counter)  # libellé de classe du fichier → nombre de lignes
    nb_sans_lieu: int = 0

    @property
    def nb_nouveaux(self):
        return sum(1 for l in self.lignes if l.existant_id is None)

    @property
    def nb_existants(self):
        return sum(1 for l in self.lignes if l.existant_id is not None)


def _eleves_connus(etablissement):
    """Index des élèves : matricule → (id, nom complet) pour tous (le matricule est unique en base) et,
    pour les élèves visibles par l'établissement, (nom, prénom, naissance) → id."""
    par_matricule = {normaliser(m): (pk, f'{nom} {prenom}')
                     for pk, m, nom, prenom in Eleve.objects.values_list('id', 'matricule', 'nom', 'prenom')}
    eleves = Eleve.objects.all()
    if etablissement is not None:
        eleves = eleves.filter(Q(inscriptions__classe__etablissement=etablissement) | Q(inscriptions__isnull=True))
    par_identite = {
        (cle_personne(nom, prenom), naissance): pk
        for pk, nom, prenom, naissance in eleves.distinct().values_list('id', 'nom', 'prenom', 'date_naissance')
    }
    return par_matricule, par_identite


def analyser(feuille, correspondance: dict, etablissement) -> Analyse:
    """Convertit et contrôle chaque ligne du fichier sans rien écrire en base."""
    analyse = Analyse()
    par_matricule, par_identite = _eleves_connus(etablissement)
    vues, matricules_vus = {}, {}  # identité / matricule → numéro de ligne : doublons à l'intérieur du fichier

    def cellule(ligne, code):
        index = correspondance.get(code)
        return ligne[index] if index is not None and index < len(ligne) else None

    for numero, ligne in zip(feuille.numeros, feuille.lignes):
        motifs = []
        if 'nom_complet' in correspondance and 'nom' not in correspondance:
            nom, prenom = separer_nom_prenom(cellule(ligne, 'nom_complet'))
        else:
            nom, prenom = texte(cellule(ligne, 'nom')), texte(cellule(ligne, 'prenom'))
        if not nom:
            motifs.append('nom manquant')
        if not prenom:
            motifs.append('prénom manquant')

        genre = date_naissance = None
        try:
            genre = en_genre(cellule(ligne, 'genre'))
            if genre is None:
                motifs.append('genre manquant')
        except ValueError as exc:
            motifs.append(str(exc))
        try:
            date_naissance = en_date(cellule(ligne, 'date_naissance'))
            if date_naissance is None:
                motifs.append('date de naissance manquante')
        except ValueError as exc:
            motifs.append(str(exc))

        redoublant = False
        if 'redoublant' in correspondance:
            try:
                redoublant = en_booleen(cellule(ligne, 'redoublant'))
            except ValueError as exc:
                motifs.append(f'redoublant : {exc}')

        if motifs:
            analyse.erreurs.append((numero, f'{nom} {prenom}'.strip(), ' ; '.join(motifs)))
            continue

        champs = {}
        for code, longueur in _CHAMPS_TEXTE.items():
            if code in correspondance:
                champs[code] = texte(cellule(ligne, code))[:longueur]
        for code in _CHAMPS_TELEPHONE:
            if code in correspondance:
                champs[code] = en_telephone(cellule(ligne, code))
        if not champs.get('lieu_naissance'):
            analyse.nb_sans_lieu += 1

        matricule = texte(cellule(ligne, 'matricule'))[:20]
        identite = (cle_personne(nom, prenom), date_naissance)
        if identite in vues:
            analyse.erreurs.append((numero, f'{nom} {prenom}', f'doublon de la ligne {vues[identite]} dans le fichier'))
            continue
        vues[identite] = numero
        if matricule:
            if normaliser(matricule) in matricules_vus:
                analyse.erreurs.append((numero, f'{nom} {prenom}',
                                        f'matricule « {matricule} » déjà utilisé à la ligne {matricules_vus[normaliser(matricule)]}'))
                continue
            matricules_vus[normaliser(matricule)] = numero

        existant_id = None
        connu = par_matricule.get(normaliser(matricule)) if matricule else None
        if connu is not None:
            existant_id, nom_connu = connu
            if par_identite.get(identite) != existant_id:
                # Matricule d'un autre élève (ou nom différent) : on refuse plutôt que de confondre deux enfants.
                analyse.erreurs.append((numero, f'{nom} {prenom}',
                                        f'le matricule « {matricule} » est déjà celui de {nom_connu} : '
                                        f'corrigez le matricule ou le nom'))
                continue
        if existant_id is None:
            existant_id = par_identite.get(identite)
            if existant_id is not None:
                matricule = ''  # l'élève garde son matricule YELEN

        classe_libelle = texte(cellule(ligne, 'classe'))
        if classe_libelle:
            analyse.classes[classe_libelle] += 1
        analyse.lignes.append(LigneEleve(
            numero=numero, nom=nom.upper(), prenom=prenom, genre=genre, date_naissance=date_naissance,
            matricule=matricule, classe_libelle=classe_libelle, redoublant=redoublant, champs=champs,
            existant_id=existant_id,
        ))
    return analyse


@dataclass
class Resultat:
    crees: int = 0          # élèves créés
    inscrits: int = 0       # inscriptions créées (nouveaux et existants)
    existants: int = 0      # élèves reconnus, fiche inchangée
    deja_inscrits: int = 0  # déjà inscrits cette année : rien à faire
    sans_classe: int = 0    # aucune classe désignée : fiche créée, inscription à faire à la main


def importer(analyse: Analyse, annee, classes: dict, classe_defaut, code_etablissement: str) -> Resultat:
    """Crée les élèves et inscriptions des lignes valides, en une seule transaction.

    ``classes`` : libellé du fichier → ``Classe`` (ou None : ne pas inscrire) ;
    ``classe_defaut`` : classe des lignes sans libellé (ou None).
    """
    resultat = Resultat()
    deja = set(Inscription.objects.filter(annee_scolaire=annee).values_list('eleve_id', flat=True))
    with transaction.atomic():
        for ligne in analyse.lignes:
            if ligne.existant_id is not None:
                eleve = Eleve.objects.get(pk=ligne.existant_id)
                resultat.existants += 1
            else:
                eleve = Eleve(
                    matricule=ligne.matricule, nom=ligne.nom, prenom=ligne.prenom, genre=ligne.genre,
                    date_naissance=ligne.date_naissance, **ligne.champs,
                )
                if not eleve.nationalite:
                    eleve.nationalite = 'Burkinabè'
                if code_etablissement:
                    eleve._etablissement_code = code_etablissement
                eleve.save()
                resultat.crees += 1

            classe = classes.get(ligne.classe_libelle) if ligne.classe_libelle else classe_defaut
            if classe is None:
                resultat.sans_classe += 1
                continue
            if eleve.pk in deja:
                resultat.deja_inscrits += 1
                continue
            Inscription.objects.create(
                eleve=eleve, annee_scolaire=annee, classe=classe, est_redoublant=ligne.redoublant,
                classe_redoublee=classe.nom if ligne.redoublant else '',
            )
            deja.add(eleve.pk)
            eleve.last_classe = classe.nom
            eleve.last_annee = annee.libelle
            eleve.save(update_fields=['last_classe', 'last_annee'])
            resultat.inscrits += 1
    return resultat
