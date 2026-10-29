"""Commandes SMS définies par l'école (``CommandeSms``) : reconnaissance du mot-clé dans un SMS reçu, rendu de la
réponse avec ses variables, texte de la commande AIDE et validation du formulaire. Les commandes intégrées
(AIDE / NOTE / SOLDE / ABS) gardent la priorité ; leurs mots sont réservés."""
from decimal import Decimal

from django.utils import timezone

from parametres.models import ModeleMessage

from .models import CommandeSms

VARIABLES_ECOLE = (
    ('{etablissement}', "sigle ou nom de l'école"),
    ('{date}', "date du jour"),
    ('{annee}', "année scolaire en cours"),
)
VARIABLES_ELEVE = (
    ('{eleve}', "prénom et nom de l'élève"),
    ('{prenom}', "prénom"),
    ('{nom}', "nom"),
    ('{matricule}', "matricule"),
    ('{classe}', "classe"),
    ('{moyenne}', "dernière moyenne générale (/20)"),
    ('{rang}', "rang de cette moyenne (ex. 3/45)"),
    ('{trimestre}', "trimestre de cette moyenne"),
    ('{absences}', "absences non justifiées de l'année"),
    ('{excusees}', "absences excusées de l'année"),
    ('{total_du}', "total dû (FCFA)"),
    ('{total_paye}', "total payé (FCFA)"),
    ('{reste}', "reste à payer (FCFA)"),
)
COMMANDES_INTEGREES = ('NOTE <matricule> [T1]', 'SOLDE <matricule>', 'ABS <matricule>')


def actives():
    return CommandeSms.objects.filter(actif=True).order_by('mot_cle')


def trouver(message_normalise):
    """(commande, argument) pour un SMS déjà mis en majuscules et espaces réduits ; (None, '') si aucun mot-clé
    défini par l'école ne commence le message. L'argument est le mot qui suit le mot-clé (matricule)."""
    mot, _, reste = message_normalise.partition(' ')
    if not mot:
        return None, ''
    for commande in actives():
        if mot in commande.mots:
            return commande, reste.split(' ')[0] if reste else ''
    return None, ''


def texte_aide():
    """Réponse à AIDE : commandes intégrées puis commandes de l'école, dans la limite d'un SMS."""
    prefixe, retenus = 'Yelen - Commandes: ', []
    for element in [*COMMANDES_INTEGREES, *(c.format_sms for c in actives())]:
        if len(prefixe + ', '.join([*retenus, element])) + 1 > CommandeSms.LONGUEUR_REPONSE:
            while len(prefixe + ', '.join(retenus) + '...') > CommandeSms.LONGUEUR_REPONSE:
                retenus.pop()
            return prefixe + ', '.join(retenus) + '...'
        retenus.append(element)
    return prefixe + ', '.join(retenus) + '.'


def _montant(valeur):
    return f"{int(Decimal(valeur or 0)):,}".replace(',', ' ')


def _sigle(etablissement):
    from parametres.models import IdentiteEtablissement
    identite = IdentiteEtablissement.objects.filter(etablissement=etablissement).first()
    if identite and (identite.sigle or identite.nom_etablissement):
        return identite.sigle or identite.nom_etablissement
    return etablissement.nom if etablissement else ''


def variables_citees(contenu):
    return set(ModeleMessage.VARIABLE.findall(contenu or ''))


def rendre(commande, eleve=None, inscription=None):
    """Réponse de la commande, variables remplacées. Seules les variables citées sont calculées (une commande
    « horaires » ne coûte aucune requête ; une commande « frais » ne calcule que la situation financière)."""
    citees = variables_citees(commande.reponse)
    valeurs = {}
    if 'etablissement' in citees:
        valeurs['etablissement'] = _sigle(commande.etablissement)
    if 'date' in citees:
        valeurs['date'] = timezone.localdate().strftime('%d/%m/%Y')
    if 'annee' in citees:
        from parametres.models import AnneeScolaire
        annee = (inscription.annee_scolaire if inscription
                 else AnneeScolaire.objects.filter(etablissement=commande.etablissement, est_courante=True).first())
        valeurs['annee'] = annee.libelle if annee else ''
    if eleve is not None:
        valeurs.update({'eleve': f"{eleve.prenom} {eleve.nom}", 'prenom': eleve.prenom, 'nom': eleve.nom,
                        'matricule': eleve.matricule, 'classe': inscription.classe.nom if inscription else ''})
        if inscription is not None:
            valeurs.update(_variables_inscription(inscription, citees))
    return ModeleMessage.rendre(commande.reponse, valeurs).strip()


