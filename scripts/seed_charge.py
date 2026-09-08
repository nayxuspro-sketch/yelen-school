"""
scripts/seed_charge.py — Peuplement d'une école réaliste pour test de charge
=============================================================================

Crée (idempotent — relancer ne duplique rien) :
  - 1 établissement (code KDG), 4 cycles, 40 classes
  - 5 années scolaires (dont la courante) avec 3 trimestres chacune
  - 1 500 élèves inscrits chaque année (≈ 7 500 inscriptions)
  - 12 matières, enseignements par classe, 4 évaluations / matière / trimestre
  - ≈ 1 000 000 de notes sur 5 ans
  - 6 paiements par inscription (≈ 45 000)
  - 40 enseignants, 21 comptes utilisateurs (1 admin + 20 testeurs)

Usage :
    DB_ENGINE=sqlite python scripts/seed_charge.py            # jeu complet
    DB_ENGINE=sqlite python scripts/seed_charge.py --annees 1 # plus rapide
    DB_ENGINE=sqlite python scripts/seed_charge.py --eleves 2500 --annees 5
"""
import argparse
import os
import random
import sys
import time
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yelen_school.settings')

import django  # noqa: E402

django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from django.db import connection, transaction  # noqa: E402

from core.signals import disable_audit  # noqa: E402
from etablissements.models import Etablissement  # noqa: E402
from finances.models import Paiement  # noqa: E402
from inscriptions.models import Eleve, Inscription  # noqa: E402
from parametres.models import AnneeScolaire, Classe, Cycle, RubriquePaiement  # noqa: E402
from pedagogie.models import Enseignement, Evaluation, Matiere, Note, Trimestre, TypeEvaluation  # noqa: E402
from personnel.models import MembrePersonnel  # noqa: E402

disable_audit()  # pas d'audit trail pendant le peuplement (sinon x2 lignes)
rnd = random.Random(2026)
User = get_user_model()

NOMS = ['OUEDRAOGO', 'SAWADOGO', 'KABORE', 'ZONGO', 'TRAORE', 'COMPAORE', 'ILBOUDO', 'NIKIEMA', 'SANOU', 'BAMOGO',
        'YAMEOGO', 'KIENTEGA', 'TAPSOBA', 'SIMPORE', 'ZOUNGRANA', 'BONKOUNGOU', 'NANA', 'GUIGMA', 'SORGHO', 'DIALLO']
PRENOMS_M = ['Abdoul', 'Issa', 'Moussa', 'Boukary', 'Salif', 'Yacouba', 'Rasmané', 'Adama', 'Wendpouiré', 'Karim']
PRENOMS_F = ['Aminata', 'Fatimata', 'Salamata', 'Awa', 'Mariam', 'Rasmata', 'Alizèta', 'Bibata', 'Nadège', 'Zalissa']
CYCLES = [('PRES', 'Préscolaire', 1), ('PRIM', 'Primaire', 2), ('POST', 'Post-primaire', 3), ('SEC', 'Secondaire', 4)]
NIVEAUX = {
    'PRES': ['PS', 'MS', 'GS'],
    'PRIM': ['CP1', 'CP2', 'CE1', 'CE2', 'CM1', 'CM2'],
    'POST': ['6ème', '5ème', '4ème', '3ème'],
    'SEC': ['2nde', '1ère', 'Tle'],
}
MATIERES = [('FR', 'Français', 4), ('MATH', 'Mathématiques', 4), ('SVT', 'SVT', 2), ('PC', 'Physique-Chimie', 2),
            ('HG', 'Histoire-Géographie', 2), ('ANG', 'Anglais', 2), ('EPS', 'EPS', 1), ('PHILO', 'Philosophie', 2),
            ('ECM', 'Éducation civique', 1), ('ARTS', 'Arts', 1), ('INFO', 'Informatique', 1), ('LV2', 'Allemand', 2)]
