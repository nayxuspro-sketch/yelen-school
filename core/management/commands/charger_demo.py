"""Jeu de données de démonstration : un établissement complet, prêt à visiter.

Une seule commande remplit une base vierge (démonstrations, formation, captures du guide, tests de
charge) : identité et agrément, année en cours et année précédente, cycles et classes, statuts, rubriques
et tarifs conformes aux plafonds, personnel et comptes, élèves inscrits, matières enseignées, évaluations
et notes des premiers trimestres, paiements et signataires des documents.

    python manage.py charger_demo                 # établissement « DEMO », 48 élèves
    python manage.py charger_demo --reset         # supprime puis recrée ce même établissement
    python manage.py charger_demo --eleves 240 --etablissement ESSAI

La commande ne touche qu'à l'établissement qu'elle crée : les autres données de la base sont intactes.
"""
import datetime as dt
import random
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction

from accounts.models import User
from core.models import RoleChoices
from etablissements.models import Etablissement
from finances.models import ModePaiement, Paiement
from inscriptions.models import Eleve, Inscription
from parametres.models import (
    AnneeScolaire, Classe, Cycle, IdentiteEtablissement, RubriquePaiement, SignataireDocument, StatutEleve,
    TarifScolarite, TypeDocument,
)
from personnel.models import MembrePersonnel
from pedagogie.models import Enseignement, Evaluation, Matiere, MatiereCycle, Note, Trimestre, TypeEvaluation
from manuels.models import AttributionManuel, EtatManuel, ExemplaireManuel, ManuelScolaire
from personnel.models import EvaluationAnnuelle, PointagePersonnel, ReglagePointage
from pedagogie.utils import CalculateurMoyenne

MOT_DE_PASSE = 'Demo2026!'
GRAINE = 2026

NOMS = ('OUÉDRAOGO', 'SAWADOGO', 'KABORÉ', 'TRAORÉ', 'ZONGO', 'COMPAORÉ', 'SANOU', 'BATIONO', 'NIKIÉMA',
        'ILBOUDO', 'KONATÉ', 'SOMÉ', 'TAPSOBA', 'YAMÉOGO', 'DAO', 'COULIBALY', 'DIALLO', 'OUATTARA')
PRENOMS_F = ('Aminata', 'Fatimata', 'Awa', 'Mariam', 'Rasmata', 'Salamata', 'Balkissa', 'Adjaratou', 'Alizèta',
             'Chantal', 'Grâce', 'Josiane')
PRENOMS_M = ('Issouf', 'Boureima', 'Moussa', 'Adama', 'Salif', 'Karim', 'Rasmané', 'Abdoul', 'Ousmane',
             'Serge', 'Éric', 'Hamado')

# code, nom, ordre
CYCLES = (('PRES', 'Préscolaire', 1), ('PRIM', 'Primaire', 2), ('POST', 'Post-primaire', 3))
# nom, niveau, code cycle
CLASSES = (('Petite section', 'PS', 'PRES'), ('Grande section', 'GS', 'PRES'),
           ('CP1', 'CP1', 'PRIM'), ('CP2', 'CP2', 'PRIM'), ('CM1', 'CM1', 'PRIM'), ('CM2', 'CM2', 'PRIM'),
           ('6e A', '6E', 'POST'), ('5e A', '5E', 'POST'))
# code, nom, soumise au plafond, ordre
RUBRIQUES = (('INSCRIPTION', 'Inscription', True, 1), ('SCOLARITE', 'Scolarité', True, 2),
             ('CANTINE', 'Cantine', False, 3), ('TENUE', 'Tenue scolaire', False, 4))
