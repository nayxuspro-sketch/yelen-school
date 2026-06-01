"""
Assistant IA YELEN SCHOOL — Moteur de requêtes par mots-clés
Analyse le langage naturel et interroge la base de données Django en temps réel.
Répond aussi aux questions fonctionnelles grâce à la base de connaissances du guide.
Aucune API externe requise — fonctionne hors ligne et sans abonnement.
"""

import re
import logging
from django.db.models import Avg, Count, Sum, Max, Min

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Base de connaissances — Guide d'utilisation YELEN SCHOOL
# ─────────────────────────────────────────────────────────────────────────────

_GUIDE_KB = [
    {
        "id": "connexion",
        "mots": ["connect", "login", "accéder", "ouvrir session", "mot de passe oublié", "identifiant", "se connecter"],
        "titre": "Connexion à YELEN SCHOOL",
        "réponse": (
            "Connexion à YELEN SCHOOL\n"
            "────────────────────────\n"
            "1. Ouvre ton navigateur et saisis l'adresse fournie par l'administrateur\n"
            "   (ex : http://192.168.1.10:8000 sur réseau local)\n"
            "2. Saisis ton adresse e-mail et ton mot de passe\n"
            "3. Clique sur « Se connecter »\n\n"
            "Mot de passe oublié ?\n"
            "Contacte l'administrateur — il peut le réinitialiser depuis\n"
            "Administration → Utilisateurs → [ton compte] → Changer le mot de passe.\n"
            "La réinitialisation par email n'est pas disponible en mode hors ligne.\n\n"
            "Double authentification (2FA) :\n"
            "Si activée, tu devras saisir un code à 6 chiffres depuis une application\n"
            "d'authentification (Google Authenticator, Authy, etc.) après le mot de passe."
        ),
    },
    {
        "id": "comptes",
        "mots": ["créer compte", "nouvel utilisateur", "utilisateur", "rôle", "directeur", "enseignant", "secrétaire",
                 "comptable", "désactiver compte", "profil utilisateur", "gestion compte"],
        "titre": "Gestion des comptes utilisateurs",
        "réponse": (
            "Gestion des comptes utilisateurs\n"
            "──────────────────────────────────\n"
            "Accès : Administration → Utilisateurs → Nouvel utilisateur\n"
            "(Réservé aux rôles SUPER_ADMIN et DIRECTEUR)\n\n"
            "Rôles disponibles :\n"
            "  • SUPER_ADMIN — toutes les fonctionnalités, tous les établissements\n"
            "  • DIRECTEUR   — toutes les fonctionnalités de son établissement\n"
            "  • PROVISEUR   — pédagogie, présences, bulletins\n"
            "  • CENSEUR     — présences, discipline\n"
            "  • SECRÉTAIRE  — documents, inscriptions\n"
            "  • COMPTABLE   — finances\n"
            "  • ENSEIGNANT  — notes et présences de ses classes\n"
            "  • PARENT      — portail de suivi de ses enfants\n\n"
            "Créer un compte parent :\n"
            "Administration → Utilisateurs → Nouveau compte parent\n"
            "Remplis : Identité, Contact, Mot de passe, puis coche les élèves liés.\n"
            "Le parent recevra bulletins, absences et notifications pour ses enfants."
        ),
    },
    {
        "id": "inscription",
        "mots": ["inscrire", "inscription", "nouvel élève", "enregistrer élève", "créer élève", "matricule",
                 "admission", "dossier élève", "réinscription"],
        "titre": "Inscrire un élève",
        "réponse": (
            "Inscrire un élève\n"
            "──────────────────\n"
            "Étape 1 — Créer le dossier élève (si nouveau) :\n"
            "  Élèves → + Nouvel élève → remplir le formulaire\n"
            "  Le matricule est généré automatiquement (format BF-AAAA-NNNNN)\n\n"
            "Étape 2 — Inscrire pour l'année en cours :\n"
            "  Inscriptions → + Nouvelle inscription\n"
            "  1. Saisir le matricule ou chercher l'élève par nom\n"
            "  2. Sélectionner la classe et l'année scolaire\n"
            "  3. Choisir le statut tarifaire (Régulier, Boursier, etc.)\n"
            "  4. Cliquer sur Enregistrer\n\n"
            "Réinscription :\n"
            "  Pour un élève déjà dans le système, va dans Inscriptions → + Nouvelle inscription\n"
            "  et utilise son matricule existant — l'historique est conservé.\n\n"
            "Erreur « matricule non reconnu » :\n"
            "  L'élève n'a pas encore été créé. Va d'abord dans Élèves → + Nouvel élève."
        ),
    },
    {
        "id": "bulletin",
        "mots": ["bulletin", "générer bulletin", "bulletin pdf", "notes pdf", "imprimer bulletin",
                 "résultats élève", "bulletin trimestriel", "bulletin annuel", "duplicata bulletin",
                 "publier bulletin", "bulletin classe"],
        "titre": "Bulletins trimestriels",
        "réponse": (
            "Bulletins trimestriels PDF\n"
            "────────────────────────────\n"
            "Bulletin individuel :\n"
            "  Pédagogie → Résultats → [classe] → [élève] → Bulletin PDF\n\n"
            "Bulletin de toute une classe (batch) :\n"
            "  Pédagogie → Résultats → [classe] → Bulletins PDF (batch)\n"
            "  → Génère un seul PDF avec tous les bulletins de la classe\n\n"
            "Duplicata (copie officielle) :\n"
            "  Dans le tableau de classe, clique sur l'icône double-page (couleur or)\n"
            "  Le duplicata porte un filigrane « DUPLICATA » et un bandeau doré\n\n"
            "Prérequis :\n"
            "  • Les notes de toutes les matières doivent être saisies\n"
            "  • Un signataire de type BULLETIN doit être configuré :\n"
            "    Paramètres → Signataires des documents → Nouveau signataire\n\n"
            "Bulletin annuel :\n"
            "  Pédagogie → Résultats → [classe] → Bulletin annuel\n"
            "  Contient la moyenne annuelle, le rang et la décision de passage.\n\n"
            "Publication aux parents :\n"
            "  Cliquer « Publier » génère un lien SMS valable 15 jours pour\n"
            "  la signature électronique par le parent."
        ),
    },
    {
        "id": "notes",
        "mots": ["saisir note", "entrer note", "saisie des notes", "note", "évaluation", "devoir",
                 "composition", "coeff", "coefficients", "grille de notes", "modifier note"],
        "titre": "Saisie des notes",
        "réponse": (
            "Saisie des notes\n"
            "──────────────────\n"
            "Accès :\n"
            "  Pédagogie → Saisie des notes → [classe] → [matière] → [type d'évaluation]\n\n"
            "Étapes :\n"
            "  1. Sélectionne la classe, la matière et le trimestre\n"
            "  2. Saisis les notes dans la grille (0 à 20 obligatoire)\n"
            "  3. Clique sur Enregistrer\n\n"
            "Moyennes :\n"
            "  Les moyennes par discipline et la moyenne générale sont calculées\n"
            "  automatiquement après chaque saisie.\n\n"
            "Modifier une note :\n"
            "  Seul l'enseignant concerné, le Directeur ou le Proviseur peut\n"
            "  modifier une note déjà saisie. Va dans Pédagogie → Saisie des notes\n"
            "  et retrouve l'évaluation concernée.\n\n"
            "Cahier de textes numérique :\n"
            "  Pédagogie → Cahier de textes → saisir le contenu du cours et les devoirs\n"
            "  Le directeur dispose d'une vue consolidée de l'avancement des programmes."
        ),
    },
    {
        "id": "presences",
        "mots": ["appel", "faire appel", "présence", "présent", "absent", "retard", "pointage",
                 "qr code présence", "scanner qr", "séance", "clôturer appel"],
        "titre": "Faire l'appel / Enregistrer les présences",
        "réponse": (
            "Faire l'appel\n"
            "──────────────\n"
            "Accès : Présences → Faire l'appel → sélectionner la séance\n\n"
            "Pour chaque élève, 3 options cliquables : Présent · Absent · En retard\n"
            "3 compteurs en temps réel (Présents / Absents / En retard)\n\n"
            "Boutons disponibles :\n"
            "  • « Tout présent » — coche tous les élèves en un clic\n"
            "  • « Scanner QR »  — active le pointage par QR code\n"
            "  • « Brouillon »   — sauvegarde sans clôturer (modifiable)\n"
            "  • « Clôturer »    — archive définitivement (irréversible)\n\n"
            "Absence en dehors d'un appel :\n"
            "  Présences → Enregistrer une absence → saisir matricule, dates, durée\n\n"
            "Pointage QR Code :\n"
            "  Chaque élève a un QR code unique. Scanner = présence enregistrée\n"
            "  automatiquement. Disponible depuis Présences → Pointage QR."
        ),
    },
    {
        "id": "absences",
        "mots": ["justification", "justifier absence", "excuser absence", "motif absence",
                 "bilan présences", "assiduité", "absences non justifiées"],
        "titre": "Justifications d'absences",
        "réponse": (
            "Justifications d'absences\n"
            "────────────────────────────\n"
            "Accès : Présences → Justifications\n"
            "(Réservé : AVS, Censeur, Directeur, Proviseur)\n\n"
            "Flux :\n"
            "  1. Parent apporte un document justificatif\n"
            "  2. AVS crée la justification (motif + document + période)\n"
            "  3. Censeur ou Directeur accepte ou refuse\n"
            "  4. Si acceptée → les absences passent du statut Absent à Excusé\n\n"
            "Bilan des présences par élève :\n"
            "  Présences → Bilan → [nom de l'élève]\n"
            "  Affiche le cumul des absences NJ, excusées, retards et l'assiduité globale."
        ),
    },
    {
        "id": "paiement",
        "mots": ["paiement", "encaisser", "frais", "scolarité", "frais de scolarité", "régler",
                 "enregistrer paiement", "reçu paiement", "rubrique", "mode paiement", "espèces"],
        "titre": "Enregistrer un paiement",
        "réponse": (
            "Enregistrer un paiement\n"
            "─────────────────────────\n"
            "Accès : Finances → + Nouveau paiement\n"
            "Ou depuis le profil élève : cliquer l'icône $\n\n"
            "Étapes :\n"
            "  1. Cherche l'élève par nom, prénom ou classe dans la barre de recherche\n"
            "  2. La carte élève s'affiche (classe, matricule, situation financière)\n"
            "  3. Les rubriques apparaissent sous forme de cartes :\n"
            "     - Soldée : grisée, non sélectionnable\n"
            "     - En attente : cliquable — affiche le reste à payer\n"
            "  4. Clique sur une carte pour la sélectionner → modifie le montant si besoin\n"
            "  5. Bouton ⚡ « Tout régler » — sélectionne toutes les rubriques en attente\n"
            "  6. Clique Enregistrer le paiement\n\n"
            "Référence obligatoire :\n"
            "  Pour Mobile Money, Chèque ou Virement, la référence de transaction est requise.\n\n"
            "Imprimer un reçu :\n"
            "  Finances → Historique des versements → [élève] → Imprimer reçu PDF"
        ),
    },
    {
        "id": "relances",
        "mots": ["relance", "relances de", "générer relance", "faire relance", "lettre relance",
                 "redevable", "rappel paiement", "élèves redevables", "coupon relance",
                 "liste impayés", "impayé"],
        "titre": "Relances de paiement PDF",
        "réponse": (
            "Relances de paiement PDF\n"
            "─────────────────────────\n"
            "Accès : Finances → Relances\n\n"
            "Étapes :\n"
            "  1. Sélectionne l'année scolaire, la classe (ou toutes), la rubrique\n"
            "  2. Saisis la date limite de paiement\n"
            "  3. Le nombre d'élèves redevables s'affiche automatiquement\n"
            "  4. Clique « Générer les relances PDF »\n\n"
            "Format : coupons A5 — 3 relances par page, trait de découpe entre chaque\n\n"
            "Prérequis :\n"
            "  Un signataire de type RELANCE doit être configuré :\n"
            "  Paramètres → Signataires des documents → Nouveau signataire → catégorie RELANCE\n\n"
            "Envoyer des SMS de relance :\n"
            "  Sur la même page (Finances → Relances), section « SMS » :\n"
            "  Sélectionne année + classe + rubrique → Envoyer SMS\n"
            "  (Module SMS doit être configuré — voir Paramètres → Configuration SMS)"
        ),
    },
    {
        "id": "mobile_money",
        "mots": ["mobile money", "orange money", "paiement à distance", "sms paiement",
                 "confirmer paiement", "demande paiement", "144", "orange"],
        "titre": "Paiements Mobile Money (Orange Money)",
        "réponse": (
            "Paiements Mobile Money — Orange Money\n"
            "──────────────────────────────────────\n"
            "Accès : Finances → Mobile Money\n\n"
            "Flux complet :\n"
            "  1. Depuis la fiche financière de l'élève, clique « Mobile Money »\n"
            "  2. Saisir la rubrique (optionnel), le montant et le numéro Orange du parent\n"
            "  3. « Créer la demande & envoyer SMS » → référence MM-AAAA-NNNNN générée\n"
            "  4. Le parent reçoit le SMS et compose *144# pour payer\n"
            "  5. Le parent communique sa référence Orange Money à l'école\n"
            "  6. Le comptable va dans Finances → Mobile Money, localise la demande\n"
            "     (statut « En attente »), clique ✓ et saisit la référence Orange\n"
            "  7. Le système crée automatiquement le paiement et génère un reçu PDF\n\n"
            "Prérequis : Module SMS configuré (Paramètres → Configuration SMS)\n"
            "Aucun abonnement ni API payante — repose sur le service USSD *144# gratuit."
        ),
    },
    {
        "id": "bourses",
        "mots": ["bourse", "aide financière", "aide scolaire", "réduction frais", "type bourse",
                 "attribuer bourse", "boursier", "subvention", "exonéré"],
        "titre": "Bourses et aides financières",
        "réponse": (
            "Bourses et aides financières\n"
            "──────────────────────────────\n"
            "Accès : Finances → Bourses\n\n"
            "Étape 1 — Créer un type de bourse (une seule fois) :\n"
            "  Finances → Types de bourses → + Nouveau type\n"
            "  Remplir : Nom, Code, Source (État / ONG / Établissement / Autre),\n"
            "  Type de réduction (% ou FCFA fixe), Valeur, Rubrique ciblée\n\n"
            "Étape 2 — Attribuer la bourse à un élève :\n"
            "  Finances → Bourses → + Attribuer une bourse\n"
            "  Sélectionner : Élève, Type de bourse, Année scolaire, Montant,\n"
            "  Date d'attribution, Référence (optionnel)\n\n"
            "Effet : La bourse réduit automatiquement le montant dû sur la rubrique ciblée.\n\n"
            "Exonérations totales :\n"
            "  Finances → Élèves exonérés → + Ajouter une exonération\n"
            "  Pour exempter un élève d'une rubrique spécifique (montant = 0)."
        ),
    },
    {
        "id": "documents",
        "mots": ["certificat", "attestation", "relevé de notes", "document administratif", "cursus",
                 "autorisation absence", "carte scolaire", "liste alphabétique", "liste classe",
                 "convocation", "circulaire", "non-redevabilité", "archivage"],
        "titre": "Documents administratifs",
        "réponse": (
            "Documents administratifs\n"
            "──────────────────────────\n"
            "Accès : Menu → Documents\n\n"
            "Documents disponibles :\n"
            "  • Certificat de scolarité\n"
            "    Documents → Certificat → saisir matricule → Générer\n"
            "  • Attestation de fréquentation\n"
            "    Documents → Attestation de fréquentation\n"
            "  • Relevé de notes / Cursus scolaire\n"
            "    Documents → Cursus scolaire → saisir matricule\n"
            "  • Autorisation d'absence\n"
            "    Documents → Autorisation d'absence\n"
            "  • Liste alphabétique d'une classe (PDF)\n"
            "    Documents → Listes de classe → sélectionner classe\n"
            "  • Liste du personnel (PDF)\n"
            "    Documents → Liste du personnel\n"
            "  • Convocations (parents, élèves, personnel)\n"
            "    Documents → Convocations → + Nouvelle convocation\n"
            "  • Circulaires\n"
            "    Documents → Circulaires → + Nouvelle circulaire\n"
            "  • Attestation de non-redevabilité\n"
            "    Documents → Attestation de non-redevabilité\n\n"
            "Prérequis : Un signataire doit être configuré pour chaque type de document\n"
            "  Paramètres → Signataires des documents → Nouveau signataire"
        ),
    },
    {
        "id": "examens",
        "mots": ["examen", "session examen", "bac", "bepc", "cep", "candidat", "centre examen",
                 "salle examen", "résultats examen", "examen officiel"],
        "titre": "Examens officiels",
        "réponse": (
            "Examens officiels (BAC, BEPC, CEP)\n"
            "────────────────────────────────────\n"
            "Accès : Menu → Examens\n"
            "(Réservé : Directeur, Proviseur, Secrétaire)\n\n"
            "Étapes :\n"
            "  1. Créer une session d'examen\n"
            "     Examens → + Nouvelle session → Type (BAC/BEPC/CEP), Année, Dates\n"
            "  2. Configurer les centres et salles\n"
            "     Examens → Centres → [session] → + Ajouter centre\n"
            "  3. Inscrire les élèves aux examens\n"
            "     Examens → Candidats → + Inscrire un candidat\n"
            "  4. Saisir les résultats\n"
            "     Examens → Résultats → [session] → saisir les notes\n"
            "  5. Générer la liste des candidats par centre\n"
            "     Examens → Liste des candidats → filtrer par centre"
        ),
    },
    {
        "id": "discipline",
        "mots": ["sanction", "discipline", "blâme", "avertissement", "conseil discipline",
                 "points discipline", "fiche suivi", "vie scolaire", "activité parascolaire"],
        "titre": "Discipline et vie scolaire",
        "réponse": (
            "Discipline et vie scolaire\n"
            "────────────────────────────\n"
            "Accès : Vie scolaire\n\n"
            "Enregistrer une sanction :\n"
            "  Vie scolaire → Sanctions → + Nouvelle sanction\n"
            "  Remplir : Élève, Type (Avertissement/Blâme/Exclusion…), Date, Motif\n\n"
            "Système de points :\n"
            "  Chaque élève part d'un capital de points (configurable).\n"
            "  Les sanctions déduisent des points. Si le capital tombe à 0 → alerte.\n"
            "  Vie scolaire → Capital points → [élève]\n\n"
            "Fiche de suivi d'un élève :\n"
            "  Vie scolaire → Suivi individuel → [élève]\n"
            "  Historique complet : absences, sanctions, activités, notes\n\n"
            "Activités parascolaires :\n"
            "  Vie scolaire → Activités → créer une activité et inscrire les participants"
        ),
    },
    {
        "id": "personnel",
        "mots": ["personnel", "enseignant", "professeur", "staff", "contrat", "salaire",
                 "congé personnel", "fiche personnel", "liste personnel"],
        "titre": "Gestion du personnel",
        "réponse": (
            "Gestion du personnel\n"
            "──────────────────────\n"
            "Accès : Menu → Personnel\n\n"
            "Créer un dossier personnel :\n"
            "  Personnel → + Nouveau membre\n"
            "  Remplir : Identité, Fonction, Diplômes, Cycles enseignés\n"
            "  Le matricule PERS-AAAA-NNNNN est généré automatiquement.\n\n"
            "Vacations (enseignants vacataires) :\n"
            "  Personnel → Vacations → + Nouveau contrat\n"
            "  Saisir les heures effectuées, générer le bulletin de vacation PDF\n\n"
            "Salaires :\n"
            "  Personnel → Salaires → saisir les éléments de paie du mois\n\n"
            "Congés :\n"
            "  Personnel → Congés → + Nouvelle demande de congé\n\n"
            "Liste du personnel (PDF) :\n"
            "  Documents → Liste du personnel → sélectionner le type et générer"
        ),
    },
    {
        "id": "sms",
        "mots": ["sms", "envoyer sms", "notification sms", "configuration sms", "sms gateway",
                 "numéro téléphone", "envoi message", "semaphore", "twilio"],
        "titre": "Configuration SMS et notifications",
        "réponse": (
            "Configuration SMS\n"
            "──────────────────\n"
            "Accès : Paramètres → Configuration SMS\n"
            "(Réservé : Super Admin, Directeur)\n\n"
            "Paramètres à renseigner :\n"
            "  • Fournisseur (Semaphore, Twilio, ou autre)\n"
            "  • Clé API du fournisseur\n"
            "  • Nom de l'expéditeur (affiché sur le téléphone du destinataire)\n\n"
            "Tester la configuration :\n"
            "  Saisir un numéro de test et cliquer « Envoyer un SMS test »\n\n"
            "Notifications automatiques configurées :\n"
            "  • Absence d'un élève → SMS au parent\n"
            "  • Publication d'un bulletin → SMS avec lien de signature\n"
            "  • Relance de paiement → SMS aux parents redevables\n"
            "  • Paiement Mobile Money → SMS de confirmation"
        ),
    },
    {
        "id": "portail_parent",
        "mots": ["portail parent", "espace parent", "application parent", "pwa parent",
                 "accès parent", "parent voir bulletin", "parent absences"],
        "titre": "Portail parent (PWA)",
        "réponse": (
            "Portail parent PWA\n"
            "────────────────────\n"
            "Le portail parent est une application web mobile-first accessible depuis\n"
            "le navigateur du parent sans téléchargement d'application.\n\n"
            "Accès pour le parent :\n"
            "  1. L'administrateur crée un compte parent :\n"
            "     Administration → Utilisateurs → Nouveau compte parent\n"
            "  2. Le parent reçoit ses identifiants (email + mot de passe)\n"
            "  3. Il ouvre le navigateur et se connecte à l'URL de l'école\n"
            "  4. Il accède à son espace parent (interface simplifiée sans sidebar admin)\n\n"
            "Fonctionnalités disponibles pour le parent :\n"
            "  • Consulter les notes et moyennes de ses enfants\n"
            "  • Voir les bulletins trimestriels\n"
            "  • Suivre les absences et présences\n"
            "  • Recevoir les notifications (absences, bulletins, relances)\n"
            "  • Signer électroniquement les bulletins\n"
            "  • Consulter la situation financière (frais payés / restants)\n\n"
            "Mode hors ligne :\n"
            "  Le Service Worker met en cache le portail — le parent voit les\n"
            "  dernières données même sans connexion internet."
        ),
    },
    {
        "id": "signataires",
        "mots": ["signataire", "signer document", "configurer signataire", "proviseur signature",
                 "qui signe", "paramètres signataire"],
        "titre": "Configurer les signataires des documents",
        "réponse": (
            "Signataires des documents\n"
            "──────────────────────────\n"
            "Accès : Paramètres → Signataires des documents → Nouveau signataire\n\n"
            "Pour chaque type de document, configure qui signe :\n"
            "  • BULLETIN       — signataire des bulletins trimestriels\n"
            "  • RELANCE        — signataire des lettres de relance paiement\n"
            "  • CERTIFICAT     — signataire des certificats de scolarité\n"
            "  • ATTESTATION    — signataire des attestations\n"
            "  • CONVOCATION    — signataire des convocations\n\n"
            "Paramètres à renseigner :\n"
            "  1. Année scolaire + Cycle (le signataire est spécifique à un cycle)\n"
            "  2. Type de document\n"
            "  3. Fonction du signataire (ex : Proviseur, Directeur…)\n"
            "  4. Membre du personnel associé\n"
            "  5. Titre honorifique (optionnel)\n\n"
            "Si aucun signataire cycle-spécifique n'existe, le système utilise\n"
            "le signataire générique de l'année."
        ),
    },
    {
        "id": "annee_scolaire",
        "mots": ["année scolaire", "changer année", "nouvelle année", "ouvrir année",
                 "clôturer année", "paramètres année", "trimestre", "période"],
        "titre": "Gestion de l'année scolaire",
        "réponse": (
            "Gestion de l'année scolaire\n"
            "──────────────────────────────\n"
            "Accès : Paramètres → Années scolaires\n\n"
            "Créer une nouvelle année :\n"
            "  1. Paramètres → Années scolaires → + Nouvelle année\n"
            "  2. Saisir le libellé (ex : 2026-2027) et les dates de début/fin\n"
            "  3. Cocher « Année courante » pour l'activer\n\n"
            "Trimestres :\n"
            "  Paramètres → Trimestres → créer les 3 périodes de l'année\n"
            "  (T1, T2, T3 avec dates de début et fin)\n\n"
            "Classes et cycles :\n"
            "  Paramètres → Classes → gérer les niveaux et leur rattachement au cycle\n"
            "  Cycles disponibles : Préscolaire · Primaire · Post-primaire · Secondaire\n\n"
            "Rubriques de paiement :\n"
            "  Finances → Rubriques → + Nouvelle rubrique\n"
            "  Puis Finances → Tarifs → affecter un montant par classe"
        ),
    },
    {
        "id": "statistiques",
        "mots": ["statistique", "rapport", "export", "csv", "tableau de bord", "bilan",
                 "encaissement", "rapport paiement", "rapport présence", "rapport financier"],
        "titre": "Statistiques et rapports",
        "réponse": (
            "Statistiques et rapports\n"
            "──────────────────────────\n"
            "Statistiques élèves :\n"
            "  Menu → Statistiques → Élèves\n"
            "  Effectifs par classe, répartition par sexe, taux de redoublement\n\n"
            "Bilan des encaissements :\n"
            "  Finances → Bilan des encaissements\n"
            "  Détail par rubrique, par classe, comparatif attendu/encaissé\n\n"
            "Rapport des paiements :\n"
            "  Finances → Rapports → filtrer par période, classe ou rubrique\n\n"
            "Rapport des présences :\n"
            "  Présences → Bilan → vue globale par classe ou individuelle\n\n"
            "Exports CSV :\n"
            "  La plupart des listes proposent un bouton « Exporter CSV »\n"
            "  (liste des élèves, utilisateurs, paiements…)\n\n"
            "Emploi du temps :\n"
            "  Menu → Emploi du temps → affichage hebdomadaire par classe"
        ),
    },
    {
        "id": "faq",
        "mots": ["aide", "problème", "erreur", "que faire", "comment", "faq", "question",
                 "lent", "lenteur", "sauvegarde", "backup", "annuler paiement", "transférer élève"],
        "titre": "Questions fréquentes",
        "réponse": (
            "Questions fréquentes\n"
            "──────────────────────\n"
            "❓ Mot de passe oublié ?\n"
            "  → Contacter l'administrateur (Administration → Utilisateurs → [compte] → Réinitialiser)\n\n"
            "❓ Élève introuvable à l'inscription ?\n"
            "  → Il faut d'abord créer son dossier : Élèves → + Nouvel élève\n\n"
            "❓ Note incorrecte saisie ?\n"
            "  → Pédagogie → Saisie des notes → retrouver l'évaluation et modifier\n\n"
            "❓ Certificat de scolarité pour un parent ?\n"
            "  → Documents → Certificat de scolarité → saisir matricule → Générer\n\n"
            "❓ Peut-on annuler un paiement ?\n"
            "  → Non directement. Contacter le Directeur ou Comptable pour correction tracée.\n\n"
            "❓ Application lente ?\n"
            "  1. Vérifier la connexion au réseau local de l'école\n"
            "  2. Fermer les autres onglets du navigateur\n"
            "  3. Redémarrer le navigateur\n"
            "  4. Si ça persiste, contacter l'administrateur technique (redémarrage serveur)\n\n"
            "❓ Comment sauvegarder les données ?\n"
            "  → Sauvegardes automatiques gérées par l'administrateur technique.\n"
            "  Contacter le prestataire technique pour configurer les sauvegardes régulières."
        ),
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# Helpers — accès aux modèles Django
# ─────────────────────────────────────────────────────────────────────────────

def _get_etab():
    from etablissements.models import Etablissement
    return Etablissement.objects.first()


def _get_annee():
    from parametres.models import AnneeScolaire
    etab = _get_etab()
    if etab:
        return AnneeScolaire.objects.filter(etablissement=etab, est_courante=True).first()
    return AnneeScolaire.objects.filter(est_courante=True).first()


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

def _req_effectifs(classe_nom=None):
    from inscriptions.models import Inscription
    annee = _get_annee()
    if not annee:
        return {"erreur": "Aucune année scolaire courante configurée."}

    qs = Inscription.objects.filter(annee_scolaire=annee).exclude(statut='ABANDON')
    if classe_nom:
        qs = qs.filter(classe__nom__icontains=classe_nom)

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


def _req_finances(classe_nom=None):
    from finances.models import Paiement, FraisScolarite
    from inscriptions.models import Inscription
    annee = _get_annee()
    if not annee:
        return {"erreur": "Aucune année scolaire courante configurée."}

    inscrits = Inscription.objects.filter(annee_scolaire=annee).exclude(statut='ABANDON')
    if classe_nom:
        inscrits = inscrits.filter(classe__nom__icontains=classe_nom)

    encaisse = Paiement.objects.filter(inscription__in=inscrits).aggregate(s=Sum('montant'))['s'] or 0
    frais_qs = FraisScolarite.objects.filter(annee_scolaire=annee)
    if classe_nom:
        frais_qs = frais_qs.filter(classe__nom__icontains=classe_nom)
    attendu = frais_qs.aggregate(s=Sum('montant'))['s'] or 0

    ids_payes = Paiement.objects.filter(inscription__in=inscrits).values_list('inscription_id', flat=True).distinct()
    nb_total = inscrits.count()
    nb_payes = inscrits.filter(id__in=ids_payes).count()
    taux = round(float(encaisse) / float(attendu) * 100, 1) if attendu else 0

    return {
        "annee": str(annee),
        "nb_inscrits": nb_total,
        "encaisse": int(encaisse),
        "attendu": int(attendu),
        "taux": taux,
        "nb_payes": nb_payes,
        "nb_retard": nb_total - nb_payes,
    }


def _req_absences(classe_nom=None, top_n=10):
    from presences.models import Presence
    from inscriptions.models import Inscription
    annee = _get_annee()
    if not annee:
        return {"erreur": "Aucune année scolaire courante configurée."}

    inscrits = Inscription.objects.filter(annee_scolaire=annee).exclude(statut='ABANDON')
    if classe_nom:
        inscrits = inscrits.filter(classe__nom__icontains=classe_nom)

    presences = Presence.objects.filter(inscription__in=inscrits)
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


def _req_difficultes(classe_nom=None, seuil=10.0, trimestre_numero=None):
    from pedagogie.models import MoyenneGenerale
    annee = _get_annee()
    if not annee:
        return {"erreur": "Aucune année scolaire courante configurée."}

    qs = MoyenneGenerale.objects.filter(
        inscription__annee_scolaire=annee,
        moyenne__lt=seuil,
    ).select_related('inscription__eleve', 'inscription__classe')

    if classe_nom:
        qs = qs.filter(inscription__classe__nom__icontains=classe_nom)
    if trimestre_numero:
        qs = qs.filter(trimestre__numero=trimestre_numero)
    else:
        dernier = qs.order_by('-trimestre__numero').values('trimestre__numero').first()
        if dernier:
            qs = qs.filter(trimestre__numero=dernier['trimestre__numero'])
            trimestre_numero = dernier['trimestre__numero']

    resultats = list(qs.order_by('moyenne')[:30])
    return {
        "seuil": seuil,
        "trimestre": trimestre_numero,
        "nb": len(resultats),
        "eleves": [
            {"eleve": f"{m.inscription.eleve.nom} {m.inscription.eleve.prenom}",
             "classe": m.inscription.classe.nom,
             "moyenne": round(float(m.moyenne), 2)}
            for m in resultats
        ],
    }


def _req_moyennes(classe_nom, trimestre_numero=None):
    from pedagogie.models import MoyenneGenerale
    from inscriptions.models import Inscription
    annee = _get_annee()
    if not annee:
        return {"erreur": "Aucune année scolaire courante configurée."}

    inscrits = Inscription.objects.filter(
        annee_scolaire=annee, classe__nom__icontains=classe_nom
    ).exclude(statut='ABANDON')
    if not inscrits.exists():
        return {"erreur": f"Classe « {classe_nom} » introuvable ou sans inscrits."}

    classe_obj = inscrits.first().classe
    qs = MoyenneGenerale.objects.filter(inscription__in=inscrits)
    if trimestre_numero:
        qs = qs.filter(trimestre__numero=trimestre_numero)
    else:
        dernier = qs.order_by('-trimestre__numero').values('trimestre__numero').first()
        if dernier:
            qs = qs.filter(trimestre__numero=dernier['trimestre__numero'])
            trimestre_numero = dernier['trimestre__numero']

    stats = qs.aggregate(moy=Avg('moyenne'), maxi=Max('moyenne'), mini=Min('moyenne'))
    top5 = list(qs.select_related('inscription__eleve').order_by('-moyenne')[:5])
    faibles = list(qs.select_related('inscription__eleve').filter(moyenne__lt=10).order_by('moyenne')[:5])

    return {
        "classe": classe_obj.nom,
        "trimestre": trimestre_numero,
        "nb_evalues": qs.count(),
        "moyenne": round(float(stats['moy'] or 0), 2),
        "max": round(float(stats['maxi'] or 0), 2),
        "min": round(float(stats['mini'] or 0), 2),
        "top5": [{"eleve": f"{m.inscription.eleve.nom} {m.inscription.eleve.prenom}",
                  "moy": round(float(m.moyenne), 2)} for m in top5],
        "faibles": [{"eleve": f"{m.inscription.eleve.nom} {m.inscription.eleve.prenom}",
                     "moy": round(float(m.moyenne), 2)} for m in faibles],
    }


def _req_progression(classe_nom=None, sens="baisse"):
    from pedagogie.models import MoyenneGenerale
    from inscriptions.models import Inscription
    annee = _get_annee()
    if not annee:
        return {"erreur": "Aucune année scolaire courante configurée."}

    inscrits = Inscription.objects.filter(annee_scolaire=annee).exclude(statut='ABANDON')
    if classe_nom:
        inscrits = inscrits.filter(classe__nom__icontains=classe_nom)

    resultats = []
    for ins in inscrits.select_related('eleve', 'classe')[:200]:
        mgs = list(
            MoyenneGenerale.objects.filter(inscription=ins)
            .order_by('trimestre__numero')
            .values('trimestre__numero', 'moyenne')
        )
        if len(mgs) < 2:
            continue
        avant = float(mgs[-2]['moyenne'])
        apres = float(mgs[-1]['moyenne'])
        diff = apres - avant
        if sens == "baisse" and diff <= -0.5:
            resultats.append({
                "eleve": f"{ins.eleve.nom} {ins.eleve.prenom}",
                "classe": ins.classe.nom,
                "t_avant": mgs[-2]['trimestre__numero'],
                "moy_avant": round(avant, 2),
                "t_apres": mgs[-1]['trimestre__numero'],
                "moy_apres": round(apres, 2),
                "diff": round(diff, 2),
            })
        elif sens == "hausse" and diff >= 0.5:
            resultats.append({
                "eleve": f"{ins.eleve.nom} {ins.eleve.prenom}",
                "classe": ins.classe.nom,
                "t_avant": mgs[-2]['trimestre__numero'],
                "moy_avant": round(avant, 2),
                "t_apres": mgs[-1]['trimestre__numero'],
                "moy_apres": round(apres, 2),
                "diff": round(diff, 2),
            })

    resultats.sort(key=lambda x: x['diff'])
    return {"sens": sens, "nb": len(resultats), "eleves": resultats[:25]}


def _req_eleve(nom=None, prenom=None):
    from inscriptions.models import Eleve, Inscription
    from pedagogie.models import MoyenneGenerale
    from finances.models import Paiement

    if not nom and not prenom:
        return {"erreur": "Fournissez au moins un nom ou un prénom."}

    qs = Eleve.objects.all()
    if nom:
        qs = qs.filter(nom__icontains=nom)
    if prenom:
        qs = qs.filter(prenom__icontains=prenom)

    resultats = []
    for eleve in qs[:8]:
        ins = (Inscription.objects.filter(eleve=eleve)
               .select_related('classe', 'annee_scolaire')
               .order_by('-annee_scolaire__date_debut').first())
        mg = MoyenneGenerale.objects.filter(inscription=ins).order_by('-trimestre__numero').first() if ins else None
        paye = Paiement.objects.filter(inscription=ins).aggregate(s=Sum('montant'))['s'] or 0 if ins else 0
        resultats.append({
            "nom": f"{eleve.nom} {eleve.prenom}",
            "matricule": eleve.matricule,
            "classe": ins.classe.nom if ins else None,
            "annee": str(ins.annee_scolaire) if ins else None,
            "statut": ins.statut if ins else "Non inscrit",
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


# ─────────────────────────────────────────────────────────────────────────────
# Détection d'intention
# ─────────────────────────────────────────────────────────────────────────────

def _search_guide(query: str):
    """Recherche dans la base de connaissances du guide le topic le plus pertinent.
    Score = somme des longueurs des mots-clés correspondants (les plus spécifiques l'emportent)."""
    m = query.lower()
    best_topic = None
    best_score = 0
    for topic in _GUIDE_KB:
        # Score = longueur totale des keywords matchés (favorise les correspondances précises)
        score = sum(len(kw) for kw in topic["mots"] if kw in m)
        if score > best_score:
            best_score = score
            best_topic = topic
    if best_score == 0:
        # Fallback : mots significatifs de la requête vs fragments de keywords
        query_words = [w for w in re.split(r'\W+', m) if len(w) >= 4]
        for topic in _GUIDE_KB:
            score = sum(
                len(kw) for qw in query_words for kw in topic["mots"]
                if qw in kw or kw.startswith(qw)
            )
            if score > best_score:
                best_score = score
                best_topic = topic
    return best_topic if best_score > 0 else None


def _intent(msg: str) -> str:
    m = msg.lower()

    # Indicateurs de questions sur le fonctionnement de l'application (guide)
    is_howto = any(k in m for k in [
        'comment', 'aide', 'aide-moi', 'utiliser', 'faire', 'créer', 'générer',
        'configurer', 'paramétrer', 'accéder', 'étapes', 'procédure', 'tutoriel',
        'expliquer', 'guide', 'fonctionnement', 'à quoi sert', 'comment ça marche',
    ])

    # Mots-clés fonctionnels du guide (non liés aux données)
    is_guide_topic = any(k in m for k in [
        'connexion', 'login', 'mot de passe', 'compte utilisateur', 'rôle',
        'inscription', 'enregistrer élève', 'matricule', 'bulletin', 'générer',
        'relance', 'bourse', 'exonéré', 'certificat', 'attestation', 'convocation',
        'circulaire', 'signataire', 'signer', 'mobile money', 'orange money',
        'sms', 'notification', 'portail parent', 'portail', 'pwa',
        'sanction', 'discipline', 'appel', 'pointage', 'qr code',
        'examen', 'bac', 'bepc', 'cep', 'vacation', 'personnel',
        'année scolaire', 'trimestre', 'paramètre', 'sauvegarde', 'backup',
        'lent', 'lenteur', 'problème', 'erreur message',
    ])

    # Les requêtes de données priment sur le guide
    if any(k in m for k in ['cherche', 'recherche', 'trouve', 'fiche', 'renseigne']):
        return 'eleve'
    if any(k in m for k in ['recouvrement', 'encaissé', 'budget']) and not is_howto:
        return 'finances'
    if any(k in m for k in ['taux', 'montant encaissé', 'montant payé']) and not is_howto:
        return 'finances'
    if any(k in m for k in ['combien', 'effectif', 'nombre d\'inscrits', 'par classe']) and not is_howto:
        return 'effectifs'
    if any(k in m for k in ['baisse', 'hausse', 'régress', 'augment']) and not is_howto:
        return 'progression'
    if any(k in m for k in ['difficulté', 'faible', 'sous', 'inférieur', 'moins de']) \
            and any(k in m for k in ['/20', 'moyenne', 'note']) and not is_howto:
        return 'difficultes'
    if any(k in m for k in ['moyenne de la', 'résultats de la', 'notes de la']) and not is_howto:
        return 'moyennes'
    if any(k in m for k in ['absent', 'assiduité', 'justifi']) \
            and any(k in m for k in ['liste', 'top', 'résumé', 'bilan', 'combien']) and not is_howto:
        return 'absences'
    if any(k in m for k in ['financ', 'paiement', 'payé', 'frais']) \
            and any(k in m for k in ['liste', 'rapport', 'résumé', 'bilan', 'combien', 'taux']) and not is_howto:
        return 'finances'

    # Guide si question fonctionnelle détectée
    if is_howto or is_guide_topic:
        return 'guide'

    return 'inconnu'


_AIDE = (
    "Je ne comprends pas la question. Voici ce que je sais faire :\n\n"
    "📊 Données en temps réel :\n"
    "  • Taux de recouvrement des frais de scolarité\n"
    "  • Effectifs par classe\n"
    "  • Résumé des absences\n"
    "  • Élèves en difficulté (ex : « sous 8/20 »)\n"
    "  • Élèves en baisse ou en hausse entre trimestres\n"
    "  • Moyennes d'une classe (ex : « moyennes de la 3ème A »)\n"
    "  • Rechercher un élève par nom\n\n"
    "📖 Guide d'utilisation (dites « comment » ou posez une question) :\n"
    "  • Comment enregistrer un paiement ?\n"
    "  • Comment générer un bulletin ?\n"
    "  • Comment faire l'appel ?\n"
    "  • Comment créer un compte utilisateur ?\n"
    "  • Comment configurer les signataires ?\n"
    "  • Comment envoyer des relances de paiement ?\n"
    "  • Comment attribuer une bourse ?\n"
    "  • Comment utiliser le portail parent ?\n\n"
    "Reformulez votre question en mentionnant l'un de ces thèmes."
)


def _process(user_message: str) -> str:
    try:
        intent = _intent(user_message)
        classe = _extract_classe(user_message)
        trimestre = _extract_trimestre(user_message)

        if intent == 'eleve':
            nom, prenom = _extract_nom(user_message)
            return _fmt_eleve(_req_eleve(nom=nom, prenom=prenom))

        if intent == 'finances':
            return _fmt_finances(_req_finances(classe_nom=classe))

        if intent == 'absences':
            return _fmt_absences(_req_absences(classe_nom=classe))

        if intent == 'progression':
            m = user_message.lower()
            sens = "hausse" if any(k in m for k in ['hausse', 'améliore', 'augment', 'progress']) else "baisse"
            return _fmt_progression(_req_progression(classe_nom=classe, sens=sens))

        if intent == 'difficultes':
            seuil = _extract_seuil(user_message, default=10.0)
            return _fmt_difficultes(_req_difficultes(classe_nom=classe, seuil=seuil, trimestre_numero=trimestre))

        if intent == 'moyennes':
            if not classe:
                return "Précisez la classe, par exemple : « Moyennes de la 3ème A »."
            return _fmt_moyennes(_req_moyennes(classe_nom=classe, trimestre_numero=trimestre))

        if intent == 'effectifs':
            return _fmt_effectifs(_req_effectifs(classe_nom=classe))

        if intent == 'guide':
            topic = _search_guide(user_message)
            if topic:
                return topic["réponse"]
            # Si aucun topic précis trouvé, proposer la liste
            return (
                "Je n'ai pas trouvé de réponse précise dans le guide pour cette question.\n\n"
                "Voici les sujets documentés :\n"
                + "\n".join(f"  • {t['titre']}" for t in _GUIDE_KB)
                + "\n\nPosez votre question avec des mots-clés plus précis."
            )

        return _AIDE

    except Exception as exc:
        logger.exception("Erreur chatbot")
        return f"Une erreur est survenue lors de la requête : {exc}"


# ─────────────────────────────────────────────────────────────────────────────
# Point d'entrée — interface avec la vue Django
# ─────────────────────────────────────────────────────────────────────────────

def chat(messages_history: list, user_message: str) -> tuple[str, list]:
    """
    Traite un message et retourne (réponse, historique_mis_à_jour).
    L'historique utilise le format {'role': ..., 'text': ...} directement.
    """
    response = _process(user_message)
    updated = list(messages_history) + [
        {"role": "user", "text": user_message},
        {"role": "assistant", "text": response},
    ]
    if len(updated) > 20:
        updated = updated[-20:]
    return response, updated
