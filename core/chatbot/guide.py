"""Base de connaissances du guide utilisateur pour l'assistant YELEN SCHOOL."""

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
            "  Le matricule est généré automatiquement (format CODE_ETAB-AAAA-NN)\n\n"
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
            "  Le matricule (format CODE_ETAB-P-AAAA-NN) est généré automatiquement.\n\n"
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

