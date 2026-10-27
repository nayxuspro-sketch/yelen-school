"""Vérification des signataires tels que les documents PDF les résolvent réellement.

    python manage.py verifier_signataires

Pour chaque cycle actif et chaque type de document du catalogue, affiche le signataire que
``SignataireDocument.objects.get_signataire`` retient (celui que ``{% signataire_auto %}`` imprime),
le repli utilisé le cas échéant, et signale les anomalies qui rendraient un document muet :
membre du personnel supprimé, fichier de signature scannée absent du disque, aucun signataire actif.
"""
import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from etablissements.models import Etablissement
from parametres.models import AnneeScolaire, Cycle, SignataireDocument, TypeDocument

_TAG = re.compile(r'{%\s*signataire_auto\s+"([A-Z_]+)"')


def _codes_des_gabarits():
    """Codes de type de document référencés par les gabarits PDF de l'application."""
    racine = Path(settings.BASE_DIR)
    codes = set()
    for gabarit in racine.rglob('templates/**/*.html'):
        if 'node_modules' in gabarit.parts or 'staticfiles' in gabarit.parts:
            continue
        codes.update(_TAG.findall(gabarit.read_text(encoding='utf-8', errors='ignore')))
    return codes


class Command(BaseCommand):
    help = "Affiche, par cycle et type de document, le signataire réellement imprimé sur les PDF et les anomalies."

    def handle(self, *args, **options):
        version = (Path(settings.BASE_DIR) / 'VERSION').read_text(encoding='utf-8').strip()
        self.stdout.write(f"YELEN SCHOOL {version} — vérification des signataires")
        anomalies = 0
        types = list(TypeDocument.objects.order_by('categorie', 'code'))
        codes_gabarits = _codes_des_gabarits()
        absents = sorted(c for c in codes_gabarits if not any(t.code == c and t.actif for t in types))
        if absents:
            self.stdout.write(f"Types référencés par les documents mais absents ou inactifs du catalogue "
                              f"(repli sur le signataire du cycle) : {', '.join(absents)}")

        for etab in Etablissement.objects.order_by('nom'):
            annee = AnneeScolaire.objects.get_annee_courante(etablissement=etab)
            self.stdout.write(f"\nÉtablissement : {etab.nom} — année courante : {annee.libelle if annee else 'AUCUNE'}")
            nb_actifs = SignataireDocument.objects.filter(cycle__etablissement=etab, actif=True).count()
            if not nb_actifs:
                anomalies += 1
                self.stdout.write("  ANOMALIE : aucun signataire actif — aucun document ne peut être signé "
                                  "(Paramètres → Signataires → Configurer les Signataires).")
                continue
            for cycle in Cycle.objects.filter(etablissement=etab, actif=True).order_by('ordre'):
                self.stdout.write(f"  Cycle {cycle.nom}")
                for td in types:
                    if not td.actif or (td.cycle_id and td.cycle_id != cycle.pk):
                        continue
                    sig = SignataireDocument.objects.get_signataire(cycle=cycle, type_document=td, annee_scolaire=annee)
                    if sig is None:
                        anomalies += 1
                        self.stdout.write(f"    {td.code:<22} ANOMALIE : aucun signataire exploitable")
                        continue
                    membre = sig.get_membre_personnel()
                    exact = sig.cycle_id == cycle.pk and sig.type_document_id == td.pk
                    repli = '' if exact else f" (repli : {sig.type_document.code} · {sig.cycle.nom})"
                    if membre.signature:
                        if membre.signature.storage.exists(membre.signature.name):
                            signature = 'signature scannée : oui'
                        else:
                            anomalies += 1
                            signature = f'ANOMALIE : fichier de signature absent ({membre.signature.name})'
                    else:
                        signature = 'signature scannée : non (espace vierge)'
                    self.stdout.write(f"    {td.code:<22} {sig.fonction or 'Le Directeur'} — "
                                      f"{membre.nom.upper()} {membre.prenom} · {signature}{repli}")
            supprimes = [s for s in SignataireDocument.objects.filter(cycle__etablissement=etab, actif=True)
                         if s.get_membre_personnel() is None]
            for s in supprimes:
                anomalies += 1
                self.stdout.write(f"  ANOMALIE : {s.type_document.code} · {s.cycle.nom} pointe vers un membre du "
                                  f"personnel supprimé (ignoré par les documents, à reconfigurer)")
        self.stdout.write(f"\n{anomalies} anomalie(s).")
