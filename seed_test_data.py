import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yelen_school.settings')
django.setup()

from etablissements.models import Etablissement
from parametres.models import AnneeScolaire, Cycle, TypeDocument
from personnel.models import MembrePersonnel
from datetime import date

def seed():
    # 1. Etablissement
    etab, created = Etablissement.objects.get_or_create(
        code='YSK',
        defaults={
            'nom': 'Yelen School Koudougou',
            'ville': 'Koudougou',
            'email': 'contact@yelen.bf'
        }
    )
    if created: print(f"Etablissement créé: {etab}")

    # 2. Annee Scolaire
    annee, created = AnneeScolaire.objects.get_or_create(
        etablissement=etab,
        libelle='2025-2026',
        defaults={
            'date_debut': date(2025, 10, 1),
            'date_fin': date(2026, 6, 30),
            'est_courante': True
        }
    )
    if created: print(f"Année scolaire créée: {annee}")

    # 3. Cycles
    cycles_data = [
        ('PRES', 'Préscolaire', 1),
        ('PRIM', 'Primaire', 2),
        ('POST', 'Post-primaire', 3),
        ('SEC', 'Secondaire', 4),
    ]
    for code, nom, ordre in cycles_data:
        c, created = Cycle.objects.get_or_create(
            etablissement=etab,
            code=code,
            defaults={'nom': nom, 'ordre': ordre, 'actif': True}
        )
        if created: print(f"Cycle créé: {c}")

    # Créer le personnel avec tous les champs requis
    personnel_data = [
        ('SAWADOGO', 'Issa', 'M', date(1980, 5, 15), 'Koudougou', 'Directeur', date(2015, 9, 1)),
        ('OUEDRAOGO', 'Fatima', 'F', date(1985, 3, 22), 'Ouagadougou', 'Censeur', date(2018, 1, 15)),
        ('TRAORE', 'Moussa', 'M', date(1990, 8, 10), 'Bobo-Dioulasso', 'Surveillant', date(2020, 10, 1)),
    ]
    for nom, prenom, genre, date_naiss, lieu_naiss, fonction, date_embauche in personnel_data:
        # Générer un matricule unique
        existing_count = MembrePersonnel.objects.count() + 1
        matricule = f"PERS-YSK-2026-{existing_count:04d}"
        
        p, created = MembrePersonnel.objects.get_or_create(
            nom=nom,
            prenom=prenom,
            defaults={
                'matricule': matricule,
                'genre': genre,
                'date_naissance': date_naiss,
                'lieu_naissance': lieu_naiss,
                'fonction': fonction,
                'date_embauche': date_embauche,
                'etablissement': etab,
            }
        )
        if created: print(f"Personnel créé: {p}")

if __name__ == '__main__':
    seed()
