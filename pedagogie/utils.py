from decimal import Decimal, ROUND_HALF_UP
from django.db.models import Avg, Sum, Q
from .models import Resultat, MoyenneGenerale, Note, Evaluation, TypeEvaluation

class CalculateurMoyenne:
    """Service pour le calcul automatique des moyennes et des rangs."""

    @staticmethod
    def arrondir(valeur):
        """Arrondi standard à deux décimales."""
        if valeur is None: return None
        return Decimal(valeur).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    @classmethod
    def calculer_resultat_matiere(cls, inscription, enseignement, trimestre):
        """Calcule la moyenne d'un élève dans une matière pour un trimestre."""
        
        # 1. Récupérer toutes les évaluations de cet enseignement pour ce trimestre
        evaluations = Evaluation.objects.filter(
            enseignement=enseignement,
            trimestre=trimestre,
            statut='TERMINEE'
        )
        
        if not evaluations.exists():
            return None

        # 2. Récupérer les notes de l'élève
        notes = Note.objects.filter(
            inscription=inscription,
            evaluation__in=evaluations
        ).select_related('evaluation__type_evaluation')

        if not notes.exists():
            return None

        # 3. Logique de calcul par type d'éval
        # On groupe les notes par type d'évaluation (Interro, Devoir, etc.)
        notes_par_type = {}
        for note in notes:
            t_eval = note.evaluation.type_evaluation
            if t_eval not in notes_par_type:
                notes_par_type[t_eval] = []
            notes_par_type[t_eval].append(note)

        total_ponderation = Decimal('0')
        somme_moyennes_types = Decimal('0')

        for t_eval, list_notes in notes_par_type.items():
            # Conversion en notes sur 20
            notes_sur_20 = [n.note_sur_20 for n in list_notes]
            
            # Application de la règle "meilleures notes" si définie
            if t_eval.nb_meilleures_notes > 0:
                notes_sur_20.sort(reverse=True)
                notes_sur_20 = notes_sur_20[:t_eval.nb_meilleures_notes]
            
            # Moyenne du type
            moyenne_type = sum(notes_sur_20) / len(notes_sur_20)
            
            # Application de la pondération du type (ex: Interro=1, Devoir=2)
            somme_moyennes_types += Decimal(moyenne_type) * t_eval.coefficient
            total_ponderation += t_eval.coefficient

        if total_ponderation == 0:
            return None

        moyenne_finale = somme_moyennes_types / total_ponderation
        
        # 4. Enregistrer le résultat
        resultat, _ = Resultat.objects.update_or_create(
            inscription=inscription,
            enseignement=enseignement,
            trimestre=trimestre,
            defaults={
                'moyenne': cls.arrondir(moyenne_finale),
                'moyenne_sur_20': cls.arrondir(moyenne_finale),
                'nb_notes': len(notes),
                'meilleure_note': max([n.note_sur_20 for n in notes]),
                'pire_note': min([n.note_sur_20 for n in notes]),
                'coefficient_utilise': enseignement.get_coefficient()
            }
        )
        return resultat

    @classmethod
    def calculer_moyenne_generale(cls, inscription, trimestre):
        """Calcule la moyenne générale d'un élève pour un trimestre."""
        
        # 1. Récupérer tous les résultats de matières (hors dispensés)
        resultats = Resultat.objects.filter(
            inscription=inscription,
            trimestre=trimestre,
            dispense=False,
        )

        if not resultats.exists():
            return None

        total_points = Decimal('0')
        total_coefficients = Decimal('0')
        validees = 0

        for res in resultats:
            if res.moyenne is None:
                continue
            coeff = res.coefficient_utilise or Decimal('1.00')
            total_points += res.moyenne * coeff
            total_coefficients += coeff
            if res.moyenne >= 10:
                validees += 1

        if total_coefficients == 0:
            return None

        # Ajout/retrait des points de sanctions confirmées sur ce trimestre
        try:
            from viescolaire.models import SanctionDisciplinaire
            from django.db.models import Sum as _Sum
        except ImportError:
            SanctionDisciplinaire = None
            _Sum = None

        if SanctionDisciplinaire is not None:
            points_sanctions = (
                SanctionDisciplinaire.objects
                .filter(
                    inscription=inscription,
                    trimestre=trimestre,
                    statut=SanctionDisciplinaire.StatutChoices.CONFIRME,
                    is_active=True,
                )
                .aggregate(total=_Sum('points'))['total']
            ) or Decimal('0')
        else:
            points_sanctions = Decimal('0')

        total_points_final = total_points + points_sanctions
        moyenne_gen = total_points_final / total_coefficients

        # 2. Enregistrer la moyenne générale
        mg, _ = MoyenneGenerale.objects.update_or_create(
            inscription=inscription,
            trimestre=trimestre,
            defaults={
                'moyenne': cls.arrondir(moyenne_gen),
                'moyenne_sur_20': cls.arrondir(moyenne_gen),
                'total_points': total_points_final,
                'total_coefficients': total_coefficients,
                'nb_matieres_validees': validees,
                'nb_matieres_total': len(resultats)
            }
        )
        return mg

    @classmethod
    def calculer_rangs(cls, classe, trimestre):
        """Calcule et met à jour les rangs pour une classe entière."""
        
        # 1. Calculer d'abord toutes les moyennes individuelles
        from inscriptions.models import Inscription
        inscriptions = Inscription.objects.filter(classe=classe, statut='ACTIF')
        
        # On s'assure que les enseignants ont leurs résultats calculés
        # Dans un vrai flux, on appellerait ça séparément ou on bouclerait
        
        # 2. Récupérer les moyennes générales triées
        moyennes = MoyenneGenerale.objects.filter(
            inscription__classe=classe,
            trimestre=trimestre
        ).order_by('-moyenne')

        # 3. Attribuer les rangs (gestion des ex-aequo)
        current_rank = 0
        current_moyenne = None
        count = 0
        
        for mg in moyennes:
            count += 1
            if mg.moyenne != current_moyenne:
                current_rank = count
                current_moyenne = mg.moyenne
            
            mg.rang = current_rank
            mg.save()
            
        return count