NB_ELEVES = 1500   # surchargé par --eleves
NB_CLASSES = 40    # recalculé : ~40 élèves par classe
EVALS_PAR_TRIM = 4
PWD = 'Yelen2026!'


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def build_etablissement():
    etab, _ = Etablissement.objects.get_or_create(
        code='KDG',
        defaults=dict(nom='Complexe Scolaire YELEN Koudougou', ville='Koudougou', email='contact@yelen.bf',
                      cycles=['PRESCOLAIRE', 'PRIMAIRE', 'POST_PRIMAIRE', 'SECONDAIRE']),
    )
    cycles = {}
    for code, nom, ordre in CYCLES:
        cycles[code], _ = Cycle.objects.get_or_create(etablissement=etab, code=code,
                                                      defaults=dict(nom=nom, ordre=ordre, actif=True))
    classes = list(Classe.objects.filter(etablissement=etab).order_by('nom'))
    if len(classes) < NB_CLASSES:
        classes = []
        # Répartition de base pour 40 classes : 3 PRES, 12 PRIM, 16 POST, 9 SEC,
        # mise à l'échelle pour NB_CLASSES (sections A, B, C, ...)
        base = [('PRES', 1), ('PRIM', 2), ('POST', 4), ('SEC', 3)]
        facteur = NB_CLASSES / 40
        for ccode, par_niveau in base:
            n_sections = max(1, round(par_niveau * facteur))
            for niveau in NIVEAUX[ccode]:
                for k in range(n_sections):
                    if len(classes) >= NB_CLASSES:
                        break
                    nom = f"{niveau} {chr(65 + k)}"
                    c, _ = Classe.objects.get_or_create(
                        etablissement=etab, nom=nom,
                        defaults=dict(cycle=cycles[ccode], niveau=niveau, capacite_max=45, actif=True))
                    classes.append(c)
        # Complément éventuel pour atteindre exactement NB_CLASSES
        k = 0
        while len(classes) < NB_CLASSES:
            niveau = NIVEAUX['POST'][k % 4]
            nom = f"{niveau} {chr(65 + 10 + k // 4)}"
            c, _ = Classe.objects.get_or_create(
                etablissement=etab, nom=nom,
                defaults=dict(cycle=cycles['POST'], niveau=niveau, capacite_max=45, actif=True))
            classes.append(c)
            k += 1
    return etab, cycles, classes[:NB_CLASSES]


def build_annees(etab, nb_annees):
    annees = []
    courante = 2026  # année scolaire 2025-2026 en cours
    for i in range(nb_annees):
        debut = courante - nb_annees + i  # ex. 2021..2025
        libelle = f"{debut}-{debut + 1}"
        a, _ = AnneeScolaire.objects.get_or_create(
            etablissement=etab, libelle=libelle,
            defaults=dict(date_debut=date(debut, 10, 1), date_fin=date(debut + 1, 6, 30),
                          est_courante=(i == nb_annees - 1), cloturee=(i != nb_annees - 1)))
        if i == nb_annees - 1 and not a.est_courante:
            AnneeScolaire.objects.filter(etablissement=etab).update(est_courante=False)
            a.est_courante = True
            a.save(update_fields=['est_courante'])
        trims = []
        bornes = [(date(debut, 10, 1), date(debut, 12, 20)), (date(debut + 1, 1, 6), date(debut + 1, 3, 28)),
                  (date(debut + 1, 4, 7), date(debut + 1, 6, 30))]
        for n, (d1, d2) in enumerate(bornes, start=1):
            t, _ = Trimestre.objects.get_or_create(annee_scolaire=a, numero=n,
                                                   defaults=dict(nom=f"Trimestre {n}", date_debut=d1, date_fin=d2))
            trims.append(t)
        annees.append((a, trims))
    return annees


def build_matieres():
    mats = []
    for code, nom, coef in MATIERES:
        m, _ = Matiere.objects.get_or_create(code=code, defaults=dict(nom=nom, coefficient=Decimal(coef)))
        mats.append(m)
    te, _ = TypeEvaluation.objects.get_or_create(code='DEV', defaults=dict(nom='Devoir', coefficient=Decimal('1.00')))
    return mats, te


