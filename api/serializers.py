"""
api/serializers.py — Sérialiseurs DRF pour l'API publique YELEN SCHOOL
"""

from rest_framework import serializers

from inscriptions.models import Eleve, Inscription
from parametres.models import AnneeScolaire, Classe, PeriodeEvaluation
from pedagogie.models import MoyenneGenerale, Resultat
from finances.models import Paiement
from presences.models import Presence
from bulletins.models import Bulletin


class EleveSerializer(serializers.ModelSerializer):
    nom_complet = serializers.SerializerMethodField()

    class Meta:
        model = Eleve
        fields = [
            'id', 'nom', 'prenom', 'nom_complet', 'matricule',
            'date_naissance', 'genre', 'telephone_parent',
        ]

    def get_nom_complet(self, obj):
        return obj.get_nom_complet()


class ClasseSerializer(serializers.ModelSerializer):
    cycle_nom = serializers.CharField(source='cycle.nom', read_only=True)

    class Meta:
        model = Classe
        fields = ['id', 'nom', 'niveau', 'cycle_nom']


class InscriptionSerializer(serializers.ModelSerializer):
    eleve = EleveSerializer(read_only=True)
    classe = ClasseSerializer(read_only=True)
    annee_libelle = serializers.CharField(source='annee_scolaire.libelle', read_only=True)

    class Meta:
        model = Inscription
        fields = [
            'id', 'eleve', 'classe', 'annee_libelle',
            'statut', 'date_inscription',
        ]


class AnneeScolaireSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnneeScolaire
        fields = ['id', 'libelle', 'date_debut', 'date_fin', 'est_courante']


class PeriodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PeriodeEvaluation
        fields = ['id', 'nom', 'type_periode', 'numero', 'date_debut', 'date_fin', 'est_en_cours']


class ResultatSerializer(serializers.ModelSerializer):
    matiere = serializers.CharField(source='enseignement.matiere.nom', read_only=True)
    coefficient = serializers.DecimalField(
        source='coefficient_utilise', max_digits=4, decimal_places=2, read_only=True
    )

    class Meta:
        model = Resultat
        fields = ['id', 'matiere', 'coefficient', 'moyenne', 'rang', 'dispense']


class MoyenneGeneraleSerializer(serializers.ModelSerializer):
    trimestre_nom = serializers.CharField(source='trimestre.nom', read_only=True)
    resultats = ResultatSerializer(many=True, read_only=True, source='inscription.resultats_trimestre')

    class Meta:
        model = MoyenneGenerale
        fields = [
            'id', 'trimestre_nom', 'moyenne', 'rang',
            'total_points', 'total_coefficients',
            'nb_absences', 'nb_retards',
        ]

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        # Ajouter les résultats matière pour ce trimestre
        resultats = Resultat.objects.filter(
            inscription=instance.inscription,
            trimestre=instance.trimestre,
        ).select_related('enseignement__matiere')
        rep['resultats'] = ResultatSerializer(resultats, many=True).data
        return rep


class PaiementSerializer(serializers.ModelSerializer):
    rubrique = serializers.CharField(source='rubrique.nom', read_only=True)

    class Meta:
        model = Paiement
        fields = ['id', 'rubrique', 'montant', 'date_paiement', 'numero_recu', 'statut']


class PresenceSerializer(serializers.ModelSerializer):
    date = serializers.DateField(source='appel.date', read_only=True)
    matiere = serializers.SerializerMethodField()

    class Meta:
        model = Presence
        fields = ['id', 'statut', 'date', 'matiere', 'justifiee']

    def get_matiere(self, obj):
        if obj.appel and obj.appel.matiere:
            return obj.appel.matiere.nom
        return None


class BulletinSerializer(serializers.ModelSerializer):
    trimestre = serializers.CharField(source='trimestre.nom', read_only=True)
    classe = serializers.CharField(source='inscription.classe.nom', read_only=True)
    eleve = serializers.CharField(source='inscription.eleve.get_nom_complet', read_only=True)
    moyenne = serializers.SerializerMethodField()

    class Meta:
        model = Bulletin
        fields = [
            'id', 'eleve', 'classe', 'trimestre',
            'est_publie', 'date_publication',
            'absences_justifiees', 'absences_non_justifiees', 'retards',
            'appreciation_conseil', 'moyenne',
        ]

    def get_moyenne(self, obj):
        mg = MoyenneGenerale.objects.filter(
            inscription=obj.inscription, trimestre=obj.trimestre
        ).first()
        return str(mg.moyenne) if mg else None
