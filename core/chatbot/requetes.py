"""Requêtes temps réel multi-tenant et formatage des réponses de l'assistant."""
import re
from collections import defaultdict

from django.db.models import Avg, Count, Max, Min


def _get_annee(etab):
    from parametres.models import AnneeScolaire
    return AnneeScolaire.objects.filter(etablissement=etab, est_courante=True).first() if etab else None


def _inscrits(etab, annee, classe_nom=None):
    """Inscriptions actives de l'année dans l'établissement (filtre facultatif sur le nom de classe)."""
    from inscriptions.models import Inscription, StatutInscriptionChoices
    qs = (Inscription.objects.filter(annee_scolaire=annee, classe__etablissement=etab)
          .exclude(statut=StatutInscriptionChoices.ABANDON))
    return qs.filter(classe__nom__icontains=classe_nom) if classe_nom else qs


# ─────────────────────────────────────────────────────────────────────────────
# Extraction de paramètres depuis le message
# ─────────────────────────────────────────────────────────────────────────────

def _extract_classe(text: str):
    patterns = [
        r'\b(terminale\s+[a-e]?)\b',
        r'\b(premi[eè]re\s+[a-e]?)\b',
        r'\b(seconde\s+[a-e]?)\b',
        r'\b(\d+(?:e|è|ème|er)\s*[a-e]?)\b',
        r'\b(cm[12])\b',
        r'\b(ce[12])\b',
        r'\b(cp)\b',
        r'\b(grande\s+section|moyenne\s+section|petite\s+section)\b',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None


def _extract_trimestre(text: str):
    m = re.search(r'\btrimestre\s*([123])\b', text, re.IGNORECASE)
    if m:
        return int(m.group(1))
    m = re.search(r'\bT([123])\b', text)
    if m:
        return int(m.group(1))
    noms = {'premier': 1, 'deuxième': 2, 'second': 2, 'troisième': 3}
    m = re.search(r'\b(premier|deuxième|second|troisième)\s+trimestre\b', text, re.IGNORECASE)
    if m:
        return noms.get(m.group(1).lower())
    return None


def _extract_seuil(text: str, default: float = 10.0) -> float:
    m = re.search(
        r'(?:sous|inférieure?\s+à|moins\s+de|en\s+dessous\s+de)\s*(\d+(?:[.,]\d+)?)',
        text, re.IGNORECASE
    )
    if m:
        return float(m.group(1).replace(',', '.'))
    return default


def _extract_nom(text: str):
    """Extrait un nom propre après des mots-déclencheurs."""
    m = re.search(
        r'(?:élève|cherche|recherche|trouve|fiche\s+de|situation\s+de|informations?\s+sur)\s+'
        r'([A-ZÀÂÄÉÈÊËÎÏÔÙÛÜ][a-zàâäéèêëîïôùûü]+(?:\s+[A-ZÀÂÄÉÈÊËÎÏÔÙÛÜ][a-zàâäéèêëîïôùûü]+)*)',
        text
    )
    if m:
        return m.group(1).split()[0], ' '.join(m.group(1).split()[1:]) or None
    # Fallback : premiers mots capitalisés
    caps = re.findall(r'\b[A-ZÀÂÄÉÈÊËÎÏÔÙÛÜ][a-zàâäéèêëîïôùûü]{2,}\b', text)
    if caps:
        return caps[0], caps[1] if len(caps) >= 2 else None
    return None, None


# ─────────────────────────────────────────────────────────────────────────────
# Requêtes ORM
# ─────────────────────────────────────────────────────────────────────────────

_SANS_ANNEE = {"erreur": "Aucune année scolaire courante configurée."}


def _req_effectifs(etab, classe_nom=None):
    annee = _get_annee(etab)
    if not annee:
        return dict(_SANS_ANNEE)
    qs = _inscrits(etab, annee, classe_nom)
    par_classe = (
        qs.values('classe__nom', 'classe__cycle__nom')
        .annotate(nb=Count('id'))
        .order_by('classe__cycle__nom', 'classe__nom')
    )
    return {
        "annee": str(annee),
        "total": qs.count(),
        "par_classe": [
            {"classe": r['classe__nom'], "cycle": r['classe__cycle__nom'], "nb": r['nb']}
            for r in par_classe
        ],
    }


def _req_finances(etab, classe_nom=None):
    """Mêmes chiffres que Finances (tarifs + services + créances − bourses, paiements − remboursements)."""
    from finances.views.commun import _situations_financieres_en_lot
    annee = _get_annee(etab)
    if not annee:
        return dict(_SANS_ANNEE)
    inscrits = list(_inscrits(etab, annee, classe_nom).select_related('classe', 'annee_scolaire'))
    situations = _situations_financieres_en_lot(inscrits)
    attendu = sum(s['total_du'] for s in situations.values())
    encaisse = sum(s['total_paye'] for s in situations.values())
    nb_retard = sum(1 for s in situations.values() if s['reste_a_payer'] > 0)
    return {
        "annee": str(annee),
        "nb_inscrits": len(inscrits),
        "encaisse": int(encaisse),
        "attendu": int(attendu),
        "taux": round(float(encaisse) / float(attendu) * 100, 1) if attendu else 0,
        "nb_payes": len(inscrits) - nb_retard,
        "nb_retard": nb_retard,
    }


def _req_absences(etab, classe_nom=None, top_n=10):
    from presences.models import Presence
    annee = _get_annee(etab)
    if not annee:
        return dict(_SANS_ANNEE)
    presences = Presence.objects.filter(inscription__in=_inscrits(etab, annee, classe_nom))
    total = presences.count()
    # ABSENT = non justifié | EXCUSE = justifié | RETARD = retard
    nb_absences = presences.filter(statut='ABSENT').count()
    nb_excuses = presences.filter(statut='EXCUSE').count()
    top = (
        presences.filter(statut='ABSENT')
        .values('inscription__eleve__nom', 'inscription__eleve__prenom', 'inscription__classe__nom')
        .annotate(nb=Count('id'))
        .order_by('-nb')[:top_n]
    )
    return {
        "total_appels": total,
        "absences_nj": nb_absences,
        "absences_justifiees": nb_excuses,
        "taux_assiduite": round((total - nb_absences - nb_excuses) / total * 100, 1) if total else 100,
        "top": [
            {"eleve": f"{r['inscription__eleve__nom']} {r['inscription__eleve__prenom']}",
             "classe": r['inscription__classe__nom'],
             "nb": r['nb']}
            for r in top
        ],
    }


def _dernier_trimestre(qs, trimestre_numero):
    """Restreint les moyennes au trimestre demandé, sinon au dernier trimestre disposant de moyennes."""
    if trimestre_numero:
        return qs.filter(trimestre__numero=trimestre_numero), trimestre_numero
    dernier = qs.order_by('-trimestre__numero').values('trimestre__numero').first()
    if dernier:
        return qs.filter(trimestre__numero=dernier['trimestre__numero']), dernier['trimestre__numero']
    return qs, None


def _req_difficultes(etab, classe_nom=None, seuil=10.0, trimestre_numero=None):
    from pedagogie.models import MoyenneGenerale
    annee = _get_annee(etab)
    if not annee:
        return dict(_SANS_ANNEE)
    # Comparaison sur `moyenne_sur_20` : le seuil demandé est exprimé sur 20, la moyenne stockée suit
    # le barème du cycle (10 au primaire) — comparer les deux rendrait tous les primaires « en difficulté ».
    qs = (MoyenneGenerale.objects.filter(inscription__in=_inscrits(etab, annee, classe_nom),
                                        moyenne_sur_20__lt=seuil)
          .select_related('inscription__eleve', 'inscription__classe'))
    qs, trimestre_numero = _dernier_trimestre(qs, trimestre_numero)
    resultats = list(qs.order_by('moyenne_sur_20')[:30])
    return {
        "seuil": seuil,
        "trimestre": trimestre_numero,
        "nb": len(resultats),
        "eleves": [
            {"eleve": f"{m.inscription.eleve.nom} {m.inscription.eleve.prenom}",
             "classe": m.inscription.classe.nom,
             "moyenne": round(float(m.moyenne_sur_20), 2)}
            for m in resultats
        ],
    }


def _req_moyennes(etab, classe_nom, trimestre_numero=None):
    from pedagogie.models import MoyenneGenerale
    annee = _get_annee(etab)
    if not annee:
        return dict(_SANS_ANNEE)
    inscrits = _inscrits(etab, annee, classe_nom)
    premier = inscrits.select_related('classe').first()
    if premier is None:
        return {"erreur": f"Classe « {classe_nom} » introuvable ou sans inscrits."}
    qs, trimestre_numero = _dernier_trimestre(MoyenneGenerale.objects.filter(inscription__in=inscrits), trimestre_numero)
    # Tout est ramené sur 20 (`moyenne_sur_20`) : le texte répondeur annonce « /20 » et compare à 10.
    stats = qs.aggregate(moy=Avg('moyenne_sur_20'), maxi=Max('moyenne_sur_20'), mini=Min('moyenne_sur_20'))
    top5 = list(qs.select_related('inscription__eleve').order_by('-moyenne_sur_20')[:5])
    faibles = list(qs.select_related('inscription__eleve').filter(moyenne_sur_20__lt=10).order_by('moyenne_sur_20')[:5])
    return {
        "classe": premier.classe.nom,
        "trimestre": trimestre_numero,
        "nb_evalues": qs.count(),
        "moyenne": round(float(stats['moy'] or 0), 2),
        "max": round(float(stats['maxi'] or 0), 2),
        "min": round(float(stats['mini'] or 0), 2),
        "top5": [{"eleve": f"{m.inscription.eleve.nom} {m.inscription.eleve.prenom}",
                  "moy": round(float(m.moyenne_sur_20), 2)} for m in top5],
        "faibles": [{"eleve": f"{m.inscription.eleve.nom} {m.inscription.eleve.prenom}",
                     "moy": round(float(m.moyenne_sur_20), 2)} for m in faibles],
    }


def _req_progression(etab, classe_nom=None, sens="baisse"):
    from pedagogie.models import MoyenneGenerale
    annee = _get_annee(etab)
    if not annee:
        return dict(_SANS_ANNEE)
    inscrits = list(_inscrits(etab, annee, classe_nom).select_related('eleve', 'classe')[:200])
    moyennes = defaultdict(list)
    for ins_id, numero, moyenne in (MoyenneGenerale.objects.filter(inscription__in=inscrits)
                                    .order_by('trimestre__numero')
                                    .values_list('inscription_id', 'trimestre__numero', 'moyenne')):
        moyennes[ins_id].append((numero, float(moyenne)))
    resultats = []
    for ins in inscrits:
        mgs = moyennes.get(ins.pk, [])
        if len(mgs) < 2:
            continue
        (t_avant, avant), (t_apres, apres) = mgs[-2], mgs[-1]
        diff = apres - avant
        if (sens == "baisse" and diff <= -0.5) or (sens == "hausse" and diff >= 0.5):
            resultats.append({
                "eleve": f"{ins.eleve.nom} {ins.eleve.prenom}",
                "classe": ins.classe.nom,
                "t_avant": t_avant,
                "moy_avant": round(avant, 2),
                "t_apres": t_apres,
                "moy_apres": round(apres, 2),
                "diff": round(diff, 2),
            })
    resultats.sort(key=lambda x: x['diff'])
    return {"sens": sens, "nb": len(resultats), "eleves": resultats[:25]}


def _req_eleve(etab, nom=None, prenom=None):
    from finances.views.commun import _calcul_situation_financiere
    from inscriptions.models import Eleve, Inscription
    from pedagogie.models import MoyenneGenerale

    if not nom and not prenom:
        return {"erreur": "Fournissez au moins un nom ou un prénom."}
    qs = Eleve.objects.filter(inscriptions__classe__etablissement=etab).distinct()
    if nom:
        qs = qs.filter(nom__icontains=nom)
    if prenom:
        qs = qs.filter(prenom__icontains=prenom)

    resultats = []
    for eleve in qs.order_by('nom', 'prenom')[:8]:
        ins = (Inscription.objects.filter(eleve=eleve, classe__etablissement=etab)
               .select_related('classe', 'annee_scolaire')
               .order_by('-annee_scolaire__date_debut').first())
        mg = MoyenneGenerale.objects.filter(inscription=ins).select_related('trimestre').order_by('-trimestre__numero').first() if ins else None
        paye = _calcul_situation_financiere(ins)['total_paye'] if ins else 0
        resultats.append({
            "nom": f"{eleve.nom} {eleve.prenom}",
            "matricule": eleve.matricule,
            "classe": ins.classe.nom if ins else None,
            "annee": str(ins.annee_scolaire) if ins else None,
            "statut": ins.get_statut_display() if ins else "Non inscrit",
            "moy": round(float(mg.moyenne), 2) if mg else None,
            "trimestre": mg.trimestre.numero if mg else None,
            "paye": int(paye),
        })
    return {"nb": len(resultats), "eleves": resultats}


# ─────────────────────────────────────────────────────────────────────────────
# Formatage des réponses en français
# ─────────────────────────────────────────────────────────────────────────────

def _fcfa(n: int) -> str:
    return f"{n:,}".replace(",", " ") + " FCFA"


def _fmt_effectifs(d: dict) -> str:
    if "erreur" in d:
        return f"Données indisponibles : {d['erreur']}"
    lignes = [f"Effectifs {d['annee']} — {d['total']} élèves inscrits\n"]
    for r in d["par_classe"]:
        lignes.append(f"  • {r['classe']} ({r['cycle']}) : {r['nb']} élèves")
    if not d["par_classe"]:
        lignes.append("Aucune classe inscrite pour cette année.")
    return "\n".join(lignes)


def _fmt_finances(d: dict) -> str:
    if "erreur" in d:
        return f"Données financières indisponibles : {d['erreur']}"
    lignes = [f"Situation financière — {d['annee']}"]
    if d["attendu"]:
        lignes.append(f"Montant attendu   : {_fcfa(d['attendu'])}")
        lignes.append(f"Montant encaissé  : {_fcfa(d['encaisse'])}")
        lignes.append(f"Taux de recouvrement : {d['taux']} %")
    else:
        lignes.append(f"Montant encaissé : {_fcfa(d['encaisse'])}")
        lignes.append("(Frais de scolarité non encore configurés — montant attendu inconnu)")
    lignes.append(f"Élèves à jour : {d['nb_payes']}/{d['nb_inscrits']}   |   En retard : {d['nb_retard']}")
    return "\n".join(lignes)


def _fmt_absences(d: dict) -> str:
    if "erreur" in d:
        return f"Données d'absences indisponibles : {d['erreur']}"
    lignes = [
        "Résumé des absences",
        f"Taux d'assiduité : {d['taux_assiduite']} %",
        f"Absences non justifiées : {d['absences_nj']}   |   Justifiées (excusées) : {d['absences_justifiees']}",
    ]
    if d["top"]:
        lignes.append("\nÉlèves les plus absents (non justifiés) :")
        for i, r in enumerate(d["top"], 1):
            lignes.append(f"  {i}. {r['eleve']} ({r['classe']}) — {r['nb']} absence(s)")
    elif d["total_appels"] == 0:
        lignes.append("Aucune présence enregistrée dans le système.")
    return "\n".join(lignes)


def _fmt_difficultes(d: dict) -> str:
    if "erreur" in d:
        return f"Données indisponibles : {d['erreur']}"
    trim = f"Trimestre {d['trimestre']}" if d['trimestre'] else "trimestre non précisé"
    lignes = [f"Élèves en difficulté — moyenne < {d['seuil']}/20 ({trim})"]
    lignes.append(f"Nombre : {d['nb']} élève(s)")
    for e in d["eleves"]:
        lignes.append(f"  • {e['eleve']} ({e['classe']}) : {e['moyenne']}/20")
    if not d["eleves"]:
        lignes.append("Aucun élève sous ce seuil.")
    return "\n".join(lignes)


def _fmt_moyennes(d: dict) -> str:
    if "erreur" in d:
        return f"Données indisponibles : {d['erreur']}"
    trim = f"Trimestre {d['trimestre']}" if d['trimestre'] else "—"
    lignes = [
        f"Moyennes — {d['classe']} | {trim}",
        f"Élèves évalués : {d['nb_evalues']}",
        f"Moyenne de la classe : {d['moyenne']}/20   |   Max : {d['max']}/20   |   Min : {d['min']}/20",
    ]
    if d["top5"]:
        lignes.append("\nMeilleurs élèves :")
        for e in d["top5"]:
            lignes.append(f"  • {e['eleve']} : {e['moy']}/20")
    if d["faibles"]:
        lignes.append("\nÉlèves sous 10/20 :")
        for e in d["faibles"]:
            lignes.append(f"  • {e['eleve']} : {e['moy']}/20")
    return "\n".join(lignes)


def _fmt_progression(d: dict) -> str:
    if "erreur" in d:
        return f"Données indisponibles : {d['erreur']}"
    label = "en baisse" if d["sens"] == "baisse" else "en hausse"
    lignes = [f"Élèves {label} entre les deux derniers trimestres — {d['nb']} élève(s)"]
    for e in d["eleves"]:
        signe = "▼" if e["diff"] < 0 else "▲"
        lignes.append(
            f"  {signe} {e['eleve']} ({e['classe']}) : "
            f"{e['moy_avant']}/20 (T{e['t_avant']}) → {e['moy_apres']}/20 (T{e['t_apres']}) "
            f"({e['diff']:+.2f})"
        )
    if not d["eleves"]:
        lignes.append(f"Aucun élève {label} avec un écart ≥ 0,5 point.")
    return "\n".join(lignes)


def _fmt_eleve(d: dict) -> str:
    if "erreur" in d:
        return f"Recherche impossible : {d['erreur']}"
    if d["nb"] == 0:
        return "Aucun élève trouvé avec ce nom ou prénom dans la base de données."
    lignes = [f"{d['nb']} élève(s) trouvé(s) :"]
    for e in d["eleves"]:
        lignes.append(f"\n— {e['nom']}  (matricule : {e['matricule']})")
        if e.get("classe"):
            lignes.append(f"  Classe : {e['classe']} — {e['annee']}")
        lignes.append(f"  Statut : {e['statut']}")
        if e.get("moy") is not None:
            lignes.append(f"  Dernière moyenne (T{e['trimestre']}) : {e['moy']}/20")
        lignes.append(f"  Total payé : {_fcfa(e['paye'])}")
    return "\n".join(lignes)