def build_personnel(etab, n=40):
    membres = list(MembrePersonnel.objects.filter(etablissement=etab))
    while len(membres) < n:
        i = len(membres)
        genre = 'M' if i % 2 == 0 else 'F'
        m = MembrePersonnel.objects.create(
            etablissement=etab, nom=NOMS[i % len(NOMS)], prenom=(PRENOMS_M if genre == 'M' else PRENOMS_F)[i % 10],
            genre=genre, date_naissance=date(1975 + i % 20, 1 + i % 12, 1 + i % 27), lieu_naissance='Koudougou',
            fonction='Enseignant', date_embauche=date(2010 + i % 12, 10, 1), telephone=f'70{i:06d}')
        membres.append(m)
    return membres


def build_eleves(etab):
    n_exist = Eleve.objects.count()
    if n_exist >= NB_ELEVES:
        return list(Eleve.objects.order_by('matricule')[:NB_ELEVES])
    log(f"Création de {NB_ELEVES - n_exist} élèves…")
    eleves = []
    for i in range(n_exist, NB_ELEVES):
        genre = 'M' if i % 2 == 0 else 'F'
        eleves.append(Eleve(
            matricule=f"KDG-2026-{i + 1:04d}", nom=NOMS[i % len(NOMS)],
            prenom=(PRENOMS_M if genre == 'M' else PRENOMS_F)[(i // 20) % 10], genre=genre,
            date_naissance=date(2005 + i % 15, 1 + i % 12, 1 + i % 28), lieu_naissance='Koudougou',
            telephone_parent=f'76{i:06d}', nom_pere=f'{NOMS[(i + 3) % 20]} Pierre', nom_mere=f'{NOMS[(i + 7) % 20]} Marie'))
    Eleve.objects.bulk_create(eleves, batch_size=500)
    return list(Eleve.objects.order_by('matricule')[:NB_ELEVES])


def build_annee_data(etab, annee, trims, classes, eleves, mats, te, profs):
    """Inscriptions, enseignements, évaluations, notes, paiements d'une année."""
    if Inscription.objects.filter(annee_scolaire=annee).exists():
        log(f"  {annee.libelle} : déjà peuplée, ignorée")
        return
    t0 = time.time()
    par_classe = NB_ELEVES // len(classes)  # 37-38 élèves / classe
    with transaction.atomic():
        inscs = [Inscription(eleve=e, annee_scolaire=annee, classe=classes[min(i // par_classe, len(classes) - 1)],
                             date_inscription=annee.date_debut, statut='AFFECTE')
                 for i, e in enumerate(eleves)]
        Inscription.objects.bulk_create(inscs, batch_size=500)
        inscs = list(Inscription.objects.filter(annee_scolaire=annee).select_related('classe'))

        ens = [Enseignement(matiere=m, classe=c, annee_scolaire=annee, personnel=profs[(ci * 3 + mi) % len(profs)])
               for ci, c in enumerate(classes) for mi, m in enumerate(mats)]
        Enseignement.objects.bulk_create(ens, batch_size=500)
        ens = list(Enseignement.objects.filter(annee_scolaire=annee))

        evals = []
        for e in ens:
            for t in trims:
                for k in range(EVALS_PAR_TRIM):
                    d = t.date_debut + timedelta(days=10 + k * 18)
                    evals.append(Evaluation(enseignement=e, type_evaluation=te, trimestre=t, titre=f"Devoir {k + 1}",
                                            date_planifiee=d, date_effectuee=d, statut='TERMINEE'))
        Evaluation.objects.bulk_create(evals, batch_size=1000)
        evals = list(Evaluation.objects.filter(trimestre__annee_scolaire=annee).select_related('enseignement'))
    log(f"  {annee.libelle} : {len(inscs)} inscriptions, {len(ens)} enseignements, {len(evals)} évaluations")

    # Notes : par classe (évaluations de la classe × inscrits de la classe)
    by_classe = {}
    for ins in inscs:
        by_classe.setdefault(ins.classe_id, []).append(ins)
    ev_by_classe = {}
    for ev in evals:
        ev_by_classe.setdefault(ev.enseignement.classe_id, []).append(ev)
    total = 0
    for cid, ev_list in ev_by_classe.items():
        batch = [Note(inscription=ins, evaluation=ev, valeur=Decimal(f"{rnd.uniform(2, 19.5):.2f}"), statut='VALIDEE')
                 for ev in ev_list for ins in by_classe.get(cid, [])]
        with transaction.atomic():
            Note.objects.bulk_create(batch, batch_size=2000)
        total += len(batch)
    log(f"  {annee.libelle} : {total:,} notes")

    rub, _ = RubriquePaiement.objects.get_or_create(etablissement=etab, code='SCOL',
                                                    defaults=dict(nom='Scolarité', montant=Decimal('75000')))
    pais = []
    for ins in inscs:
        for k in range(6):
            pais.append(Paiement(inscription=ins, rubrique=rub, montant=Decimal('12500'),
                                 date_paiement=annee.date_debut + timedelta(days=30 * k + rnd.randint(0, 20)),
                                 mode_paiement='ESPECES', numero_recu=f"REC-{annee.libelle[:4]}-{ins.eleve_id.hex[:6]}{k}"))
    with transaction.atomic():
        Paiement.objects.bulk_create(pais, batch_size=1000)
    log(f"  {annee.libelle} : {len(pais):,} paiements — {time.time() - t0:.0f} s")


def build_users(etab):
    admin, created = User.objects.get_or_create(
        email='admin@yelen.bf', defaults=dict(username='admin@yelen.bf', first_name='Admin', last_name='YELEN',
                                              role='SUPER_ADMIN', is_staff=True, is_superuser=True, etablissement=etab))
    if created:
        admin.set_password(PWD)
        admin.save()
    roles = ['DIRECTEUR', 'SECRETAIRE', 'COMPTABLE'] + ['ENSEIGNANT'] * 17
    profs = list(MembrePersonnel.objects.filter(etablissement=etab).order_by('matricule'))
    for i in range(20):
        email = f'user{i + 1:02d}@yelen.bf'
        u, created = User.objects.get_or_create(
            email=email, defaults=dict(username=email, first_name=f'Testeur{i + 1}', last_name=NOMS[i],
                                       role=roles[i], etablissement=etab, is_staff=roles[i] != 'ENSEIGNANT'))
        if created:
            u.set_password(PWD)
            u.save()
        # Relier chaque compte enseignant à une fiche personnel (rapprochement par e-mail)
        if roles[i] == 'ENSEIGNANT' and profs:
            prof = profs[i % len(profs)]
            if prof.email != email:
                prof.email = email
                prof.save(update_fields=['email'])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--annees', type=int, default=5)
    ap.add_argument('--eleves', type=int, default=1500, help="Nombre d'élèves par année")
    args = ap.parse_args()
    global NB_ELEVES, NB_CLASSES
    NB_ELEVES = args.eleves
    NB_CLASSES = max(4, round(NB_ELEVES / 40))

    log(f"SGBD : {connection.vendor} — {connection.settings_dict['NAME']}")
    t0 = time.time()
    etab, cycles, classes = build_etablissement()
    annees = build_annees(etab, args.annees)
    mats, te = build_matieres()
    profs = build_personnel(etab)
    eleves = build_eleves(etab)
    build_users(etab)
    log(f"Structure : {len(classes)} classes, {len(annees)} années, {len(mats)} matières, {len(profs)} enseignants, {len(eleves)} élèves")
    for annee, trims in annees:
        build_annee_data(etab, annee, trims, classes, eleves, mats, te, profs)

    if connection.vendor == 'sqlite':
        with connection.cursor() as c:
            c.execute('PRAGMA wal_checkpoint(TRUNCATE)')
            c.execute('ANALYZE')
        size = Path(connection.settings_dict['NAME']).stat().st_size / 1024 / 1024
        log(f"Fichier SQLite : {size:.0f} Mo")
    log(f"Totaux : {Inscription.objects.count():,} inscriptions | {Note.objects.count():,} notes | "
        f"{Paiement.objects.count():,} paiements | {User.objects.count()} utilisateurs")
    log(f"Terminé en {time.time() - t0:.0f} s. Connexion : admin@yelen.bf / {PWD} (idem user01..user20@yelen.bf)")


if __name__ == '__main__':
    main()