# code cycle → (inscription, scolarité annuelle, cantine) en FCFA — total plafonné sous le plafond de la
# catégorie 2 / zone 1 (PRES 100 000, PRIM 80 000, POST 120 000 — parametres.plafonds)
TARIFS = {'PRES': (7500, 45000, 25000), 'PRIM': (10000, 60000, 30000), 'POST': (15000, 90000, 35000)}
# code cycle → (code, nom, coefficient)
MATIERES = {
    'PRES': (('EVEIL', 'Éveil', 2), ('LANG', 'Langage', 3), ('MOTR', 'Motricité', 1)),
    'PRIM': (('FRA', 'Français', 3), ('MATH', 'Mathématiques', 3), ('SVT', 'Sciences d’observation', 2),
             ('HG', 'Histoire-Géographie', 2), ('ECM', 'Éducation civique et morale', 1)),
    'POST': (('FRA', 'Français', 3), ('MATH', 'Mathématiques', 3), ('SVT', 'Sciences de la vie et de la terre', 3),
             ('PCT', 'Physique-Chimie', 3), ('ANG', 'Anglais', 2), ('HG', 'Histoire-Géographie', 2)),
}
# matricule, nom, prénom, fonction, est_directeur, est_censeur, compte
PERSONNEL = (
    ('DIR-01', 'OUÉDRAOGO', 'Issa', 'Directeur', True, False, ('direction@demo.bf', RoleChoices.DIRECTEUR)),
    ('CEN-01', 'KABORÉ', 'Salifou', 'Censeur', False, True, ('censeur@demo.bf', RoleChoices.CENSEUR)),
    ('SEC-01', 'SAWADOGO', 'Balkissa', 'Secrétaire', False, False, ('secretariat@demo.bf', RoleChoices.SECRETAIRE)),
    ('CPT-01', 'COMPAORÉ', 'Adama', 'Comptable', False, False, ('comptabilite@demo.bf', RoleChoices.COMPTABLE)),
    ('ENS-01', 'TRAORÉ', 'Moussa', 'Enseignant de mathématiques', False, False, ('e.moussa@demo.bf', RoleChoices.ENSEIGNANT)),
    ('ENS-02', 'ZONGO', 'Awa', 'Enseignante de français', False, False, ('e.awa@demo.bf', RoleChoices.ENSEIGNANT)),
    ('ENS-03', 'NIKIÉMA', 'Boureima', 'Enseignant de sciences', False, False, ('e.boureima@demo.bf', RoleChoices.ENSEIGNANT)),
    ('ENS-04', 'SANOU', 'Mariam', 'Enseignante du primaire', False, False, ('e.mariam@demo.bf', RoleChoices.ENSEIGNANT)),
)


def libelle_annee(jour=None):
    """Libellé de l'année scolaire en cours : « 2026-2027 » de septembre à août."""
    jour = jour or dt.date.today()
    debut = jour.year if jour.month >= 9 else jour.year - 1
    return f'{debut}-{debut + 1}'