def _variables_inscription(inscription, citees):
    valeurs = {}
    if citees & {'moyenne', 'rang', 'trimestre'}:
        from inscriptions.models import Inscription, StatutInscriptionChoices
        from pedagogie.models import MoyenneGenerale
        mg = MoyenneGenerale.objects.filter(inscription=inscription).select_related('trimestre').order_by('-trimestre__numero').first()
        if mg and mg.moyenne is not None:
            effectif = Inscription.objects.filter(classe=inscription.classe, annee_scolaire=inscription.annee_scolaire) \
                .exclude(statut=StatutInscriptionChoices.ABANDON).count()
            valeurs.update({'moyenne': f"{Decimal(mg.moyenne):.2f}".replace('.', ','),
                            'rang': f"{mg.rang}/{effectif}" if mg.rang else 'N/A', 'trimestre': mg.trimestre.nom})
        else:
            valeurs.update({'moyenne': 'N/A', 'rang': 'N/A', 'trimestre': '-'})
    if citees & {'absences', 'excusees'}:
        from presences.models import Presence
        valeurs['absences'] = Presence.objects.filter(inscription=inscription, statut=Presence.StatutChoices.ABSENT).count()
        valeurs['excusees'] = Presence.objects.filter(inscription=inscription, statut=Presence.StatutChoices.EXCUSE).count()
    if citees & {'total_du', 'total_paye', 'reste'}:
        from finances.views import _calcul_situation_financiere
        situation = _calcul_situation_financiere(inscription)
        valeurs.update({'total_du': _montant(situation['total_du']), 'total_paye': _montant(situation['total_paye']),
                        'reste': _montant(situation['reste_a_payer'])})
    return valeurs


def valider(donnees, etablissement, instance=None):
    """Champs nettoyés et erreurs du formulaire (création ou modification) d'une commande."""
    champs = {
        'mot_cle': CommandeSms.normaliser_mot(donnees.get('mot_cle', '')),
        'alias': ', '.join(m for m in (CommandeSms.normaliser_mot(a) for a in donnees.get('alias', '').split(',')) if m),
        'portee': donnees.get('portee', CommandeSms.Portee.ECOLE),
        'description': ' '.join(donnees.get('description', '').split())[:80],
        'reponse': donnees.get('reponse', '').strip(),
        'actif': donnees.get('actif') == '1',
    }
    erreurs = []
    mots = [champs['mot_cle'], *[m for m in champs['alias'].split(', ') if m]]
    for mot in mots:
        if not CommandeSms.FORMAT_MOT.match(mot):
            erreurs.append(f"« {mot or '(vide)'} » : un mot-clé commence par une lettre et compte 2 à 20 lettres ou chiffres, sans espace.")
        elif mot in CommandeSms.RESERVES:
            erreurs.append(f"« {mot} » est une commande intégrée de YELEN : choisissez un autre mot.")
    if len(set(mots)) != len(mots):
        erreurs.append("Un même mot apparaît deux fois.")
    autres = CommandeSms.objects.filter(etablissement=etablissement)
    if instance is not None:
        autres = autres.exclude(pk=instance.pk)
    for autre in autres:
        deja = sorted(set(mots) & set(autre.mots))
        if deja:
            erreurs.append(f"« {', '.join(deja)} » : déjà utilisé par la commande {autre.mot_cle}.")
    if champs['portee'] not in CommandeSms.Portee.values:
        erreurs.append("Choisissez la portée de la commande.")
    if not champs['reponse']:
        erreurs.append("Rédigez la réponse envoyée au parent.")
    elif len(champs['reponse']) > CommandeSms.LONGUEUR_REPONSE:
        erreurs.append(f"La réponse dépasse {CommandeSms.LONGUEUR_REPONSE} caractères ({len(champs['reponse'])}) : un seul SMS est envoyé.")
    connues = {v.strip('{}') for v, _ in VARIABLES_ECOLE}
    if champs['portee'] == CommandeSms.Portee.ELEVE:
        connues |= {v.strip('{}') for v, _ in VARIABLES_ELEVE}
    inconnues = ModeleMessage.variables_inconnues(champs['reponse'], connues)
    if inconnues:
        erreurs.append("Variable(s) inconnue(s) : " + ', '.join('{' + v + '}' for v in inconnues)
                       + (" — les variables de l'élève demandent la portée « Information sur un élève »."
                          if champs['portee'] != CommandeSms.Portee.ELEVE and
                          set(inconnues) & {v.strip('{}') for v, _ in VARIABLES_ELEVE} else "."))
    return champs, erreurs

