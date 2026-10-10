"""
viescolaire/services.py — Génération automatique d'emploi du temps.

Algorithme : greedy avec random restarts.
- Pour chaque enseignement (trié par nb séances DESC), on cherche des créneaux
  libres en respectant 4 contraintes :
    1. La classe n'est pas déjà occupée à ce créneau
    2. Le prof n'est pas déjà occupé à ce créneau (si affecté)
    3. Le prof n'est pas marqué indisponible à ce créneau
    4. Maximum MAX_SEANCES_PAR_JOUR séances d'un même enseignement par jour
- Si un enseignement ne peut pas être entièrement placé, on réessaie avec un
  nouvel ordre aléatoire (jusqu'à MAX_TENTATIVES).
"""

import json
import random
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

MAX_SEANCES_PAR_JOUR = 2
MAX_TENTATIVES = 40

CRENEAUX_BF = [
    (time(7, 30),  time(8, 20)),
    (time(8, 20),  time(9, 10)),
    (time(9, 10),  time(10, 0)),
    (time(10, 20), time(11, 10)),
    (time(11, 10), time(12, 0)),
    (time(14, 0),  time(14, 50)),
    (time(14, 50), time(15, 40)),
    (time(15, 40), time(16, 30)),
    (time(16, 30), time(17, 20)),
]

JOURS_DEFAUT = [1, 2, 3, 4, 5, 6]


@dataclass
class SeancePrevue:
    enseignement_id: str
    jour: int
    heure_debut: str
    heure_fin: str
    matiere_nom: str
    prof_nom: str

    @property
    def jour_nom(self) -> str:
        """Libellé du jour (« Lundi »…) pour l'aperçu ; le numéro brut si inconnu."""
        from .models import JourSemaine
        try:
            return str(JourSemaine(int(self.jour)).label)
        except ValueError:
            return str(self.jour)


@dataclass
class ResultatGeneration:
    seances: list = field(default_factory=list)
    nb_placees: int = 0
    nb_total: int = 0
    non_placees: list = field(default_factory=list)

    @property
    def complet(self):
        return self.nb_placees >= self.nb_total

    @property
    def taux(self):
        if self.nb_total == 0:
            return 100
        return round(100 * self.nb_placees / self.nb_total)

    def to_json(self):
        return json.dumps([
            {
                'enseignement_id': str(s.enseignement_id),
                'jour': s.jour,
                'heure_debut': s.heure_debut,
                'heure_fin': s.heure_fin,
            }
            for s in self.seances
        ])

    def seances_par_jour(self):
        """Retourne {jour: [SeancePrevue]} trié."""
        grouped = defaultdict(list)
        for s in self.seances:
            grouped[s.jour].append(s)
        return dict(sorted(grouped.items()))


def _build_slots(config):
    """Construit la liste (jour, hd, hf) depuis une ConfigEDT."""
    slots = []
    jours = config.get_jours_actifs()
    duree = timedelta(minutes=config.duree_seance)
    today = date.today()
    for jour in jours:
        t = datetime.combine(today, config.heure_debut_matin)
        end = datetime.combine(today, config.heure_fin_matin)
        while t + duree <= end:
            slots.append((jour, t.time(), (t + duree).time()))
            t += duree
        t = datetime.combine(today, config.heure_debut_aprem)
        end = datetime.combine(today, config.heure_fin_aprem)
        while t + duree <= end:
            slots.append((jour, t.time(), (t + duree).time()))
            t += duree
    return slots


def _build_slots_defaut(jours=None):
    return [(j, hd, hf) for j in (jours or JOURS_DEFAUT) for hd, hf in CRENEAUX_BF]


def _nb_seances(ens, duree_min):
    heures = float(ens.heures_hebdomadaires or ens.matiere.heures_hebdomadaires or 2)
    nb = round(heures / (duree_min / 60))
    return max(1, min(nb, 12))


class GenerateurEDT:
    """Générateur d'emploi du temps pour une classe."""

    def __init__(self, classe, annee, config=None):
        self.classe = classe
        self.annee = annee
        if config:
            self.slots = _build_slots(config)
            self.duree = config.duree_seance
        else:
            self.slots = _build_slots_defaut()
            self.duree = 50

    def generer(self):
        from pedagogie.models import Enseignement
        from .models import DisponibiliteEnseignant

        enseignements = list(
            Enseignement.objects
            .filter(classe=self.classe, annee_scolaire=self.annee, est_actif=True)
            .select_related('matiere', 'personnel')
        )
        if not enseignements:
            return ResultatGeneration()

        profs = [e.personnel for e in enseignements if e.personnel_id]
        indispo = defaultdict(set)
        for d in DisponibiliteEnseignant.objects.filter(
            etablissement=self.classe.etablissement,
            personnel__in=profs,
        ):
            indispo[d.personnel_id].add((d.jour, d.heure_debut))

        reqs = [(e, _nb_seances(e, self.duree)) for e in enseignements]
        nb_total = sum(n for _, n in reqs)

        best = None
        for _ in range(MAX_TENTATIVES):
            res = self._essai(reqs, indispo, nb_total)
            if best is None or res.nb_placees > best.nb_placees:
                best = res
            if best.complet:
                break

        return best or ResultatGeneration(nb_total=nb_total)

    def _essai(self, reqs, indispo, nb_total):
        occ_classe = {}
        occ_prof = defaultdict(set)
        seances_par_jour = defaultdict(int)

        result = []
        non_placees = []
        nb_placees = 0

        reqs_ord = sorted(reqs, key=lambda x: -x[1])
        slots = list(self.slots)
        random.shuffle(slots)
        random.shuffle(reqs_ord)

        for ens, nb in reqs_ord:
            places = 0
            for jour, hd, hf in slots:
                if places >= nb:
                    break
                if not self._peut_placer(ens, jour, hd, occ_classe, occ_prof, seances_par_jour, indispo):
                    continue
                occ_classe[(jour, hd)] = True
                if ens.personnel_id:
                    occ_prof[(jour, hd)].add(ens.personnel_id)
                seances_par_jour[(ens.pk, jour)] += 1
                result.append(SeancePrevue(
                    enseignement_id=ens.pk,
                    jour=jour,
                    heure_debut=hd.strftime('%H:%M'),
                    heure_fin=hf.strftime('%H:%M'),
                    matiere_nom=ens.matiere.nom,
                    prof_nom=ens.personnel.get_nom_complet() if ens.personnel else '—',
                ))
                places += 1

            nb_placees += places
            if places < nb:
                non_placees.append(f"{ens.matiere.nom} ({places}/{nb} séances placées)")

        return ResultatGeneration(
            seances=sorted(result, key=lambda s: (s.jour, s.heure_debut)),
            nb_placees=nb_placees,
            nb_total=nb_total,
            non_placees=non_placees,
        )

    def _peut_placer(self, ens, jour, hd, occ_classe, occ_prof, seances_par_jour, indispo):
        if (jour, hd) in occ_classe:
            return False
        if ens.personnel_id:
            if ens.personnel_id in occ_prof.get((jour, hd), set()):
                return False
            if (jour, hd) in indispo.get(ens.personnel_id, set()):
                return False
        if seances_par_jour[(ens.pk, jour)] >= MAX_SEANCES_PAR_JOUR:
            return False
        return True