class Command(BaseCommand):
    help = "Crée un établissement de démonstration complet (année en cours, élèves, notes, paiements)."

    def add_arguments(self, parser):
        parser.add_argument('--etablissement', default='DEMO', help="Code de l'établissement à créer (DEMO).")
        parser.add_argument('--eleves', type=int, default=48, help="Nombre d'élèves (48 par défaut).")
        parser.add_argument('--reset', action='store_true',
                           help="Supprime l'établissement de démonstration avant de le recréer.")

    def handle(self, *args, **options):
        code = options['etablissement'].strip().upper()
        nb_eleves = options['eleves']
        if nb_eleves < len(CLASSES):
            raise SystemExit(f"Au moins {len(CLASSES)} élèves sont nécessaires pour remplir les classes.")

        if options['reset']:
            self._supprimer(code)

        with transaction.atomic():
            etab = self._etablissement(code)
            identite = self._identite(etab)
            courante, precedente = self._annees(etab)
            statuts = self._statuts(etab)
            classes = self._cycles_classes(etab)
            rubriques = self._rubriques(etab)
            self._tarifs(etab, precedente, classes, rubriques, statuts)
            self._tarifs(etab, courante, classes, rubriques, statuts)
            personnel = self._personnel(etab)
            self._comptes(etab, personnel)
            courantes, precedentes = self._eleves(etab, courante, precedente, classes, statuts, nb_eleves)
            self._familles(etab, courantes)
            self._pedagogie(annee=precedente, classes=classes, personnel=personnel, eleves=precedentes)
            self._pedagogie(annee=courante, classes=classes, personnel=personnel, eleves=courantes)
            self._paiements(precedente, precedentes, rubriques, statuts)
            self._paiements(courante, courantes, rubriques, statuts)
            self._signataires(courante, personnel)
            self._pointages(courante, personnel)
            self._evaluations(courante, personnel)
            self._bibliotheque(courante, courantes)

        self._compte_rendu(etab, identite, courante, nb_eleves)

    # ── Établissement ────────────────────────────────────────────────────────────────────────────
    def _supprimer(self, code):
        """Supprime l'établissement de démonstration, sauf si son historique financier est protégé.

        Sous PostgreSQL, un paiement comptabilisé est immuable (`finances/migrations/0016`) : la suppression
        est alors refusée proprement, avec la marche à suivre, au lieu de laisser remonter une erreur SQL."""
        try:
            with transaction.atomic():
                supprimes = Etablissement.objects.filter(code=code).delete()
        except IntegrityError as exc:
            raise CommandError(
                f"Établissement {code} non supprimé : son historique financier est immuable (paiements "
                "comptabilisés). Choisissez un autre code (--etablissement ESSAI) ou une base d'essai SQLite."
            ) from exc
        self.stdout.write(f"Établissement {code} supprimé ({supprimes[0]} objet(s)).")

    def _etablissement(self, code):
        return Etablissement.objects.get_or_create(
            code=code, defaults={'nom': 'Complexe Scolaire Laafi', 'ville': 'Ouagadougou',
                                 'adresse': 'Secteur 30, Karpala', 'telephone': '+226 25 00 00 00',
                                 'email': 'contact@laafi.bf'},
        )[0]

    def _identite(self, etab):
        return IdentiteEtablissement.objects.get_or_create(
            etablissement=etab, defaults={
                'nom_etablissement': 'COMPLEXE SCOLAIRE LAAFI', 'sigle': 'CSL', 'type_etablissement': 'PRIVE',
                'numero_agrement_mena': '2020-0456/MENAPLN', 'date_agrement': dt.date(2020, 9, 1),
                'categorie_reglementaire': 2, 'zone_implantation': 1,
                'adresse_complete': 'Secteur 30, Karpala, Ouagadougou', 'ville': 'Ouagadougou',
                'province': 'Kadiogo', 'region': 'Centre', 'telephone': '+226 25 00 00 00',
                'email': 'contact@laafi.bf', 'nom_directeur': 'Issa OUÉDRAOGO',
                'devise': 'Discipline, travail, réussite',
            },
        )[0]

    def _annees(self, etab):
        jour = dt.date.today()
        debut = jour.year if jour.month >= 9 else jour.year - 1
        courante, _ = AnneeScolaire.objects.get_or_create(
            etablissement=etab, libelle=f'{debut}-{debut + 1}',
            defaults={'date_debut': dt.date(debut, 10, 1), 'date_fin': dt.date(debut + 1, 6, 30),
                      'est_courante': True},
        )
        precedente, _ = AnneeScolaire.objects.get_or_create(
            etablissement=etab, libelle=f'{debut - 1}-{debut}',
            defaults={'date_debut': dt.date(debut - 1, 10, 1), 'date_fin': dt.date(debut, 6, 30),
                      'est_courante': False, 'cloturee': True},
        )
        return courante, precedente

    def _statuts(self, etab):
        modes = (('NOUVEAU', 'Nouveau', '#0EA5E9'), ('AFFECTE', 'Affecté', '#00A86B'),
                 ('REDOUB', 'Redoublant', '#F59E0B'))
        return {code: StatutEleve.objects.get_or_create(
            etablissement=etab, code=code, defaults={'nom': nom, 'couleur': couleur})[0]
            for code, nom, couleur in modes}

    def _cycles_classes(self, etab):
        self.cycles = {
            code: Cycle.objects.get_or_create(etablissement=etab, code=code,
                                              defaults={'nom': nom, 'ordre': ordre})[0]
            for code, nom, ordre in CYCLES
        }
        return {
            nom: Classe.objects.get_or_create(
                etablissement=etab, nom=nom,
                defaults={'cycle': self.cycles[code_cycle], 'niveau': niveau, 'capacite_max': 60})[0]
            for nom, niveau, code_cycle in CLASSES
        }

    def _rubriques(self, etab):
        return {code: RubriquePaiement.objects.get_or_create(
            etablissement=etab, code=code,
            defaults={'nom': nom, 'soumise_plafond': plafond, 'ordre': ordre,
                      'obligatoire': code in ('INSCRIPTION', 'SCOLARITE')})[0]
            for code, nom, plafond, ordre in RUBRIQUES}

    def _tarifs(self, etab, annee, classes, rubriques, statuts):
        for nom_classe, classe in classes.items():
            inscription, scolarite, cantine = TARIFS[classe.cycle.code]
            for code, montant in (('INSCRIPTION', inscription), ('SCOLARITE', scolarite), ('CANTINE', cantine)):
                if code == 'CANTINE' and nom_classe not in ('CP1', 'CM2', '6e A'):
                    continue                                    # service annexe souscrit par quelques classes
                TarifScolarite.objects.get_or_create(
                    etablissement=etab, annee_scolaire=annee, classe=classe, statut_eleve=statuts['AFFECTE'],
                    rubrique=rubriques[code], defaults={'montant': Decimal(montant)},
                )

    def _personnel(self, etab):
        membres = {}
        for matricule, nom, prenom, fonction, directeur, censeur, (email, _role) in PERSONNEL:
            membre = MembrePersonnel.objects.get_or_create(
                etablissement=etab, matricule=matricule,
                defaults={'nom': nom, 'prenom': prenom, 'genre': 'F' if prenom in PRENOMS_F else 'M',
                          'date_naissance': dt.date(1985, 5, 12), 'lieu_naissance': 'Ouagadougou',
                          'fonction': fonction, 'date_embauche': dt.date(2019, 9, 2),
                          'telephone': '+226 70 00 00 00', 'est_directeur': directeur, 'est_censeur': censeur},
            )[0]
            if membre.email != email:                       # relie la fiche au compte (enseignant titulaire)
                membre.email = email
                membre.save(update_fields=['email'])
            membres[matricule] = membre
        return membres

    def _comptes(self, etab, personnel):
        for matricule, _, prenom, _, _, _, (email, role) in PERSONNEL:
            membre = personnel[matricule]
            self._utilisateur(etab, email, prenom, membre.nom, role)

    def _utilisateur(self, etab, email, prenom, nom, role):
        """Compte de démonstration : créé au premier passage, rattaché à l'établissement à chaque passage."""
        user, cree = User.objects.get_or_create(
            username=email, defaults={'email': email, 'first_name': prenom, 'last_name': nom,
                                      'role': role, 'etablissement': etab},
        )
        if cree:
            user.set_password(MOT_DE_PASSE)
            user.must_change_password = False
        user.etablissement = etab
        user.role = role
        user.save()
        return user

    def _eleves(self, etab, annee, precedente, classes, statuts, nb_eleves):
        """Élèves et leurs deux inscriptions (année précédente, année en cours) : l'évolution des indicateurs et
        les bulletins ont ainsi un historique réel."""
        hasard = random.Random(GRAINE)
        annee_naissance = {'PS': 2022, 'GS': 2021, 'CP1': 2019, 'CP2': 2018, 'CM1': 2017, 'CM2': 2016,
                           '6E': 2015, '5E': 2014}
        classe_precedente = {'PS': 'PS', 'GS': 'PS', 'CP1': 'GS', 'CP2': 'CP1', 'CM1': 'CP2', 'CM2': 'CM1',
                             '6E': 'CM2', '5E': '6E'}
        par_niveau = {classe.niveau: classe for classe in classes.values()}
        courantes, precedentes = [], []
        par_classe = nb_eleves // len(classes)
        for nom_classe, classe in classes.items():
            for rang in range(par_classe):
                genre = hasard.choice('FM')
                prenom = hasard.choice(PRENOMS_F if genre == 'F' else PRENOMS_M)
                nom = hasard.choice(NOMS)
                eleve, _ = Eleve.objects.get_or_create(
                    matricule=f"{etab.code}{annee.date_debut.year % 100}-{len(courantes) + 1:04d}",
                    defaults={
                        'nom': nom, 'prenom': prenom, 'genre': genre,
                        'date_naissance': dt.date(annee_naissance[classe.niveau], hasard.randint(1, 12),
                                                  hasard.randint(1, 28)),
                        'lieu_naissance': hasard.choice(('Ouagadougou', 'Bobo-Dioulasso', 'Koudougou')),
                        'lieu_residence': hasard.choice(('Karpala', 'Saaba', 'Dassasgho', 'Pissi', 'Tanghin')),
                        'telephone_parent': f"+226 7{hasard.randint(0, 9)} {hasard.randint(10, 99)} "
                                            f"{hasard.randint(10, 99)} {hasard.randint(10, 99)}",
                        'nom_pere': f'{hasard.choice(NOMS)} {hasard.choice(PRENOMS_M)}',
                        'nom_mere': f'{hasard.choice(NOMS)} {hasard.choice(PRENOMS_F)}',
                    },
                )
                courantes.append(Inscription.objects.get_or_create(
                    eleve=eleve, annee_scolaire=annee,
                    defaults={'classe': classe, 'statut_eleve': statuts['AFFECTE'],
                              'date_inscription': annee.date_debut},
                )[0])
                precedentes.append(Inscription.objects.get_or_create(
                    eleve=eleve, annee_scolaire=precedente,
                    defaults={'classe': par_niveau[classe_precedente[classe.niveau]], 'statut_eleve': statuts['AFFECTE'],
                              'date_inscription': precedente.date_debut},
                )[0])
        return courantes, precedentes

    def _familles(self, etab, eleves):
        """Un compte parent (deux enfants) et un compte élève : les portails sont visitables."""
        parent = self._utilisateur(etab, 'parent@demo.bf', 'Aminata', 'OUÉDRAOGO', RoleChoices.PARENT)
        parent.eleves_lies.set([eleves[0].eleve, eleves[-1].eleve])
        eleve = self._utilisateur(etab, 'eleve@demo.bf', eleves[0].eleve.prenom, eleves[0].eleve.nom,
                                  RoleChoices.ELEVE)
        eleve.eleves_lies.set([eleves[0].eleve])

    # ── Pédagogie ────────────────────────────────────────────────────────────────────────────────
    def _pedagogie(self, annee, classes, personnel, eleves):
        enseignants = [m for k, m in personnel.items() if k.startswith('ENS')]
        for code_cycle, matieres in MATIERES.items():
            for code, nom, coefficient in matieres:
                matiere, _ = Matiere.objects.get_or_create(
                    code=code, defaults={'nom': nom, 'coefficient': Decimal(coefficient)})
                MatiereCycle.objects.get_or_create(
                    matiere=matiere, cycle=self.cycles[code_cycle],
                    defaults={'coefficient': Decimal(coefficient)},
                )

        devoir, _ = TypeEvaluation.objects.get_or_create(
            code='DEV', defaults={'nom': 'Devoir surveillé', 'coefficient': Decimal('1'), 'ordre': 1})
        composition, _ = TypeEvaluation.objects.get_or_create(
            code='COMP', defaults={'nom': 'Composition', 'coefficient': Decimal('2'), 'ordre': 2})

        fin_t1 = dt.date(annee.date_debut.year, 12, 19)
        if annee.est_courante and fin_t1 < dt.date.today():
            fin_t1 = dt.date.today() + dt.timedelta(days=30)
        trimestre, _ = Trimestre.objects.get_or_create(
            annee_scolaire=annee, numero=1,
            defaults={'nom': '1er trimestre', 'date_debut': annee.date_debut, 'date_fin': fin_t1},
        )
        hasard = random.Random(GRAINE + annee.date_debut.year)
        for nom_classe, classe in classes.items():
            inscriptions = [i for i in eleves if i.classe_id == classe.pk]
            for code, _, coefficient in MATIERES[classe.cycle.code]:
                enseignement, _ = Enseignement.objects.get_or_create(
                    matiere=Matiere.objects.get(code=code), classe=classe, annee_scolaire=annee,
                    defaults={'personnel': enseignants[len(nom_classe) % len(enseignants)],
                              'coefficient': Decimal(coefficient), 'heures_hebdomadaires': Decimal('4')},
                )
                for type_eval, titre in ((devoir, 'Devoir 1'), (composition, 'Composition du 1er trimestre')):
                    evaluation, _ = Evaluation.objects.get_or_create(
                        enseignement=enseignement, type_evaluation=type_eval, trimestre=trimestre, titre=titre,
                        defaults={'date_planifiee': annee.date_debut + dt.timedelta(days=30),
                                  'bareme': Decimal('20'), 'coefficient': type_eval.coefficient,
                                  'statut': Evaluation.StatutChoices.TERMINEE},
                    )
                    for inscription in inscriptions:
                        Note.objects.get_or_create(
                            inscription=inscription, evaluation=evaluation,
                            defaults={'valeur': Decimal(hasard.randint(60, 185)) / 10,
                                      'statut': Note.StatutNoteChoices.VALIDEE},
                        )
            trimestre.derogation_ouverte = True                         # peuplement de l'historique sans persister de dérogation
            CalculateurMoyenne.recalculer_classe(classe, trimestre)     # moyennes, rangs et bulletins prêts
            trimestre.derogation_ouverte = False

    def _paiements(self, annee, eleves, rubriques, statuts):
        for rang, inscription in enumerate(eleves):
            inscription_montant, scolarite, _ = TARIFS[inscription.classe.cycle.code]
            Paiement.objects.get_or_create(
                inscription=inscription, rubrique=rubriques['INSCRIPTION'],
                numero_recu=f"REC-{annee.date_debut.year}-{rang + 1:05d}",
                defaults={'montant': Decimal(inscription_montant), 'date_paiement': annee.date_debut,
                          'mode_paiement': ModePaiement.ESPECES, 'statut_eleve': statuts['AFFECTE']},
            )
            if rang % 3 and scolarite:                              # deux élèves sur trois ont versé une tranche
                Paiement.objects.get_or_create(
                    inscription=inscription, rubrique=rubriques['SCOLARITE'],
                    numero_recu=f"REC-{annee.date_debut.year}-{len(eleves) + rang + 1:05d}",
                    defaults={'montant': Decimal(scolarite) / 3,
                              'date_paiement': annee.date_debut + dt.timedelta(days=15 + rang % 20),
                              'mode_paiement': ModePaiement.MOBILE_MONEY, 'statut_eleve': statuts['AFFECTE']},
                )

    def _signataires(self, annee, personnel):
        types = {
            code: TypeDocument.objects.get_or_create(
                code=code, defaults={'libelle': libelle, 'categorie': categorie})[0]
            for code, libelle, categorie in (
                ('BULLETIN', 'Bulletin de notes', 'PEDAGOGIE'),
                ('RECU_PAIEMENT', 'Reçu de paiement', 'FINANCE'),
                ('CERT_SCOL', 'Certificat de scolarité', 'SCOLARITE'),
            )
        }
        for cycle in self.cycles.values():
            for code, type_doc in types.items():
                signataire, cree = SignataireDocument.objects.get_or_create(
                    cycle=cycle, type_document=type_doc, annee_scolaire=annee,
                    defaults={'titre': 'Le Comptable' if code == 'RECU_PAIEMENT' else 'Le Directeur'},
                )
                if cree:
                    signataire.set_membre_personnel(personnel['CPT-01' if code == 'RECU_PAIEMENT' else 'DIR-01'])
                    signataire.save(update_fields=['membre_personnel_id'])

    def _pointages(self, annee, personnel):
        """Trois semaines de pointage : présences à l'heure, quelques retards et une absence — de quoi lire la
        feuille mensuelle et son PDF signé (5.51.0)."""
        agents = list(MembrePersonnel.objects.filter(etablissement=annee.etablissement, is_active=True))
        if not agents:
            return
        ReglagePointage.pour(annee.etablissement)
        hasard = random.Random(GRAINE + 7)
        jour = dt.date.today()
        jours = []
        while len(jours) < 15:
            if jour.weekday() < 5:                                  # du lundi au vendredi
                jours.append(jour)
            jour -= dt.timedelta(days=1)
        for agent in agents:
            for date_jour in jours:
                if hasard.random() < 0.06:                          # absence isolée
                    PointagePersonnel.objects.get_or_create(
                        personnel=agent, date=date_jour,
                        defaults={'statut': PointagePersonnel.StatutChoices.ABSENT,
                                  'observation': 'Absence non justifiée'})
                    continue
                retard = hasard.random() < 0.15
                arrivee = dt.time(7, 31 + hasard.randint(0, 28)) if retard else dt.time(7, hasard.randint(0, 29))
                depart = dt.time(12, 30) if hasard.random() < 0.5 else dt.time(16, hasard.randint(0, 30))
                PointagePersonnel.objects.get_or_create(
                    personnel=agent, date=date_jour,
                    defaults={
                        'heure_arrivee': arrivee, 'heure_depart': depart,
                        'statut': (PointagePersonnel.StatutChoices.RETARD if retard
                                   else PointagePersonnel.StatutChoices.PRESENT),
                        'observation': 'Retard signalé' if retard else '',
                    })

    def _evaluations(self, annee, personnel):
        """Un entretien annuel par agent, notes variées : la liste, la grille et le PDF ne sont pas vides (5.51.0)."""
        directeur = personnel.get('DIR-01') or personnel.get('CEN-01')
        hasard = random.Random(GRAINE + 11)
        for agent in MembrePersonnel.objects.filter(etablissement=annee.etablissement, is_active=True):
            notes = [hasard.randint(3, 5) for _ in EvaluationAnnuelle.CRITERES]
            EvaluationAnnuelle.objects.get_or_create(
                personnel=agent, annee_scolaire=annee,
                defaults={
                    'date_entretien': annee.date_debut + dt.timedelta(days=45),
                    'evaluateur': directeur,
                    'ponctualite': notes[0], 'competence': notes[1], 'qualite': notes[2],
                    'relations': notes[3], 'initiative': notes[4],
                    'bilan': "Année régulière : les élèves progressent et le cahier de textes est tenu à jour.",
                    'objectifs': "Poursuivre l'accompagnement des élèves en difficulté et participer aux concertations.",
                    'avis': (EvaluationAnnuelle.AvisChoices.FAVORABLE if sum(notes) >= 20
                             else EvaluationAnnuelle.AvisChoices.RESERVE),
                })

    def _bibliotheque(self, annee, eleves):
        """Catalogue de manuels et prêts en cours, dont deux en retard : la page « Prêts et retards » est
        exploitable dès la démonstration (5.50.0)."""
        etab = annee.etablissement
        ouvrages = (('Mathématiques 6e', 'CIAM', 2500), ('Français 6e', 'Hachette', 2500),
                    ('Sciences d’observation 6e', 'NEI', 2000), ('Histoire-Géographie 6e', 'NEI', 2000))
        aujourdhui = dt.date.today()
        for rang, (titre, editeur, prix) in enumerate(ouvrages):
            manuel, cree = ManuelScolaire.objects.get_or_create(
                etablissement=etab, titre=titre,
                defaults={'auteur': '', 'editeur': editeur, 'cycle': 'POST_PRIMAIRE',
                          'annee_edition': aujourdhui.year - 2, 'prix_remplacement': Decimal(prix),
                          'actif': True},
            )
            if not cree:
                continue
            for _ in range(12):
                ExemplaireManuel.objects.create(
                    manuel=manuel, etat=EtatManuel.BON, annee_acquisition=aujourdhui.year - 1, actif=True)
        exemplaires = list(ExemplaireManuel.objects.filter(manuel__etablissement=etab).order_by('code_exemplaire'))
        # Trois prêts sur des élèves du post-primaire : deux échus, un en cours — la relance et la liste des retards
        # ont toujours du contenu, quel que soit l'effectif demandé.
        post = [i for i in eleves if i.classe.cycle.code == 'POST']
        for rang, inscription in enumerate(post[:3]):
            if not exemplaires:
                return
            AttributionManuel.objects.get_or_create(
                exemplaire=exemplaires.pop(0), inscription=inscription,
                defaults={'date_attribution': aujourdhui - dt.timedelta(days=40 + rang),
                          'etat_sortie': EtatManuel.BON,
                          'date_retour_prevue': aujourdhui + dt.timedelta(days=-12 if rang % 2 == 0 else 10)},
            )

    def _compte_rendu(self, etab, identite, annee, nb_eleves):
        self.stdout.write(self.style.SUCCESS(
            f"Établissement {identite.nom_etablissement} ({etab.code}) — année {annee.libelle} prête."))
        self.stdout.write(
            f"{nb_eleves} élèves inscrits, {Note.objects.filter(inscription__annee_scolaire=annee).count()} notes, "
            f"{Paiement.objects.filter(inscription__annee_scolaire=annee).count()} paiements, "
            f"{PointagePersonnel.objects.count()} pointages, {EvaluationAnnuelle.objects.count()} évaluations "
            f"annuelles, {AttributionManuel.objects.count()} prêts d'ouvrages.")
        self.stdout.write("Comptes de démonstration :")
        for _, _, _, fonction, _, _, (email, role) in PERSONNEL:
            self.stdout.write(f"  {email:24} {role:12} {fonction}")
        self.stdout.write(f"  {'parent@demo.bf':24} {'PARENT':12} parent de deux élèves")
        self.stdout.write(f"  {'eleve@demo.bf':24} {'ELEVE':12} élève")
        self.stdout.write(f"Mot de passe : {MOT_DE_PASSE}")
