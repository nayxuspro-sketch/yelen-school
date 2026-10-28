"""Comptes parents en masse : les élèves inscrits sans compte parent sont regroupés par téléphone du parent ou du
tuteur ; un compte par famille est créé avec le téléphone pour identifiant et un mot de passe provisoire, remis par
SMS (si activés) et affiché une seule fois pour une remise sur papier."""
import re
import secrets
from collections import OrderedDict

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction

from core.models import RoleChoices
from inscriptions.models import Inscription, StatutInscriptionChoices
from .models import User

DOMAINE_PARENT = 'parent.invalid'   # TLD réservé (RFC 2606) : l'adresse technique n'est jamais routable
_ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789'   # sans 0/O, 1/l/I
LONGUEUR_MOT_DE_PASSE = 12


def telephone_normalise(valeur):
    """Huit derniers chiffres du numéro (format national burkinabè), '' si le numéro est incomplet."""
    chiffres = re.sub(r'\D', '', valeur or '')
    return chiffres[-8:] if len(chiffres) >= 8 else ''


def email_technique(telephone):
    return f"{telephone}@{DOMAINE_PARENT}"


def email_depuis_identifiant(identifiant):
    """Identifiant saisi à la connexion : un numéro de téléphone désigne le compte parent créé en masse ; toute autre
    valeur est une adresse e-mail."""
    identifiant = (identifiant or '').strip().lower()
    if identifiant and '@' not in identifiant and re.fullmatch(r'[\d\s().+-]+', identifiant):
        telephone = telephone_normalise(identifiant)
        if telephone:
            return email_technique(telephone)
    return identifiant


def identifiant_connexion(user):
    """Ce que l'utilisateur tape pour se connecter : son téléphone pour un compte parent créé en masse, sinon son e-mail."""
    email = user.email or ''
    return email.split('@', 1)[0] if email.endswith('@' + DOMAINE_PARENT) else email


def mot_de_passe_provisoire():
    while True:
        candidat = ''.join(secrets.choice(_ALPHABET) for _ in range(LONGUEUR_MOT_DE_PASSE))
        try:
            validate_password(candidat)
        except ValidationError:
            continue
        return candidat


def _responsable(eleve):
    return (eleve.tuteur_nom or eleve.nom_pere or eleve.nom_mere or '').strip()


def familles_sans_compte(etab, annee):
    """Groupes d'élèves de l'année sans compte parent, par téléphone : [{'cle', 'telephone', 'responsable', 'enfants',
    'compte_existant'}] ; et la liste des élèves injoignables (aucun téléphone)."""
    inscriptions = (
        Inscription.objects.filter(annee_scolaire=annee, classe__etablissement=etab)
        .exclude(statut=StatutInscriptionChoices.ABANDON)
        .select_related('eleve', 'classe').prefetch_related('eleve__utilisateurs_lies')
        .order_by('eleve__nom', 'eleve__prenom')
    )
    comptes_par_telephone = {}   # téléphone → compte parent déjà lié à un enfant de la famille
    sans_compte, sans_telephone = [], []
    for ins in inscriptions:
        eleve = ins.eleve
        telephone = telephone_normalise(eleve.telephone_parent) or telephone_normalise(eleve.tuteur_telephone)
        parent = next((u for u in eleve.utilisateurs_lies.all() if u.role == RoleChoices.PARENT and u.is_active), None)
        if parent is not None:
            if telephone:
                comptes_par_telephone.setdefault(telephone, parent)
            continue
        if not telephone:
            sans_telephone.append(ins)
            continue
        sans_compte.append((telephone, ins))
    if not sans_compte:
        return [], sans_telephone
    techniques = {
        identifiant_connexion(u): u
        for u in User.objects.filter(role=RoleChoices.PARENT, email__endswith='@' + DOMAINE_PARENT,
                                     email__in=[email_technique(t) for t, _ in sans_compte])
    }
    groupes = OrderedDict()
    for telephone, ins in sans_compte:
        groupe = groupes.get(telephone)
        if groupe is None:
            groupe = groupes[telephone] = {
                'cle': telephone,
                'telephone': telephone,
                'responsable': _responsable(ins.eleve),
                'enfants': [],
                'compte_existant': comptes_par_telephone.get(telephone) or techniques.get(telephone),
            }
        groupe['enfants'].append(ins)
        if not groupe['responsable']:
            groupe['responsable'] = _responsable(ins.eleve)
    return list(groupes.values()), sans_telephone


def _nom_prenom(responsable, premier_enfant):
    parties = responsable.split()
    if len(parties) >= 2:
        return parties[0], ' '.join(parties[1:])
    if parties:
        return parties[0], ''
    return premier_enfant.eleve.nom, 'Parent'


def creer_comptes(etab, groupes, cles, par):
    """Crée (ou complète) le compte parent des familles dont la clé figure dans ``cles``. Renvoie, par famille, le compte,
    le mot de passe provisoire (None si le compte existait : les enfants y sont simplement rattachés) et les enfants."""
    resultats = []
    for groupe in groupes:
        if groupe['cle'] not in cles:
            continue
        enfants = [ins.eleve for ins in groupe['enfants']]
        with transaction.atomic():
            compte = groupe['compte_existant']
            mot_de_passe = None
            if compte is None:
                nom, prenom = _nom_prenom(groupe['responsable'], groupe['enfants'][0])
                mot_de_passe = mot_de_passe_provisoire()
                email = email_technique(groupe['telephone'])
                compte = User(email=email, username=email, last_name=nom[:150], first_name=prenom[:150],
                              telephone=groupe['telephone'], role=RoleChoices.PARENT, etablissement=etab,
                              must_change_password=True)
                compte.set_password(mot_de_passe)
                compte.save()
            compte.eleves_lies.add(*enfants)
        resultats.append({'compte': compte, 'mot_de_passe': mot_de_passe, 'enfants': enfants,
                          'identifiant': identifiant_connexion(compte)})
    return resultats


def message_sms(sigle, identifiant, mot_de_passe, url):
    """SMS d'accueil (≤ 160 caractères, sans accent pour les modems GSM 7 bits)."""
    texte = (f"YELEN SCHOOL {sigle}: compte parent cree. Identifiant: {identifiant} Mot de passe: {mot_de_passe} "
             f"- {url} (a changer a la 1re connexion)").strip()
    return texte[:160]
