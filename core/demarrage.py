"""Assistant de première configuration : chaque étape de mise en route de l'établissement, son état réel et son
lien direct. Les étapes ne bloquent rien (l'application fonctionne sans), elles indiquent seulement l'ordre
conseillé — la page sert aussi de tableau de bord de rentrée."""
from django.urls import NoReverseMatch, reverse

from inscriptions.models import Eleve
from parametres.models import (
    AnneeScolaire, Classe, Cycle, IdentiteEtablissement, RubriquePaiement, SignataireDocument, TarifScolarite,
)
from personnel.models import MembrePersonnel


def etapes(etablissement, user=None):
    """[{'cle', 'titre', 'detail', 'fait', 'url', 'action'}] — 8 étapes, dans l'ordre de la mise en route."""
    from accounts.models import User
    identite = IdentiteEtablissement.objects.filter(etablissement=etablissement).first()
    nb_annees = AnneeScolaire.objects.filter(etablissement=etablissement).count()
    courante = AnneeScolaire.objects.filter(etablissement=etablissement, est_courante=True).first()
    nb_cycles = Cycle.objects.filter(etablissement=etablissement, actif=True).count()
    nb_classes = Classe.objects.filter(etablissement=etablissement, actif=True).count()
    nb_rubriques = RubriquePaiement.objects.filter(etablissement=etablissement, actif=True).count()
    nb_tarifs = TarifScolarite.objects.filter(etablissement=etablissement, actif=True).count()
    nb_personnel = MembrePersonnel.objects.filter(etablissement=etablissement, is_active=True).count()
    nb_comptes = User.objects.filter(etablissement=etablissement, is_active=True).exclude(role='PARENT').exclude(role='ELEVE').count()
    nb_eleves = Eleve.objects.filter(inscriptions__classe__etablissement=etablissement).distinct().count()
    nb_signataires = SignataireDocument.objects.filter(cycle__etablissement=etablissement, actif=True).count()

    def url(nom, espace='parametres'):
        try:
            return reverse(f'{espace}:{nom}')
        except NoReverseMatch:                 # nom absent : l'étape reste affichée sans lien
            return ''

    identite_complete = bool(identite and identite.nom_etablissement and identite.numero_agrement_mena)
    return [
        {'cle': 'identite', 'titre': "Identité de l'établissement",
         'detail': ("Nom, sigle, N° Agrément et devise renseignés" if identite_complete
                    else "Renseignez le nom, le N° Agrément, la devise et le logo : ils figurent sur tous les PDF"),
         'fait': identite_complete, 'url': url('identite_etablissement'), 'action': "Compléter l'identité"},
        {'cle': 'annee', 'titre': 'Année scolaire en cours',
         'detail': (f"Année courante : {courante.libelle}" if courante else
                    f"{nb_annees} année(s) déclarée(s), aucune n'est marquée « en cours »"),
         'fait': bool(courante), 'url': url('annee_list'), 'action': 'Déclarer l\'année'},
        {'cle': 'cycles', 'titre': 'Cycles et classes',
         'detail': f"{nb_cycles} cycle(s) actif(s), {nb_classes} classe(s) active(s)",
         'fait': nb_cycles > 0 and nb_classes > 0, 'url': url('classe_list'), 'action': 'Créer les classes'},
        {'cle': 'tarifs', 'titre': 'Rubriques et tarifs de scolarité',
         'detail': f"{nb_rubriques} rubrique(s) de paiement, {nb_tarifs} tarif(s) actif(s)",
         'fait': nb_rubriques > 0 and nb_tarifs > 0, 'url': url('tarif_list'), 'action': 'Saisir les tarifs'},
        {'cle': 'personnel', 'titre': 'Fiches du personnel',
         'detail': f"{nb_personnel} membre(s) du personnel actif(s)",
         'fait': nb_personnel > 0, 'url': url('personnel_list', 'personnel'), 'action': 'Ajouter le personnel'},
        {'cle': 'comptes', 'titre': 'Comptes de connexion',
         'detail': f"{nb_comptes} compte(s) de gestion actif(s) (direction, secrétariat, enseignants, comptabilité)",
         'fait': nb_comptes > 1, 'url': url('user_list', 'accounts'), 'action': 'Créer les comptes'},
        {'cle': 'eleves', 'titre': 'Élèves et inscriptions',
         'detail': f"{nb_eleves} élève(s) enregistré(s)",
         'fait': nb_eleves > 0, 'url': reverse('inscriptions:eleve_list'), 'action': 'Inscrire les élèves'},
        {'cle': 'signataires', 'titre': 'Signataires des documents',
         'detail': (f"{nb_signataires} signataire(s) configuré(s) : bulletins, certificats, reçus et attestations"
                    if nb_signataires else
                    'Qui signe les bulletins, certificats, reçus et attestations (nom, fonction, signature scannée)'),
         'fait': nb_signataires > 0, 'url': url('signataire_config'), 'action': 'Configurer les signataires'},
    ]


def avancement(liste):
    faits = sum(1 for e in liste if e['fait'])
    return {'faits': faits, 'total': len(liste), 'pourcentage': round(100 * faits / len(liste)) if liste else 0,
            'termine': faits == len(liste)}
