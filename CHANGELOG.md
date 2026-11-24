# Journal des versions

Format : une entrée par version livrée (`VERSION` + tag `vX.Y.Z`). Les correctifs incrémentent le
troisième chiffre, les évolutions fonctionnelles le deuxième, les changements de rupture le premier.

## 5.65.23 — 2026-11-13

- **Deux fiches du personnel portant le même e-mail rendaient l'enseignant invisible.** Le lien compte → fiche se fait par l'adresse e-mail ; rien n'interdit à deux fiches de la partager (agent saisi deux fois). L'application retenait **la première trouvée**, sans critère : quand l'affectation se trouvait sur la seconde, l'enseignant n'avait **ni classe ni discipline**, et le message lui disait que les affectations ne portaient pas son nom — alors que tout était correct dans les écrans.
- **La fiche active qui porte réellement des enseignements est désormais retenue**, à défaut la première. Effet sur tout le parcours enseignant d'un seul coup : saisie des notes, évaluations, présences, cahier de textes, appréciations.
- Recommandation : désactiver la fiche fantôme (`Personnel → Modifier → Actif` décoché) plutôt que la supprimer, et garder l'adresse du compte sur la fiche réellement affectée.
- Aucune migration, aucune nouvelle URL, aucun changement des notes ni des documents.

## 5.65.22 — 2026-11-13

- **Un enseignant sans cycle assigné ne voyait ni sa classe ni sa discipline.** Sa portée est son **affectation** (`Pédagogie → Enseignements`) ; s'y ajoutait le filtre des **cycles autorisés du compte**, vides par défaut sur un compte créé à la main. L'affectation était correcte, le second filtre ne laissait rien passer : sélection de classe de la saisie des notes, filtre par classe des évaluations et liste d'appel étaient **vides**.
- **La portée d'un enseignant est désormais exclusivement son affectation** : ses cycles de compte ne la restreignent plus. Les autres rôles sont inchangés et le filtre par cycle continue de s'appliquer à la direction, au censeur, au secrétaire.
- Le cloisonnement reste entier : un enseignant ne voit toujours que **ses** classes, celles de ses enseignements de l'année.
- Aucune migration, aucune nouvelle URL, aucun changement des notes ni des documents.

## 5.65.21 — 2026-11-13

- **Le message « aucun enseignement ne vous est attribué » cachait trois causes.** La plus fréquente : la ligne d'affectation existe pour l'année, mais son champ **Enseignant** est resté **vide**. L'administration, croyant à une affectation manquante, en créait une seconde — refusée, la matière étant déjà prise dans cette classe. Le message nomme désormais la cause exacte : « les affectations de l'année ne portent pas votre nom : le champ Enseignant y est resté vide ».
- **Le champ « Enseignant » devient obligatoire** dans *Nouvelle affectation* hors primaire, dès qu'une classe est choisie : une ligne sans enseignant ne donne aucun cours, elle est refusée à la saisie plutôt que créée en silence. Au primaire, la liste restant limitée à la classe, aucune contrainte n'y est ajoutée.
- **Une ligne déjà muette se corrige par le bouton Modifier**, jamais en créant un doublon.
- Aucune migration, aucune nouvelle URL, aucun changement des notes ni des documents.

## 5.65.20 — 2026-11-13

- **« Planifier un devoir » : deuxième cause de blocage, enfin nommée.** Quand **aucune période d'évaluation** n'est configurée pour l'année, le champ *Trimestre / Période* est vide et l'enregistrement échoue sur un champ que l'enseignant ne peut pas remplir. Une alerte explicite indique désormais la cause et la correction (`Paramètres › Périodes`).
- **Elle s'adresse à tous les rôles**, pas seulement aux enseignants : la direction voit le même message et sait immédiatement ce qui manque.
- Rappel : les périodes ne sont **jamais créées automatiquement** — ni à l'installation, ni par le jeu de démonstration. Leur création reste un préalable obligatoire pour toute évaluation.
- Aucun message dès qu'une période existe. Aucune migration, aucune nouvelle URL, aucun changement des notes ni des documents.

## 5.65.19 — 2026-11-13

- **« Planifier un devoir » n'affiche plus une liste muette.** Un enseignant dont la liste **Enseignement** était vide ne voyait qu'une liste déroulante sans aucun choix — aucune cause, aucune correction à demander. Une alerte explicite distingue désormais les deux situations : la **fiche du personnel ne porte pas l'adresse e-mail du compte** (cas le plus fréquent : fiche non reliée, donc aucun enseignement retrouvé) ou **aucun enseignement n'est affecté pour l'année**.
- **L'alerte ne s'affiche que si le choix est réellement impossible** : dès qu'une discipline est disponible, le formulaire est inchangé.
- Le cloisonnement enseignant est intact : il ne voit et ne choisit que ses propres enseignements. Aucune migration, aucune nouvelle URL, aucun changement des notes ni des documents.

## 5.65.18 — 2026-11-13

- **Un professeur peut enfin être affecté à plusieurs classes la même année.** Dans la fenêtre *Nouvelle affectation* (`Pédagogie → Enseignements`), la liste des enseignants ne proposait que les personnes **déjà rattachées à la classe choisie** — son titulaire et ceux qui y avaient déjà un enseignement. Un professeur de mathématiques de la 3e A n'apparaissait donc **pas** dans la liste de la 4e B : impossible de l'y affecter, et donc de lui ouvrir la saisie des notes de cette seconde classe. Le modèle, lui, l'autorisait depuis toujours : la contrainte ne porte que sur classe × matière × année, jamais sur l'enseignant.
- **La liste couvre désormais le personnel actif de l'établissement** au post-primaire, au secondaire et au préscolaire — le même périmètre que la liste « Nom du professeur » des absences. Un enseignant peut recevoir autant de classes et de disciplines que nécessaire.
- **Le primaire est inchangé.** Le titulaire y couvre toutes les disciplines de sa classe : la liste reste limitée aux enseignants de la classe choisie, et le libellé le rappelle (« Aucun enseignant associé à cette classe »).
- Le message d'une liste vide ne parle plus de la classe hors primaire (« Aucun personnel actif dans l'établissement »). Aucune migration, aucune nouvelle URL, aucun changement des notes ni des documents.

## 5.65.17 — 2026-11-13

- **« Matière de discipline » décide enfin de la moyenne.** La case de la fenêtre *Ajouter une matière* était enregistrée mais **lue nulle part** : elle n'avait aucun effet. Cochée (défaut), la matière compte dans la moyenne générale avec son coefficient ; décochée, elle est suivie **hors moyenne** — notes et appréciations conservées et imprimées, coefficient ignoré dans la moyenne, le rang et les décisions.
- **Aucune moyenne existante n'est bouleversée.** Le champ valait `False` par défaut et n'était lu nulle part : appliquer le filtre tel quel aurait exclu **toutes** les matières de tous les établissements. Le défaut passe à `True` et une reprise de données marque explicitement toutes les matières déjà créées comme disciplines. Un établissement ne perd donc aucune moyenne ; il décoche ensuite, matière par matière, ce qui doit sortir du calcul.
- **Une aide contextuelle** sous la case explique la règle dans les fenêtres d'ajout et de modification ; le gabarit affiche désormais le texte d'aide des cases à cocher, qui était ignoré.
- Aucun changement des notes, des résultats par matière ni des documents imprimés. Une migration de données (défaut + reprise), aucune nouvelle URL.

## 5.65.16 — 2026-11-13

- **Trois écrans donnaient des résultats faux au primaire, pas seulement un libellé.** Le **portail parent** lisait `mg.valeur`, un champ qui n'existe sur aucun modèle : la tuile de moyenne restait **toujours vide**. La **prédiction de réussite** divisait une moyenne sur 10 par 20 : un élève à 8,50/10 obtenait un score de base de 42 % au lieu de 85 %, et son pronostic d'examen était faussé. Le **tableau de bord**, les **statistiques par enseignant** et le **chatbot** agrégeaient des moyennes de barèmes différents : moyenne d'établissement et **taux de réussite faux** dès qu'une classe du primaire existe. Tous s'appuient désormais sur `moyenne_sur_20`, toujours exprimée sur 20.
- **Les autres écrans suivent le barème du cycle** — fiche de suivi de l'élève, PV du conseil de classe, tableau des bulletins d'une classe, saisie des appréciations, bilan des périodes, portail vie scolaire et moyennes par discipline : valeur, couleur et légende. Les seuils de couleur des moyennes par discipline (10 et 14 sur 20) deviennent 5 et 7 au primaire, via la nouvelle propriété `Classe.seuil_bien`.
- **Le taux d'admission** du bilan des périodes et du PDF de bilan comptait zéro admis dans toutes les classes du primaire (seuil figé à 10) : il applique le seuil de chaque classe.
- **Aucun chiffre de moyenne n'est retouché** : seuls les comparaisons, agrégats et libellés étaient faux. Aucune nouvelle URL, aucun changement de schéma, aucune migration.

## 5.65.15 — 2026-11-13

- **Le bulletin annuel et la page parent annoncent le barème du cycle.** Le bulletin annuel web affichait « 8,50/20 » pour un élève du primaire dont la moyenne est sur 10 — dans la tuile de moyenne annuelle, l'en-tête du tableau des périodes et la ligne de pied — et la page publique du parent écrivait « Moyenne /20 ». Les deux suivent désormais le barème : `/10` au préscolaire et au primaire, `/20` ailleurs.
- **Les couleurs suivent le seuil du cycle.** Sur les deux pages, une moyenne de 8,50 au primaire s'affichait en échec (seuil figé à 10) ; elle apparaît en réussite, le seuil étant 5.
- **La mention se calcule enfin sur le bon barème.** `_get_mention()` compare aux seuils 16 / 14 / 12 / 10, qui sont des seuils sur 20 : au primaire, un 8,50/10 vaut 17/20 et doit donner **« Très Bien »** — il donnait « Insuffisant ». La moyenne est ramenée sur 20 avant le calcul ; au secondaire, un 8,50/20 reste « Insuffisant ».
- **Aucun chiffre de moyenne ne change** : ni les moyennes, ni les rangs, ni les décisions d'admission, ni les statistiques de classe. Aucune nouvelle URL, aucun changement de schéma, aucune migration.

## 5.65.14 — 2026-11-13

- **Le palmarès annuel annonce le barème du cycle.** La colonne « Moy. Annuelle » affichait « 8,00/20 » pour un élève du primaire dont la moyenne est en réalité sur 10 : elle s'écrit désormais **« 8,00/10 »** au préscolaire et au primaire, « /20 » ailleurs — comme la page d'aperçu du palmarès, qui était déjà correcte.
- **La fiche de discipline annonce le barème du cycle.** Quatre mentions étaient figées sur 20 : l'en-tête de la colonne des moyennes (`Moy /10` au primaire), les trois statistiques (meilleure moyenne, moyenne de la classe, moyenne la plus faible), la légende (`≥ 5/10 — admis`, `< 5/10 — insuffisant`) et le **seuil de couleur** des notes et des moyennes, qui passe de 10 à 5. Sans ce dernier point, toutes les moyennes du primaire — y compris 9,50/10 — se seraient imprimées en « insuffisant ».
- **Les chiffres ne changent pas** : les moyennes étaient déjà calculées et converties sur le barème du cycle avant impression. Seuls les libellés et le seuil de couleur étaient figés.
- Post-primaire et secondaire : aucun changement, tout reste sur 20. Aucune nouvelle URL, aucun changement de schéma, aucune migration.

## 5.65.13 — 2026-11-13

- **Le cartouche d'identité de la fiche de discipline nomme le titulaire au primaire.** La barre d'informations en tête de fiche (« Enseignant(e) ») affichait l'enseignant **de la matière** alors que la signature annonce « L'Enseignant(e) titulaire » : les deux pouvaient désigner deux personnes différentes. Au primaire, le cartouche nomme désormais le **titulaire de la classe**, avec son nom et son matricule.
- **Replis conservés** : sans titulaire désigné pour la classe, le cartouche garde l'enseignant affecté à la matière ; sans aucun des deux, « Non assigné ».
- **Post-primaire et secondaire : aucun changement** — le cartouche garde l'enseignant de la matière, comme la signature et comme le reste de la fiche.
- Le bloc de signature, le contresignataire du cycle et la date sont inchangés. Aucune nouvelle URL, aucun changement de schéma, aucune migration.

## 5.65.12 — 2026-11-13

- **Au primaire, la fiche de discipline nomme « l'Enseignant(e) titulaire ».** Le titre de signature était « L'Enseignant(e) de *Mathématiques* » dans tous les cycles, alors qu'au primaire le titulaire enseigne **toutes** les disciplines de sa classe : chaque matière semblait avoir son professeur. La fiche porte désormais « L'Enseignant(e) titulaire », quel que soit le relevé imprimé.
- **Le titulaire signe la discipline restée sans enseignant affecté.** Au primaire, si la matière n'a pas de personnel affecté, la fiche imprimait « (Aucun enseignant assigné à cette discipline) » : c'est maintenant le **titulaire de la classe** qui est nommé et signe, comme il signe déjà les bulletins, le relevé de notes, le relevé des moyennes et le palmarès (5.65.8).
- **Post-primaire et secondaire : aucun changement.** Le titre reste « L'Enseignant(e) de *Mathématiques* » et la fiche conserve l'enseignant de la matière ; le repli sur le titulaire ne s'applique pas. Le cartouche d'identité en tête de fiche, le contresignataire du cycle et la date sont inchangés.
- Aucune nouvelle URL, aucun changement de schéma, aucune migration.

## 5.65.11 — 2026-11-13

- **Le rang du bulletin annonce son effectif.** La ligne récapitulative du bulletin trimestriel affichait « 5e / 5 » — le nombre d'élèves sans dire de quoi il s'agissait — alors que le bloc statistiques du même document écrivait « Rang 5ème / 5 élèves ». Elle affiche désormais « 5e / 5 élèves », au singulier ou au pluriel selon l'effectif.
- **Une seule orthographe de l'ordinal.** Le bulletin trimestriel mêlait « 5e » et « 5ème » sur la même page ; le bulletin annuel PDF, l'aperçu du bulletin et les infobulles de médailles du relevé de notes utilisaient la forme longue. Toute l'application écrit désormais `1er`, puis `2e`, `3e`… — la forme la plus répandue et l'usage typographique courant.
- Aucun changement de calcul ni de classement : seul le libellé du rang change. Aucune nouvelle URL, aucun changement de schéma, aucune migration.

## 5.65.10 — 2026-11-13

- **Le relevé des moyennes de la classe annonce le barème du cycle.** La colonne était intitulée « Moyenne /20 » quel que soit le cycle, alors que la moyenne d'un élève du primaire est sur **10** : un élève à 8,45 y passait pour un élève en difficulté. Le libellé suit désormais le barème réel — **« Moyenne /10 »** au préscolaire et au primaire, « Moyenne /20 » au post-primaire et au secondaire — et la légende annonce le bon seuil d'insuffisance (**< 5/10** au primaire, < 10/20 ailleurs).
- Les **chiffres affichés n'ont pas changé** : les moyennes étaient déjà calculées et stockées sur le barème du cycle ; seul le libellé était figé sur 20, y compris dans la légende.
- Le style de la ligne (gras = admis, gras italique = insuffisant) suit déjà le barème du cycle et reste inchangé.
- Aucune nouvelle URL, aucun changement de schéma, aucune migration.

## 5.65.9 — 2026-11-13

- **La fiche de discipline est contresignée par le directeur du cycle.** Elle ne portait que la signature de l'enseignant de la matière. Elle affiche désormais deux signatures côte à côte : **l'enseignant de la matière** à gauche (fonction, signature scannée, nom, matricule) et le **directeur du cycle** à droite (fonction, signature scannée, nom), la date restant rattachée à la signature de l'enseignant. Sans enseignant affecté, seule la signature du directeur est imprimée ; sans signataire configuré pour le cycle, la fiche reste signée par l'enseignant seul.
- Le contresignataire est celui configuré pour le type `BULLETIN` du **cycle de la classe** dans `Paramètres → Signataires des documents` — même résolution que les bulletins et les relevés.
- **Cartes scolaires : aucun code modifié.** La carte individuelle et l'impression des cartes de classe portaient déjà, sous la photo, la signature du directeur du cycle (type `CARTE_ID`) ; un test existant le vérifie. Si l'image n'apparaît pas, c'est que le signataire `CARTE_ID` n'est pas configuré ou n'a pas de signature scannée.
- Aucune nouvelle URL, aucun changement de schéma, aucune migration.

## 5.65.8 — 2026-11-13

- **Au primaire, le titulaire signe désormais tous les documents de sa classe.** La règle existait pour les bulletins et la liste alphabétique ; elle est étendue au **relevé de notes**, au **relevé des moyennes de la classe**, au **palmarès annuel** et aux **moyennes par discipline**. Chaque document porte le titulaire à gauche et le signataire du cycle à droite, selon le motif déjà en place sur la liste alphabétique ; sans titulaire désigné, il est signé exactement comme auparavant.
- **La règle est maintenant limitée au primaire, comme sa documentation l'annonçait.** Le code appliquait la signature du titulaire à **tous les cycles** : au secondaire, un titulaire affecté à une 3e signait donc aussi. Un seul point de décision (`_titulaire_signe`) conditionne désormais les deux tags de signature : au post-primaire et au secondaire, les documents sont signés par le signataire du cycle, comme avant la 5.55.0.
- Le relevé de notes reçoit la classe dans son contexte PDF, condition nécessaire pour que le bloc du titulaire soit rendu — la page HTML du relevé était déjà correctement alimentée.
- Aucune nouvelle URL, aucun changement de schéma, aucune migration.

## 5.65.7 — 2026-11-13

- **Supprimer la note d'un élève depuis la fenêtre de saisie.** Vider le champ d'un élève puis enregistrer efface désormais sa note pour l'évaluation — au primaire comme au secondaire, la page étant commune aux cycles. Jusqu'ici un champ vide était ignoré : aucune note ne pouvait être retirée une fois saisie. Une confirmation nomme le nombre de notes concernées avant l'envoi, et un message de bilan « N note(s) supprimée(s). » rend l'opération visible. Les moyennes de la discipline, la moyenne générale et le rang sont recalculés immédiatement.
- **Garde-fous conservés.** Un élève **absent** garde sa note (son champ est vide par construction : décocher « Absent » d'abord) ; un élève **dispensé** n'est pas concerné (la dispense efface déjà la note) ; un champ vide sans note ne fait rien ; un envoi partiel n'efface que les champs réellement transmis. La clôture du trimestre, le périmètre de l'enseignant et le contrôle de paiement continuent de refuser l'opération comme le reste de la saisie. Le mode hors réseau suit.
- Aucune nouvelle URL, aucun changement de schéma, aucune migration.

## 5.65.6 — 2026-11-13

- **La carte « Saisies » de la page de saisie des notes compte des élèves, plus des champs.** La page présente chaque élève deux fois — une ligne de tableau sur ordinateur, une carte sur téléphone — et les deux jeux de champs se recopient. Le compteur les additionnait : il affichait « 10 / 5 » pour cinq élèves notés, et le bandeau du bas doublait également. Le décompte se fait désormais par élève : un absent compte une fois, un dispensé ne compte pas, et le total ne peut plus dépasser l'effectif. Les statistiques (moyenne, minimum, maximum) et l'enregistrement des notes étaient et restent exacts.
- **Le contrôle qualité s'évalue sur des effectifs réels.** Les alertes (taux d'absents, zéros non justifiés, notes identiques, moyenne très basse ou très haute, tous au maximum) portaient sur des listes doublées : leurs seuils étaient franchis avec deux fois moins d'élèves, et le message du taux d'absents annonçait un effectif faux. Un seul absent sur cinq ne déclenche plus « taux d'absents élevé » ; deux notes identiques ne déclenchent plus « notes identiques suspectes ».
- Aucun changement de schéma, aucune migration ; la saisie et l'enregistrement des notes sont inchangés.

## 5.65.5 — 2026-11-13

- **Sigle de l'évaluation par compétences adapté au cycle.** Au primaire, l'évaluation par compétences relève de l'**Approche Pédagogique Intégratrice (API)** et non de l'APC : les intitulés affichés portent désormais le bon sigle. Le préscolaire, le post-primaire et le secondaire restent en **Approche Par Compétences (APC)**. Concerne l'intitulé de la section du bulletin trimestriel PDF (« Approche Pédagogique Intégratrice (API) » au primaire), le référentiel des compétences (« Catégorie API » / « Catégorie APC », en-tête de colonne compris) et le sous-titre de la page des bulletins de compétences.
- La règle est portée par deux propriétés du cycle (`sigle_competences`, `libelle_competences`) dans `parametres/models/etablissement.py`, sans changement de schéma ni migration.
- Vérifications ajoutées : `TestSigleCompetences` (PRIM → API ; PRES, POST, SEC → APC) et deux tests de bulletin (le bulletin primaire porte le libellé API, le bulletin du secondaire n'affiche aucune section de compétences).

## 5.65.4 — 2026-11-14

- **Règle de signature clarifiée : un document hors cycle se signe sur la fiche de l'établissement.** Les deux listes globales — tous les élèves (`Élèves → PDF`) et tout le personnel (`Personnel → PDF`) — sont désormais signées exclusivement par le directeur général saisi dans `Paramètres → Établissement` : son nom et la signature enregistrée sous « Signature du directeur général ». La case « Directeur général » d'une fiche du personnel et les signataires configurés cycle par cycle (`LISTE_ELEVES`, `LISTE_PERSONNEL`) n'interviennent plus sur ces deux documents. Les documents d'un cycle (bulletins, certificats, listes d'une classe ou d'un cycle…) restent signés par le signataire de leur cycle, sans changement.
- Le tag `signataire_direction_generale` ne lit plus qu'une seule source : `IdentiteEtablissement`. La fiche établissement énonce la règle et avertit lorsqu'aucune signature n'est enregistrée. Aucun changement de schéma, aucune migration.

## 5.65.3 — 2026-11-14

- **Les listes globales impriment la signature du directeur général de la fiche établissement.** Quand aucun directeur général n'est désigné sur une fiche du personnel, le repli sur `Paramètres → Établissement` n'imprimait que le nom : la signature enregistrée sous « Signature du directeur général » est désormais apposée. Concerne les deux listes globales (liste de tous les élèves, liste du personnel de tous les cycles). Sans image enregistrée, rien ne change : l'espace reste vierge pour la signature manuscrite. Aucun changement de schéma, aucune migration.

## 5.65.2 — 2026-11-13

- **Liste du personnel (tous les cycles) signée par le directeur général.** Le PDF de `Personnel → PDF` couvre l'établissement entier : il porte désormais la signature du directeur général désigné sur sa fiche du personnel, et non plus celle d'un signataire de cycle. Replis : signataire du type « Liste du Personnel » pour l'année, puis nom de la fiche établissement, sans signature scannée. La liste du personnel d'un cycle (`Documents → Liste du personnel`) reste signée par le signataire de ce cycle. L'année scolaire de l'établissement est maintenant transmise au gabarit, ce qui rend ce repli effectif ; même correction pour la liste générale des élèves.
- Résolution centralisée dans le tag `signataire_direction_generale` (ex-`signataire_directeur_general`, renommé et paramétré par type de document). Aucun changement de schéma, aucune migration.

## 5.65.1 — 2026-11-13

- **Liste générale des élèves signée par le directeur général.** Le PDF de la liste de tous les élèves (exports › liste des élèves) ne reprend plus la signature du cycle — il affiche celle du directeur général désigné dans le personnel. Un signataire propre au type « Liste des Élèves » peut être configuré dans Paramètres › Signataires à défaut ; sinon le nom de la fiche établissement est imprimé, sans signature scannée. Les listes alphabétiques par classe restent signées par le titulaire et le signataire du cycle.
- La fiche établissement indique désormais si un directeur général est désigné et, à défaut, rappelle que son nom sert de solution de repli. Nouveau type de document `LISTE_ELEVES` (migration `parametres/0051`).

## 5.65.0 — 2026-09-06

- **Fiche établissement unique.** Le menu « Établissement » rassemble maintenant les données du site et les informations officielles ; nom, adresse, ville, téléphone, courriel et logo ne sont saisis qu'une fois et sont synchronisés pour les documents et le reste de l'application. L'ancien lien d'identité est retiré du menu mais reste compatible. Les droits existants sont fusionnés sans supprimer d'accès ; les anciennes coordonnées préremplissent les champs officiels lorsqu'ils étaient vides.
- Le premier enregistrement affiche maintenant la fiche enregistrée ; le code interne et le pays restent des champs distincts, clairement identifiés.

## 5.64.0 — 2026-09-06

- **Organisation multi-cycle d’un établissement.** Référence des cycles centralisée ; migrations relationnelles préservant les cycles historiques des manuels et des frais de scolarité. Les affectations professionnelles multi-cycles et la désignation annuelle des directeurs de cycle sont distinctes des droits de consultation des comptes ; la direction générale reste distincte.
- **Démonstration étendue au secondaire.** Le jeu inclut les quatre cycles et 11 classes, avec tarifs, matières et progression pour `SEC`. `charger_demo --eleves N` conserve exactement l’effectif demandé, réparti entre les classes.

## 5.63.61 — 2026-09-06

- **Masquage des résultats et bulletins des élèves sans paiement net admissible.** Les relevés à l'écran et leurs PDF, les tableaux de moyennes, les bulletins trimestriels/annuels individuels et en lot, ainsi que les accès parent/élève et API, appliquent désormais la règle centralisée d'accès aux notes. Un paiement net positif, même partiel, et les exonérations restent autorisés ; aucune note n'est supprimée. Aucun changement de schéma ni migration.

## 5.63.60 — 2026-09-06

- **Contrôle central des notes impayées.** Le modèle `Note` vérifie aussi chaque création ou modification via `.save()` : l'administration et les autres écritures passant par le modèle ne peuvent plus contourner le blocage des formulaires et imports. Tests de régression couvrant le POST direct et l'écriture modèle. Aucun changement de schéma ni migration.

## 5.63.59 — 2026-09-06

- **Saisie des notes : élargit le contrôle aux types non publics.** Tout type d'établissement configuré autre que `PUBLIC` (notamment `PRIVE` et `CONFESSIONNEL`) déclenche le blocage des élèves non exonérés au montant net de scolarité nul. La saisie directe et les imports sont protégés ; `PUBLIC` reste exclu. Aucun changement de schéma ni migration.

## 5.63.58 — 2026-09-06

- **Correction du contrôle de paiement avant saisie des notes.** Le blocage des élèves privés non exonérés au montant net nul s'applique désormais même sans tarif actif configuré pour l'année. Le calcul porte sur les paiements des rubriques de scolarité (net des remboursements), et le seuil est exactement zéro. La saisie directe et l'import Excel sont protégés ; exonérés, versements nets non nuls et établissements non privés restent hors blocage.
- Aucun changement de schéma, aucune migration.

## 5.63.57 — 2026-09-06

- **Saisie des notes bloquée sans paiement de scolarité dans le privé.** Pour tout cycle, les élèves privés non exonérés dont le total versé net (paiements moins remboursements) sur l'inscription annuelle est nul sont exclus de la saisie directe et de l'import Excel. Les exonérés et les élèves ayant effectué un versement net positif, même partiel, restent autorisés. Les établissements d'un autre type ne sont pas concernés.
- Aucun changement de schéma, aucune migration.

## 5.62.0 — 2026-11-06

- **Extension du filtrage par cycle aux vues restantes.** Le middleware `CycleAccessMiddleware` et les utilitaires `filtrer_classe_par_cycle` / `get_cycle_ids` sont désormais appliqués à : `appel_list` et `appel_csv` (présences), `sanction_list` (sanctions disciplinaires), `classe_result_list`, `bilan_periodes`, `resultat_classe` et `moyennes_disciplines` (résultats/bulletins). Chaque vue vérifie que l'utilisateur a accès au cycle des données affichées ; sinon, une erreur est renvoyée et l'accès est refusé.

## 5.61.0 — 2026-11-06

- **Filtrage des données par cycle (isolation des données).** Nouveau middleware `CycleAccessMiddleware` qui détermine, pour chaque utilisateur, les cycles qu'il est autorisé à voir. Deux nouveaux champs sur `User` : `cycles` (ManyToMany vers `Cycle`) et `est_tous_cycles` (booléen). Règles : SUPER_ADMIN / DIRECTEUR_RESEAU voient tous les cycles ; `est_tous_cycles=True` voit tous les cycles ; `cycles` assignés voit seulement ces cycles ; sans aucun des deux → données vides. Utilitaires `filtrer_par_cycle`, `filtrer_eleve_par_cycle`, `filtrer_classe_par_cycle` dans `yelen_school/cycle_filter.py`. Vues filtrées : `classe_list`, `eleve_list`, `evaluation_list`, `saisie_classe_select` (saisie des notes). Une migration `accounts/0010_add_cycles_to_user.py` ajoute les champs.

## 5.60.6 — 2026-11-06

- **Paramétrage des signataires en une seule fenêtre (matricule).** Nouvelle page `Paramètres → Signataires — Matricule` affichant, sur une même fenêtre, une grille matricielle : lignes = types de documents par catégorie, colonnes = cycles (Préscolaire, Primaire, Post-primaire, Secondaire). Chaque cellule permet de créer ou modifier le signataire (membre du personnel, fonction, titre honorifique) pour l'intersection cycle × type de document × année scolaire. Les types de documents sans cycle (`cycle=NULL`) s'appliquent à tous les cycles ; chaque cycle peut configurer son propre signataire.
- Les vues existantes (`signataires_list`, `signataires_list_detail`, `signataire_edit`, `signataire_config`, `signataire_formulaire`) restent intactes.
- Aucun changement de calcul, aucune migration.

## 5.60.5 — 2026-11-05

- **Colonne Appréciation du bulletin primaire remplie depuis la grille « Appréciation Moyennes Primaire ».** Au
  préscolaire et au primaire, l'appréciation de chaque matière sur le bulletin trimestriel provient de la grille
  `AppreciationMoyennePrimaire` (moyenne de la matière sur 10 → libellé Excellent/Bien/Passable/…), configurée
  dans `Paramètres → Appréciation Moyennes Primaire`. Une appréciation saisie manuellement par l'enseignant
  (« Pédagogie → Appréciations par matière ») reste prioritaire. Sans grille configurée, la colonne reste vide.
- Aucun changement de calcul, aucune migration.

## 5.60.4 — 2026-11-05

- **Samedi comme jour de classe dans le champ « Jour » de l'emploi du temps.** Samedi (jour 6) est proposé par défaut dans le menu déroulant lors de l'ajout d'une séance (`Vie Scolaire → Emploi du temps → Ajouter une séance`). La liste respecte la configuration des jours de classe : si seuls Lundi–Vendredi sont actifs, Samedi n'apparaît pas. Une séance ne peut pas être placée un samedi non configuré.
- Aucun changement de calcul, aucune migration.

## 5.60.3 — 2026-11-05

- **Saisie des notes filtrée par scolarité (établissement privé).** Dans un établissement privé, un élève non
  inscrit ou dont le total dû de scolarité est <= 0 n'apparaît plus dans la page de saisie des notes
  (`Pédagogie → Évaluations → Saisir les notes`). Cette règle ne s'applique pas aux établissements publics.
- Aucun changement de calcul, aucune migration.

## 5.60.2 — 2026-11-05

- **Colonne Appréciation remplie sur le bulletin primaire.** L'appréciation saisie par l'enseignant pour chaque
  matière (via « Pédagogie → Appréciations par matière ») s'affiche désormais dans la colonne Appréciation du
  bulletin trimestriel et de l'aperçu, au primaire comme au post-primaire et au secondaire.
- **Espace pour la signature de l'enseignant titulaire.** La zone de signature du bloc « Enseignant titulaire »
  comporte désormais un espace vierge entre le intitulé de fonction et le nom imprimé de l'enseignant, pour
  permettre la signature manuscrite sur le bulletin imprimé.
- Aucun changement de calcul, aucune migration.

## 5.60.1 — 2026-11-05

- **Bulletin trimestriel au barème de la classe.** L'en-tête de colonne affiche « Moy. /10 » au préscolaire et au
  primaire (au lieu de « Moy. /20 ») et la ligne récapitulative « 7,86 / 10 » (au lieu de « 7,86 / 20 ») ; le
  maximum du total de points suit le barème (coef × 10). Même règle à l'écran d'aperçu du bulletin.
- **Colonne « Note pond. » supprimée** du tableau des notes (PDF, lot de classe, duplicata et aperçu) : le tableau
  passe à six colonnes — matières 27 %, coef 7 %, moyenne 12 %, appréciation 19 %, professeur 24 %, signature 11 %.
  La note pondérée reste calculée dans le total des points, qui est inchangé.
- Aucun changement de calcul, aucune migration.

## 5.60.0 — 2026-11-05

- **Moyennes du primaire sur 10 : la note saisie est la moyenne de la discipline.** Au préscolaire et au primaire
  (`Cycle.code` PRES/PRIM), `CalculateurMoyenne` ne pondère plus les notes par type d'évaluation : la moyenne de la
  discipline est la moyenne des notes ramenées au barème de la classe (10), la moyenne générale est la moyenne
  pondérée par coefficient des disciplines sur 10, et le seuil de validation est la moitié du barème (5/10).
  `MoyenneGenerale.bareme`, `moyenne_suffisante` et le total de points maximum suivent ce barème ; les moyennes sur
  20 restent enregistrées (`moyenne_sur_20`) pour les états secondaires. Le post-primaire et le secondaire sont
  inchangés.
- **Bouton « Calculer les moyennes » fiabilisé** : il calcule la moyenne de chaque élève et **annonce le nombre de
  moyennes calculées** ; sans aucune note sur la période, il affiche un avertissement explicite (classe, période,
  enseignements à vérifier) au lieu d'un « calcul terminé » trompeur. Une évaluation **notée** entre désormais dans
  le calcul même si son statut est resté « Planifiée » ; seules les évaluations **annulées** sont écartées.
- **Affichage au barème** : page Résultats, bulletin trimestriel, bulletin annuel, palmarès annuel et relevé de
  moyenne de la classe affichent « /10 » au primaire (seuil 5,00/10) et « /20 » ailleurs ; le commentaire de bulletin
  généré automatiquement suit le même barème.
- Aucune migration : `Classe.bareme_moyenne` / `seuil_moyenne` et `MoyenneGenerale.bareme` sont des propriétés.

## 5.59.0 — 2026-11-05

- **Impression des absences d'une période.** La liste des absences accepte un **intervalle de dates** (`du` / `au`)
  à la place du mois, et le bouton **Imprimer la période** produit un PDF A4 portrait signé : détail des séances
  (professeur, date, classe, matière, horaire, heures, observation, justifiée, jours à retenir), total d'heures, puis
  bilan par agent sur la même période. Le filtre d'agent est conservé ; une seule borne suffit et des bornes
  inversées sont remises dans l'ordre. Nouvelle vue `personnel:absence_pdf` (`absences/imprimer/`) et gabarit
  `personnel/pdf/absences_periode.html` (socle PDF commun).
- **« Toutes les matières »** dans le champ *Matière* de la saisie : au primaire, un seul enseignant dispense toutes
  les disciplines de sa classe. La case enregistre `AbsencePersonnel.toutes_matieres` (migration `personnel/0019`) et
  laisse la matière vide ; la liste et le PDF affichent « Toutes les matières ».
- Le bilan de la liste est désormais borné à la période affichée (mois ou intervalle) ; l'historique d'un agent
  choisi sans bornes reste complet, comme auparavant.

## 5.58.0 — 2026-11-05

- **Saisie des absences quotidiennes des professeurs alignée sur le formulaire de référence.** Le formulaire reprend
  exactement ses champs et son ordre : année scolaire (rappel, lecture seule), **date**, **au** (facultatif),
  **nom du professeur**, **classe**, **matière**, **heure de début**, **heure de fin**, **nombre d'heures** (calculé,
  deux décimales) et **observation** en liste déroulante **obligatoire** avec le bouton **＋ Ajouter** à sa droite.
- `AbsencePersonnel` gagne `classe`, `matiere`, `heure_debut`, `heure_fin` (tous facultatifs) et la propriété
  `nombre_heures` — migration `personnel/0018`. Les absences déjà enregistrées restent valides.
- **Contrôles** : observation obligatoire (« Sélectionnez obligatoirement une observation. »), date de fin
  postérieure ou égale à la date, heure de fin postérieure à l'heure de début. Le motif reste facultatif : il est
  déduit de l'observation choisie quand il n'est pas précisé.
- La liste du mois affiche désormais la **séance** (classe · matière · horaire), le nombre d'**heures** et
  l'**observation**.

## 5.57.0 — 2026-11-04

- **Saisie des absences du personnel : cycle et observations en listes déroulantes.** Le formulaire *Nouvelle
  absence* (primaire comme post-primaire / secondaire) commence par un champ **Cycle** lié à la table `Cycle` de
  l'établissement ; le choix recharge la page et **restreint la liste des agents** à ceux qui enseignent dans ce
  cycle. « Tous les cycles » reste possible.
- **Champ Observation en liste déroulante**, alimenté par les observations de l'école et les observations communes
  (`Raison de santé`, `Congé annuel`, `Congé de maternité`, `Permission exceptionnelle`, `Formation / mission`,
  `Absence non justifiée`, `Autre`, posées à l'installation). Une absence déjà enregistrée avec une observation
  hors liste reste éditable.
- **Bouton « ＋ Ajouter »** à côté du champ Observation : ouvre une page courte qui crée l'observation manquante,
  puis revient au formulaire d'absence avec la valeur déjà sélectionnée. Nouvelle table `ObservationAbsence`
  (observation commune ou propre à l'établissement, unique par école) — migration `personnel/0017` avec amorçage.
- Aucune donnée existante modifiée : `AbsencePersonnel` garde ses colonnes, le texte de l'observation est
  simplement choisi dans la liste.
- Guide d'utilisation §9.33.

## 5.56.0 — 2026-11-04

- **Le titulaire de la classe signe le bulletin comme la direction, et son suppléant aussi.** Dans une même
  classe, l'enseignant **titulaire** et son **suppléant** sont tous deux signataires des bulletins de notes,
  aux côtés du signataire paramétré du cycle.
- `MembrePersonnel.qualite_affectation` (`TITULAIRE` par défaut / `SUPPLEANT`) : la fenêtre *Ajouter un membre*
  et *Modifier le membre* proposent la **qualité** juste sous la classe d'affectation ; laissée vide, elle vaut
  *Titulaire* (aucune saisie existante n'est invalidée).
- `Classe.enseignant_titulaire` et `Classe.enseignant_suppleant` (premier agent **actif** de chaque qualité).
- Nouveau bloc `{% signataires_classe %}` : le bulletin trimestriel et le bulletin annuel affichent jusqu'à
  **trois signatures** — enseignant titulaire, enseignant suppléant, direction — dans une grille à quatre colonnes
  (code QR compris). La **liste alphabétique** reste signée par le titulaire et la direction.
- Grille resserrée uniquement quand deux enseignants de classe signent (police et espace de signature réduits) :
  le bulletin **tient toujours sur une page**, vérifié sur le pire cas (16 matières, mentions, honorifiques,
  signature scannée, duplicata).
- Migration `personnel/0016` (une colonne). Guide §5.1 et §24.2.

## 5.55.0 — 2026-11-04

- **Classe d'affectation de l'enseignant.** La fenêtre **Ajouter un membre** (et *Modifier le membre*) propose,
  dans la section *Cycles d'enseignement*, le choix de la **classe dont l'agent est titulaire** — la liste est
  limitée aux classes de l'établissement choisi et une classe d'un autre établissement est refusée.
  `MembrePersonnel.classe_affectation` (facultatif, `SET_NULL` : la classe survit au départ de l'agent).
- **Le titulaire signe les bulletins de notes et la liste alphabétique de sa classe.** Nouveau bloc de signature
  `{% signataire_classe %}` : fonction « L'Enseignant titulaire », nom de l'agent, date et lieu, signature scannée
  s'il en possède une. Il est apposé sur le **bulletin trimestriel**, le **bulletin annuel** (grille à trois
  colonnes : code QR, titulaire, signataire du cycle) et la **liste alphabétique** (titulaire à gauche, signataire
  du cycle à droite).
- **Repli inchangé** : sans classe d'affectation, ou si l'agent est désactivé, les documents sont signés
  exactement comme avant (signataire paramétré par cycle × type × année) ; la liste globale des élèves (toutes
  classes) ne porte pas de bloc titulaire. La fiche du personnel affiche la classe d'affectation et rappelle ce
  qu'elle implique.
- Migration `personnel/0015` (une colonne, aucun pointage ni fiche perdue).
- Guide d'utilisation : §5.1 (fiche du personnel) et §24.2 (signataires des documents).

## 5.54.0 — 2026-11-04

- **Pointage en deux plages : matin et après-midi.** Un enseignant qui a cours de 9h00 à 11h00 puis de 15h00 à
  17h00 pointe désormais **quatre heures** — arrivée et départ du matin, arrivée et départ de l'après-midi —
  au lieu d'une arrivée et d'un départ uniques qui comptaient la coupure de midi comme du travail.
- `PointagePersonnel` : `heure_arrivee_apres_midi` et `heure_depart_apres_midi` ; `heures_matin`, `heures_apres_midi`,
  `heures_travaillees` (somme des deux plages), `heure_arrivee_effective` (première arrivée) et
  `heure_depart_effective` (dernier départ).
- **Plages libres, réglées au jour le jour** : une plage sans cours reste vide et **n'est pas comptée comme une
  absence** ; seule la présence renseignée est mesurée (l'exemple ci-dessus donne 4 h 10, et non 8 h 10).
- Statut : le retard s'apprécie sur la **première arrivée** de la journée (matin, sinon après-midi) comparée à
  l'heure limite propre à l'agent ; le **départ anticipé** s'apprécie sur le **dernier départ**.
- **Page *Pointage du jour*** : en-têtes groupés *Matin* / *Après-midi* (quatre champs horaires) et colonne
  *Total* du jour par agent ; feuille du mois et PDF signé inchangés côté calcul (les heures sont la somme).
- Migration `personnel/0014` (deux colonnes ajoutées ; libellés des deux colonnes existantes précisés
  « (matin) ») — aucune donnée modifiée, aucun pointage existant perdu.

## 5.53.1 — 2026-11-04

- **Mise à jour d'une copie de production dont l'historique local a divergé de `main`.** Sur
  `C:\YELEN-SCHOOL`, `mettre-a-jour.bat` s'arrêtait sur `fatal: Not possible to fast-forward` puis affichait
  « Des fichiers ont été modifiés localement », message trompeur : la copie de production était restée sur un
  commit réécrit côté éditeur (amendement), donc l'avance rapide était impossible alors que l'arbre de travail
  était propre. Le script **réaligne désormais la copie de production sur `main`** (`git reset --hard FETCH_HEAD`)
  après la sauvegarde et après avoir vérifié qu'aucun fichier suivi n'est modifié ; s'il en reste, il s'arrête en
  nommant les fichiers et la commande à lancer. Aucune donnée n'est touchée : `.env`, `backups/` et `media/` ne
  sont pas versionnés.
- Guide de déploiement : procédure manuelle et tableau de dépannage complétés (§8.3 et §8.6).

## 5.53.0 — 2026-11-04

- **Pointage : horaires propres à chaque agent et à chaque profil.** Un enseignant qui commence à 9h00 et finit à
  11h00 n'a plus la même heure limite d'arrivée ni la même heure de départ qu'un agent d'administration.
  Trois niveaux, du plus général au plus précis — **établissement → profil (enseignant / administration) → agent** :
  une valeur vide hérite du niveau supérieur, une valeur saisie prime.
- **`MembrePersonnel`** : `profil_pointage` (ENSEIGNANT / ADMINISTRATION, déduit du titre à la création),
  `heure_arrivee_limite` et `heure_depart_normale` (facultatifs, propres à l'agent) ; accesseurs
  `heure_limite_pointage(reglage)` et `heure_depart_pointage(reglage)`.
- **`ReglagePointage`** : `heure_arrivee_limite_enseignant`, `heure_arrivee_limite_administration`,
  `heure_depart_normale`, `heure_depart_normale_enseignant`, `heure_depart_normale_administration` ; méthodes
  `limite_pour(profil)` et `depart_pour(profil)`.
- **Page *Pointage du jour*** : bloc *Horaires de référence* (six champs), colonnes *Limite d'arrivée* et
  *Départ prévu* éditables par agent, bouton *Enregistrer les horaires individuels* ; le statut retenu est calculé
  sur la limite de l'agent, un départ antérieur à son heure normale est signalé **Départ anticipé**.
- **Feuille du mois et PDF signé** : nouvelle colonne *Départs anticipés* (par agent et en total).
- **Fiche du personnel** : champs *Profil de pointage*, *Heure limite d'arrivée* et *Heure normale de départ*.
- Migration `personnel/0013` (colonnes ajoutées + classement automatique des fiches dont le titre désigne un
  enseignant). L'ancien bouton *Enregistrer la limite* reste accepté.

## 5.52.6 — 2026-11-04

- **Guide de déploiement Windows en PDF éditorial prêt à imprimer** (`docs/GUIDE_DEPLOIEMENT_WINDOWS.pdf`,
  71 pages A4, 1,4 Mo) : couverture marine et or, fiche documentaire, mode d'emploi, avant-propos présenté en
  tableau de synthèse, sommaire paginé en 6 parties, **3 schémas vectoriels** (architecture des cinq conteneurs,
  cycle de vie d'une sauvegarde, mise à jour en un clic), 11 chapitres et leur annexe de règles essentielles.
- **Moteur de composition généralisé** : `scripts/md_vers_pdf.py` s'appuie désormais sur un dossier
  documentaire (`scripts/guide_pdf/documents.py`) qui décrit couverture, fiche, parties, schémas et page de
  clôture de chaque guide. Les deux PDF se régénèrent avec `python scripts/md_vers_pdf.py utilisation` et
  `python scripts/md_vers_pdf.py deploiement`.
- **Correctifs de composition** relevés en relecture des épreuves :
  - listes numérotées interrompues par un bloc de code indenté (les points suivants repartaient dans une nouvelle
    liste, hors du cadre) — continuations réindentées, blocs rétrogradés en jetons puis réinjectés ;
  - étiquettes d'encadrés laissant la phrase commencer en minuscule ;
  - dernière page liminaire produisant une page blanche ;
  - en-têtes de page repliés sur quatre lignes pour les titres de chapitre longs.
- Guides `.docx` régénérés ; versions alignées sur `5.52.6` (`VERSION`, en-têtes des deux guides).

## 5.52.5 — 2026-11-04

- `lxml` porté de 6.0.2 à **6.1.0** (correction de la vulnérabilité PYSEC-2026-87 relevée par `pip-audit`
  dans la CI) ; aucune autre modification.

## 5.52.4 — 2026-11-04

- **Guide d'utilisation en PDF éditorial, prêt à imprimer** (`docs/GUIDE_UTILISATION_YELEN_SCHOOL.pdf`,
  268 pages A4, 8,4 Mo) :
  - couverture marine et or, fiche documentaire, mode d'emploi du manuel, sommaire paginé en 8 parties,
    index des 17 figures, ouvertures de partie, 40 chapitres avec chapeau et renvois de sections, page de clôture ;
  - composition typographique : Inter (titres et texte), Source Serif 4 (titres de chapitre, exergues),
    JetBrains Mono (commandes et arborescences) — polices embarquées ;
  - encadrés normalisés (astuce, avertissement, accès, règle de sécurité) avec pictogrammes vectoriels,
    tableaux à en-tête marine, captures d'écran en figures numérotées et légendées ;
  - en-têtes et pieds de page symétriques (titre du guide / chapitre courant, folio, édition et date),
    signets de navigation sur deux niveaux, métadonnées du document ;
  - **numérotation en deux passes** : les renvois du sommaire indiquent la page imprimée du corps
    (le folio du corps repart de 1 après les pages liminaires).
- Outil de production : `scripts/md_vers_pdf.py` + `scripts/guide_pdf/` (feuille de style éditoriale et polices).
  Dépendances de développement ajoutées : `beautifulsoup4`, `lxml`.

## 5.52.3 — 2026-11-04

- **Pré-inscription : le nom du parent arrive dans « Nom du père », plus dans « Nom du tuteur ».**
  À la conversion d'une demande en élève, `PreInscription.parent_nom` (« Parent / tuteur ») alimentait
  `Eleve.tuteur_nom` : la fiche s'ouvrait avec un tuteur renseigné et le père vide.
  - **Conversion** (`inscriptions.preinscriptions.inscrire`) : le nom du parent est désormais écrit dans
    `nom_pere` ; `tuteur_nom` reste vide jusqu'à ce que l'école désigne un tuteur.
  - **Élèves déjà convertis** : le formulaire de modification (`/inscriptions/eleve/<id>/modifier/`) présente
    automatiquement le tuteur enregistré dans **Nom du père** et laisse **Nom du tuteur** vide
    (`_initial_depuis_preinscription`) ; l'enregistrement reporte la valeur au bon endroit. La reprise ne vaut que
    pour un élève issu d'une pré-inscription dont `nom_pere` est vide — aucune autre fiche n'est touchée.
- Guides : `docs/GUIDE_UTILISATION_YELEN_SCHOOL.md` §9.31 et §40.1.
- Tests : `inscriptions/tests/test_sante_preinscriptions.py` (+2 tests, 1 assertion mise à jour).

## 5.52.2 — 2026-11-04

- **Guide d'utilisation : captures d'écran régénérées et exemples de saisie.** Vérification de
  `docs/GUIDE_UTILISATION_YELEN_SCHOOL.md` contre l'application réelle (jeu de démonstration, navigateur Chromium).
  - **15 captures réelles** (contre 10, dont plusieurs antérieures à 5.46) : les 10 existantes sont reprises sur la
    version courante et cinq écrans récents sont ajoutés — *Comptes élèves en masse* (5.49.0), *Prêts et retards*
    (5.50.0), *Pointage du jour* (5.51.0), *Évaluations annuelles* (5.51.0) et *Configuration SMS* avec la réception
    filtrée (5.52.0). Légendes réécrites (§33), sommaire complété.
  - **Nouvelle section §40 « Exemples de saisie, champ par champ »** : sept formulaires courants (élève, personnel,
    encaissement, manuel et prêt, pointage, entretien annuel, configuration SMS) avec une valeur d'exemple réaliste
    et la règle appliquée par chaque champ.
  - **§3.13** : le jeu de démonstration annonce désormais son contenu 5.50 à 5.52 (pointages, évaluations annuelles,
    prêts d'ouvrages) — il sert de base aux captures.
- **Jeu de démonstration enrichi** (`charger_demo`) : trois semaines de pointage des 8 agents (présences, retards,
  absences), un entretien annuel par agent et trois prêts d'ouvrages dont deux échus. Contrôlé par un test
  (`core/tests/test_demo.py`).
- **Correctif d'affichage** : les classes utilitaires `.align-end` et `.align-items-end` étaient utilisées par
  seize gabarits sans être définies dans `yelen.css` — les barres de filtres concernées n'étaient pas alignées
  (visible sur *Pointage du jour*). Ajout des deux règles (alignement bas).
- Guides : `docs/GUIDE_UTILISATION_YELEN_SCHOOL.md` (§3.13, §33, §40) et sa version Word régénérée.
- Tests : `core/tests/test_demo.py` (+1 test).

## 5.52.1 — 2026-11-04

- **Guide de déploiement Windows remis à niveau (5.52.1).** Vérification complète contre le dépôt et la
  production, puis mise à jour de `docs/GUIDE_DEPLOIEMENT_WINDOWS.md` (et de sa version Word).
  - **Cinq conteneurs** : le tableau de §1.1 décrivait encore `web`, `db` et `redis` ; il documente désormais
    `sms` (réception des SMS, `sms_recus --boucle`, ajouté en 5.46) et `proxy` (Caddy, profil `https`), avec les
    ports publiés et les **sept** volumes Docker à ne jamais supprimer.
  - **Référence complète du `.env`** (§3.2) : 30 lignes de variables — Django, base, ports, HTTPS, licence,
    image, jeton Git, passerelle SMS, `SMS_RECEPTION_FILTREE` (5.52.0), alertes, sauvegardes, CinetPay, MinIO,
    e-mails — avec la valeur attendue en production et les variables écrites automatiquement par les scripts.
  - **Nouvelle §4.4 « Où sont les journaux »** : les dix journaux de `logs\` et `backups\` avec le script qui les
    écrit, plus la distinction avec les journaux Django du volume `yelen_logs`.
  - **Nouvelle §6.7 « Réception des SMS des parents (conteneur `sms`) »** : état, redémarrage, contrôle de la
    carte *Réception des SMS* (relève de moins de 15 s), interrupteur de réception filtrée, diagnostic.
  - **Nouvelle §8.5 « Après chaque mise à jour : trois contrôles »** : `/health/` comparé à `VERSION`, état des
    conteneurs, recette de deux minutes ; rappel que migrations et fichiers statiques passent par `entrypoint.sh`.
  - **Dépannage** : trois entrées ajoutées (§10) — service `sms` arrêté, parent sans réponse à cause de la
    réception filtrée, page ou PDF sans mise en forme après une mise à jour.
  - En-tête, sommaire, §3.4 (« trois services » → cinq conteneurs) et §4.1 (journaux `web` et `sms`) alignés.

## 5.52.0 — 2026-11-04

- **Réception filtrée des SMS : n'accepter que les numéros enregistrés sur la plateforme.** Nouveau réglage
  `SMS_RECEPTION_FILTREE`, interrupteur **N'accepter que les SMS des numéros enregistrés** de
  `Paramètres → Configuration SMS` (désactivé par défaut, appliqué sans redémarrage).
  - **Numéros reconnus** : père / mère, tuteur et urgence des fiches élèves, téléphone des fiches du personnel,
    téléphone des comptes utilisateurs et `MASTER_SMS_NUMBERS` — comparaison sur les huit derniers chiffres, donc
    indifférente au format (`70 11 22 33` = `+22670112233`).
  - **Expéditeur hors périmètre** : journalisé sous le nouveau type `REFUSE` (migration `communication/0008`),
    **sans réponse automatique** (aucun SMS facturé), invisible dans *Messages libres* et dans la pastille des
    non-lus, consultable dans **Communication → Messages reçus → Numéros inconnus** avec le badge *Numéro non
    enregistré*. Le webhook répond `ignored` : le téléphone passerelle ne rejoue pas le message.
  - Les numéros enregistrés sont mémorisés 10 minutes (`sms_recus.numeros_enregistres`) : la relève ne relit pas
    les fiches à chaque SMS.
- Guides : `docs/GUIDE_UTILISATION_YELEN_SCHOOL.md` § 32.6 bis ; `.env.example` documente la variable.
- Tests : `communication/tests/test_reception_filtree.py` (9 tests).

## 5.51.1 — 2026-11-04

- **Vue consolidée du réseau — le bouton *Tableau de bord* était inaccessible.** Il occupait la douzième et dernière
  colonne du tableau, au-delà de onze colonnes de chiffres : il fallait faire défiler le tableau horizontalement
  pour l'atteindre, et il restait hors écran en dessous de 1 400 px. Le lien est désormais placé dans la **première
  colonne**, sous le nom du site — visible dès l'ouverture de la page, sans défilement — et la colonne d'action
  devenue vide est supprimée (en-tête, corps et pied de tableau restent cohérents à 11 colonnes).
- Tests : `etablissements/tests/test_reseau.py` (1 test de non-régression).

## 5.51.0 — 2026-11-04

- **Pointage du personnel et entretien annuel d'évaluation (audit P2-14).** Dernier chantier de l'audit : le suivi
  des présences quotidiennes des agents et leur évaluation annuelle, avec documents signés.
  - **Modèles** (migration `personnel/0012`) : `ReglagePointage` (une ligne par établissement, heure d'arrivée limite,
    07:30 par défaut, au-delà de laquelle le pointage est compté en retard), `PointagePersonnel` (arrivée, départ,
    statut *Présent / En retard / Absent / En congé*, observation, `heures_travaillees`, un pointage par agent et par
    jour) et `EvaluationAnnuelle` (cinq critères notés de 0 à 5 — ponctualité, compétence, qualité, relations,
    initiative —, bilan, objectifs, avis *favorable / avec réserves / défavorable*, `total_points` et
    `moyenne_sur_20`, une évaluation par agent et par année scolaire).
  - **Page `Personnel → Pointage`** (`/personnel/pointage/`) : journée sélectionnable, une ligne par agent actif avec
    arrivée, départ, statut et observation, enregistrement en une passe ; les lignes laissées vides ne sont pas
    enregistrées et le statut est déduit automatiquement de l'heure limite (modifiable depuis la page).
  - **Page `Personnel → Pointage du mois`** (`/personnel/pointage/mois/`) : jours pointés, heures, retards, absences
    et congés par agent, totaux, navigation mois précédent / suivant et **feuille de pointage en PDF** (A4 signé,
    `pointage_mois_pdf`).
  - **Page `Personnel → Évaluations annuelles`** (`/personnel/evaluations/`) : évaluations de l'année scolaire choisie,
    liste des agents restant à évaluer, saisie de l'entretien (grille de notes 0 à 5, bilan, objectifs, avis, contrôle
    des bornes et du doublon), **compte rendu en PDF** (A4 signé, `evaluation_pdf`) et suppression d'une saisie erronée.
  - **Signature** : deux nouveaux documents signables (migration `parametres/0047`) — `FEUILLE_POINTAGE` et
    `EVALUATION_PERSONNEL`, qui héritent du signataire déjà configuré pour la catégorie *Personnel*.
  - **Droits** : fonctionnalités *Pointage du personnel* (action *Pointer les arrivées et départs*) et *Évaluations
    annuelles* (actions *Saisir un entretien annuel*, *Supprimer une évaluation*), entrées du menu latéral rangées
    par ordre alphabétique.
- Guides : `docs/GUIDE_UTILISATION_YELEN_SCHOOL.md` § 5.5 et § 5.6 ; `docs/GUIDE_DEMARRAGE_RAPIDE.md` § 5 bis et § 7.
- Tests : `personnel/test_pointage_evaluations.py` (12 tests).

## 5.50.0 — 2026-11-04

- **Prêts d'ouvrages et retards de la bibliothèque (audit P2-13).** Le circuit d'attribution des manuels gagne son
  échéance et sa relance, côté école comme côté familles.
  - **Modèle** : `AttributionManuel.date_retour_prevue` (échéance fixée à la sortie, facultative) et
    `derniere_relance_le`, avec `est_en_retard` / `jours_de_retard` (migration `manuels/0003`). Le formulaire
    d'attribution accepte l'échéance.
  - **Page `Manuels → Prêts et retards`** (`/manuels/prets/`) : prêts en cours triés par échéance, filtres
    *En retard* / *À rendre sous 7 jours*, compteurs, pagination à 50, relance groupée des prêts cochés et
    **liste des retards en PDF** (A4 signé, `prets_retards_pdf`).
  - **Relance** : `core.notifications.notifier_pret_retard` avise le compte élève et les comptes parents dans leur
    portail (notification in-app + push), envoie le SMS au numéro de la famille si les SMS sont activés (nouveau
    modèle de message `PRET`, personnalisable) et date la relance.
  - **Relance automatique quotidienne** : nouveau déclencheur `PRETS_RETARD` de `Paramètres → SMS automatiques`
    (commande `sms_auto`, migration `parametres/0046`) — une relance par prêt au plus tous les 3 jours (champ
    « jours avant »), jamais deux le même jour, jamais pour un ouvrage rendu.
  - **Portail** : section *Ouvrages à rendre* de la vie scolaire (parent et élève) — ouvrage, code, échéance et
    jours de retard (`core.portail.prets_en_cours`).
  - **Droits** : fonctionnalité *Manuels scolaires › Prêts et retards* avec l'action *Relancer les familles*.
- Guides : `docs/GUIDE_UTILISATION_YELEN_SCHOOL.md` § 26.4 et § 26.5 bis ; `docs/GUIDE_DEMARRAGE_RAPIDE.md` § 7 et § 8.
- Tests : `manuels/test_prets.py` (8 tests).

## 5.49.0 — 2026-11-03

- **Portail élève au niveau du portail parent (audit P2-12).**
  - **Comptes élèves en masse** : nouvelle page `Utilisateurs → Comptes élèves en masse`
    (`/accounts/utilisateurs/eleves/masse/`) qui liste les élèves inscrits de l'année dépourvus de compte actif et
    crée en une fois un compte ELEVE par élève coché, **identifiant = le matricule** (inscrit au dos de la carte
    scolaire), mot de passe provisoire de 12 caractères, SMS d'accueil au numéro du parent si les SMS sont activés,
    récapitulatif imprimable (mots de passe affichés une seule fois). Service : `accounts/parents_masse.py`
    (`eleves_sans_compte`, `creer_comptes_eleves`, `message_sms_eleve`, domaine technique `eleve.invalid`) ;
    la connexion accepte le **matricule** comme identifiant (`email_depuis_identifiant`, insensible à la casse).
  - **Notifications de l'élève** : `Notification` reçoit la valeur `DOCUMENT` (migration `core/0010`) ; les avis
    d'**absence**, de **retard**, de **sanction**, de **bulletin publié** et de **document délivré** parviennent
    désormais aussi au compte élève, avec le lien de son propre portail ; `core/push.py` ouvre le portail élève pour
    un destinataire ELEVE (`page_notifications`, `charge_utile`).
  - **Documents délivrés** : `documents/archivage.py::archiver_pdf_document` archive le PDF (certificat, attestation,
    convocation) puis prévient la famille dans son portail (`notifier_document_delivre`).
  - **Carte scolaire dans le portail** : `core:portail_eleve_carte` / `core:portail_parent_carte` téléchargent la
    carte scolaire en PDF (pièce d'entrée portant le matricule) pour l'élève lui-même ou ses parents ;
    `inscriptions/views/documents.py` expose `contexte_carte_scolaire` et `pdf_carte_scolaire` partagés avec l'écran
    d'administration.
  - **PWA élève** : raccourcis « Mes bulletins » / « Ma vie scolaire » dans `/manifest-eleve.json` et pages du
    portail pré-cachées par `/sw-eleve.js` pour l'accès hors réseau.
  - **API REST** : `GET /api/eleves/<pk>/documents/` (documents délivrés, lien de téléchargement du portail, mêmes
    droits que le portail — soi-même pour un élève, ses enfants pour un parent).
- Guides : `docs/GUIDE_UTILISATION_YELEN_SCHOOL.md` § 9.23 (comptes en masse, connexion par numéro **ou matricule**)
  et § 19.6 (portail élève complet) ; `docs/GUIDE_DEMARRAGE_RAPIDE.md` § 4.4.
- Tests : `accounts/tests/test_eleves_masse.py`, `api/test_documents_portail.py`, compléments de
  `core/tests/test_portail_eleve.py` et `core/tests/test_push.py`.

## 5.48.1 — 2026-11-03

- **Allègement de `core/templates/core/base.html` (audit P1-8)** : extraction de la barre latérale vers
  `core/templates/core/partials/sidebar.html` (`base.html` passe de `1 223` à `433` lignes, `0` attribut
  `style=` inline).
- **Découpage rétrocompatible des 5 modules Python ≥ 1 000 lignes (audit P2-16b)** — `0` migration, `0`
  fichier applicatif `.py` ≥ 1 000 lignes :
  - `licences/models.py` (`1 350` l.) → `licences/models/` (`licence.py`, `activations_audit.py`, `__init__.py`
    + mise à jour de la vérification d'intégrité `licences/boot_check.py`).
  - `core/chatbot.py` (`1 116` l.) → `core/chatbot/` (`guide.py`, `requetes.py`, `__init__.py`).
  - `personnel/views.py` (`1 101` l.) → `personnel/views/` (`membres.py`, `paie_conges.py`, `__init__.py`).
  - `finances/models.py` (`1 025` l.) → `finances/models/` (`scolarite.py`, `gestion.py`, `__init__.py`).
  - `communication/views.py` (`1 000` l.) → `communication/views/` (`commun.py`, `messages.py`,
    `campagnes_recus.py`, `__init__.py`).
- Garde-fou statique permanent : `core/tests/test_architecture_modules.py`.

## 5.48.0 — 2026-11-03

- **Compteur d'usage anonyme par module dans *Exploitation* (audit P1-10).**
  - Nouveau module `core/usage.py` + modèle `core.UsageModuleQuotidien(date, module, appels)` (sans champ
    d'horodatage `BaseModel`, donc exclu de `AuditLog`) et middleware `UsageModuleMiddleware` : cumule en
    mémoire dans chaque processus les pages servies aux utilisateurs connectés (hors `/health/` et routes de
    rafraîchissement automatique) sans aucune donnée personnelle (ni utilisateur, ni IP, ni paramètres d'URL),
    puis reverse en base au plus une fois par minute afin d'éviter toute contention SQLite.
  - Nouvelle carte **Usage des modules (anonyme)** dans *Administration → Exploitation* (totaux et répartition
    par module sur 7 et 30 jours glissants, sans alerte supplémentaire).
- **Guide court de démarrage actualisé en 5.48.0 (audit P2-15)** : mise à niveau de
  `docs/GUIDE_DEMARRAGE_RAPIDE.md` (`/aide/demarrage/`) avec l'accès distant enseignant Tailscale, la clôture
  automatique des périodes d'évaluation, les boutons **Mise à jour en ligne** / **Mise à jour (`.zip`)**,
  l'essai trimestriel `tester-restauration.bat` et la carte d'usage des modules.
- Tests : `core/tests/test_usage_modules.py` + `core/tests/test_aide.py`.

## 5.47.9 — 2026-11-03

- **Correctif de la mise à jour en ligne (`Configuration → Mise à jour en ligne`).**
  - **Cause principale corrigée (`LogonType S4U` → `Interactive`)** : lorsque `mettre-a-jour.bat` était exécuté en
    Administrateur, `installer\register-update-agent-task.ps1` enregistrait la tâche `YELEN SCHOOL - Agent de mise a jour`
    en `LogonType S4U` (*« Ne pas stocker le mot de passe »*), mode dans lequel Windows bloque l'accès au Gestionnaire
    d'identification Windows (`CredRead` → `1312`) et au contexte Docker Desktop utilisateur ; `git fetch origin main`
    échouait alors sur le dépôt privé et retournait un faux message *« Dépôt GitHub injoignable »*. Désormais, la tâche
    est toujours enregistrée en `LogonType Interactive` et répare automatiquement toute ancienne inscription `S4U`.
  - **Fiabilisation Git / Docker sans fenêtre** (`appliquer-mise-a-jour-en-attente.ps1`, `mettre-a-jour.ps1`,
    `configure-firewall.ps1`, `Dockerfile`) : `GIT_TERMINAL_PROMPT=0` + `GCM_INTERACTIVE=never`, `safe.directory=*`
    en mémoire (`GIT_CONFIG_COUNT`), ajout automatique des chemins standards `Git` et `Docker` au `PATH`, relais
    optionnel de `YELEN_GITHUB_TOKEN` (`.env`) en mémoire sans écriture disque, écriture atomique à tentatives sur
    `mises-a-jour\demande.json`, diagnostic exact dans `logs\mise-a-jour.log`, désactivation de toute invite UAC
    bloquante en arrière-plan (`YELEN_UNATTENDED=1`), normalisation des seules différences CRLF/LF avant fusion et
    expiration propre dans l'interface si l'agent hôte ne répond pas (`core/mise_a_jour.py`).
- Documentation : guide de déploiement Windows (**§8.1**) et guide d'utilisation mis à jour.
- Tests : `installer/tests/test-agent-mise-a-jour.ps1` (exécuté en CI `pwsh`),
  `test_expiration_demande_bloquee_en_verification_ou_en_cours` (`core/tests/test_mise_a_jour.py`) et
  `test_agent_mise_a_jour_en_ligne_interactive_et_git_non_interactif` (`core/tests/test_scripts_windows.py`).

## 5.47.8 — 2026-11-03

- **Maintenance rapide (dépendances, performances `Redevables`, lanceur `tester-restauration.bat`).**
  - **Dépendances de production** : montée de `gunicorn` en `26.2.0` (`pip check` et `pip-audit` sans anomalie) et
    exclusion explicite de `python-dateutil >= 3.0.0` dans `.github/dependabot.yml` tant que `botocore` impose
    `python-dateutil<3.0.0,>=2.1`.
  - **Allègement et pagination de `finances:liste_redevables`** : pagination par lots de 50 élèves, filtre direct
    par classe (`?classe=`) repris à l'impression PDF, chargement de `HistoriqueRelance` limité aux élèves de la
    page courante et projection SQL `.only(...)` tout en conservant `nb_redevables` et `total_redevable` globaux
    exacts. Sur 1 500 élèves redevables (`manage.py mesure_reference`), la réponse passe de **397 ms / 2 176 Ko**
    à **170 ms / 137 Ko** (-94 % de poids HTML).
  - **Lanceur racine `tester-restauration.bat`** : relais direct vers `installer\tester-restauration.ps1` depuis
    `C:\YELEN-SCHOOL\tester-restauration.bat`, cité dans l'alerte et l'écran *Exploitation*.
- Documentation : guide d'utilisation (**§3.6**, **§9.8**) et guide de déploiement Windows (**§9.7**) mis à jour.
- Tests : `test_page_redevables_pagination_et_filtre_classe` (`finances/tests/test_views.py`) et
  `test_lanceur_tester_restauration` (`core/tests/test_scripts_windows.py`).

## 5.47.7 — 2026-11-03

- **Suppression de la fenêtre noire furtive des tâches planifiées Windows.** Sous Windows 10/11 (en particulier
  Windows 11 avec Windows Terminal par défaut), lancer directement `powershell.exe -WindowStyle Hidden` depuis
  le Planificateur de tâches alloue et affiche brièvement une fenêtre noire avant que PowerShell ne la masque
  (toutes les minutes pour *Agent de mise a jour*, toutes les 5 minutes pour *Surveillance et alerte SMS*, et
  lors des sauvegardes / SMS quotidiens). Désormais, les 8 scripts `installer\register-*-task.ps1` s'appuient
  sur `installer\yelen-scheduled-task.ps1` (`conhost.exe --headless`), qui attache PowerShell et ses processus
  enfants à une console sans fenêtre dès la création du processus, et `Update-YelenTasksHeadless` migre
  automatiquement sur place les tâches `YELEN SCHOOL - *` déjà enregistrées.
- Documentation : guide de déploiement Windows **§6.1** mis à jour.
- Tests : garde-fou `test_taches_planifiees_windows_sans_fenetre_noire` dans `core/tests/test_scripts_windows.py`
  sur l'ensemble des scripts `installer/register-*-task.ps1`.

## 5.47.6 — 2026-11-03

- **Bouton « Mise à jour en ligne » dans la rubrique Configuration.** Ajout du bouton **Mise à jour en ligne**
  dans la rubrique **Configuration** du menu latéral (et sur `/mise-a-jour/`), réservé aux rôles *Directeur*
  et *Super Admin*. Au clic :
  - si une nouvelle version est disponible sur la branche `main` du dépôt officiel, l'utilisateur reçoit le
    message *« Nouvelle version X.Y.Z disponible : la mise à jour commence. »*, l'opération est journalisée
    dans `AuditLog` et la mise à jour démarre automatiquement (sauvegarde chiffrée, reconstruction, `/health/`,
    retour arrière automatique) avec suivi en direct toutes les 3 s sur `/mise-a-jour/` ;
  - sinon, le message *« Il n'y a pas de mise à jour disponible (version actuelle : X.Y.Z). »* s'affiche sans
    redémarrage ni sauvegarde inutile.
- **Compatibilité dépôt privé sans configuration supplémentaire.** Si le conteneur ne dispose pas de
  `YELEN_GITHUB_TOKEN`, la vérification est relayée en quelques secondes à l'agent hôte Windows
  (`installer\appliquer-mise-a-jour-en-attente.ps1`), qui utilise les identifiants Git du serveur Windows
  sans jamais exposer `docker.sock`.
- Documentation : guide d'utilisation **§35.2** et guide de déploiement Windows **§8.1** mis à jour.
- Tests : 5 nouveaux tests dans `core/tests/test_mise_a_jour.py` (18 au total sur le module de mise à jour)
  + contrat `EN_LIGNE` dans `core/tests/test_scripts_windows.py`.

## 5.47.5 — 2026-11-03

- **Bouton « Mise à jour » par archive `.zip` dans la rubrique Configuration.** La direction (*Directeur* /
  *Super Admin*) dispose désormais d'un bouton **Mise à jour** dans la rubrique **Configuration** du menu
  latéral (ainsi que d'une carte dans *Paramètres*). Au clic, la boîte de sélection de fichier s'ouvre
  immédiatement filtrée sur `.zip` ; après choix de `yelen-school-<version>.zip`, le serveur vérifie en
  mémoire/flux l'absence de traversée de chemin, le plafond de taille (300 Mo), l'en-tête Git bundle,
  l'empreinte **SHA-256** et la progression de version avant toute écriture, consigne l'acte dans `AuditLog`
  et dépose atomiquement le bundle vérifié + `demande.json` dans `mises-a-jour/`.
- **Exécution automatique côté hôte Windows sans exposer `docker.sock` et suivi en direct.** Le conteneur
  `web` monte uniquement `./mises-a-jour:/app/mises-a-jour` ; côté Windows, l'agent planifié silencieux
  `installer\appliquer-mise-a-jour-en-attente.ps1` (enregistré par `start-local.ps1` et relayé par
  `surveiller-yelen.ps1`) valide le nom du bundle et l'empreinte, exécute `mettre-a-jour.ps1 -DepuisArchive`
  (sauvegarde chiffrée, reconstruction, `/health/`, retour arrière automatique) et met à jour `demande.json`
  relu toutes les 5 s en HTMX sur `/mise-a-jour/`.
- **Outil éditeur et CLI unifiés `.zip` / `.bundle`.** `installer\outils-editeur\creer-archive-mise-a-jour.ps1`
  génère désormais `yelen-school-<version>.zip` en plus du couple `.bundle` + `.sha256`, et
  `mettre-a-jour.bat -DepuisArchive` accepte indifféremment `.zip` ou `.bundle`.
- Documentation : guide d'utilisation **§35.2** et guide de déploiement Windows **§8.2** mis à jour.
- Tests : 13 nouveaux tests dans `core/tests/test_mise_a_jour.py` + contrat PowerShell/Docker dans
  `core/tests/test_scripts_windows.py`.

## 5.47.4 — 2026-11-03

- **Clôture automatique des périodes en fin de trimestre.** Tant que personne ne cliquait sur « Clôturer »
  dans *Paramètres → Périodes*, un trimestre échu restait ouvert en écriture : un enseignant pouvait encore
  saisir ou corriger des notes après l'impression des bulletins. Désormais, la saisie reste ouverte jusqu'à
  **23 h 59 le jour de la date de fin** de la période, puis le verrou s'applique **automatiquement** dès le
  lendemain côté serveur — sans tâche planifiée ni action manuelle (saisie en ligne et hors réseau, création
  et modification d'évaluations, import Excel, appréciations, compétences APC et recalcul des moyennes).
  Consultation, conseils de classe, bulletins et exports ne changent pas ; la clôture anticipée par la
  direction reste possible.
- **Dérogation temporaire réservée à la direction, motif obligatoire et journal intégré.** Rouvrir une
  période verrouillée exige désormais un **motif** saisi dans la modale de réouverture ; la liste *Périodes*
  affiche un badge ambre **Dérogation ouverte** tant qu'elle n'est pas refermée, ainsi que le dernier acte
  enregistré (`[JJ/MM/AAAA HH:MM] Réouverture par … : motif`, puis `Clôture par …`), et la modale restitue
  l'historique complet en complément de `AuditLog`. Une réouverture accordée *avant* la date de fin laisse
  le verrou automatique agir normalement à l'échéance ; la clôture d'une année scolaire referme toute
  dérogation restée ouverte.
- **Défense en profondeur et formulaire de période.** Modifier la date de fin d'une période déjà verrouillée
  exige le droit de clôture de la direction, et toute mise à jour des dates dans *Paramètres → Périodes*
  synchronise le trimestre pédagogique correspondant ; correction au passage de l'affichage des dates ISO et
  du bandeau d'erreur dans la modale `periode_form.html`.
- Documentation : guide d'utilisation **§3.4** mis à jour (clôture automatique, dérogation motivée,
  refermeture).
- Tests : 5 nouveaux tests de parcours dans `pedagogie/tests/test_cloture_automatique.py` (ouverture jusqu'au
  dernier jour puis blocage automatique le lendemain sur toutes les écritures, modale et motif obligatoire,
  journalisation ouverture/refermeture, refus hors direction et blocage du contournement par `date_fin`,
  maintien de la clôture automatique après réouverture anticipée, refermeture lors de la clôture d'année).

## 5.47.3 — 2026-11-02

- **Mise à jour sans Internet.** L'école ne pouvait se mettre à jour que par GitHub : une coupure de
  l'opérateur ou une panne de DNS (`Could not resolve host: github.com`) bloquait tout, la production
  restant sur sa version du moment. `mettre-a-jour.bat -DepuisArchive <archive>` applique désormais une
  archive de version fournie par l'éditeur, **sans réseau**.
- L'archive est un bundle git : elle emprunte **exactement le même chemin** que GitHub (`fetch` puis
  avance rapide), donc la sauvegarde préalable, le contrôle `/health/` et le **retour arrière automatique**
  restent inchangés. Aucune nouvelle logique de copie de fichiers à maintenir.
- **Empreinte SHA-256 obligatoire**, vérifiée *avant* la sauvegarde et avant toute écriture : archive
  absente, incomplète, altérée ou mal formée → arrêt immédiat, « rien n'a été modifié ». Puis
  `git bundle verify` contrôle que l'archive est bien une mise à jour YELEN SCHOOL applicable sur la
  version installée.
- Panne réseau : le message d'erreur indique maintenant la solution hors ligne au lieu de laisser
  l'administrateur devant « GitHub injoignable ».
- Nouvel outil éditeur `installer\outils-editeur\creer-archive-mise-a-jour.ps1` : produit
  `yelen-school-<version>.bundle` (26 Mo environ) et son `.sha256`, refuse un dépôt modifié, ne livre rien
  si `git bundle verify` échoue, et affiche les commandes à communiquer.
- Guide de déploiement **§8.2** (nouvelle section) : ce que reçoit l'école, les cinq refus prévus avec la
  cause et la conduite à tenir ; anciens §8.2 et §8.3 deviennent §8.3 et §8.4.
- Éprouvé de bout en bout : archive d'une version publiée appliquée sur un clone en 5.47.2 → 5.47.3 sans
  réseau, second passage « déjà à jour » sans effet, et cinq cas de refus (archive absente, empreinte
  absente, mal formée, incorrecte, bundle étranger).
- Tests : 3 garde-fous dans `core/tests/test_scripts_windows.py` — l'empreinte est vérifiée avant la
  sauvegarde et avant la fusion, le bundle utilise `git -C`, le chemin GitHub reste intact, et l'archive
  éditeur porte une empreinte au format `sha256sum`.

## 5.47.2 — 2026-11-02

- **Une sauvegarde jamais restaurée n'est pas une sauvegarde.** Nouveau `installer\tester-restauration.ps1` :
  il importe la dernière sauvegarde (chiffrée ou non) dans une base temporaire `<DB_NAME>_test_restauration`,
  vérifie le nombre de tables et les effectifs (élèves, inscriptions, paiements), puis supprime cette base.
  **La production n'est pas touchée** — l'application reste en marche, aucune donnée n'est remplacée.
  Le résultat est consigné dans `backups\restauration.log` et apparaît dans *Exploitation*, nouvelle carte
  **Restauration testée** ; sans essai depuis plus de 120 jours, une alerte y figure et le relais quotidien la reprend.
- **Surveillance extérieure documentée** (guide de déploiement §9.6) : les alertes de la veille sont internes,
  elles ne peuvent pas prévenir si le serveur est éteint. Procédure complète, pas à pas, avec deux services
  gratuits — UptimeRobot sur `/health/` (le serveur répond-il ?) et Healthchecks.io sur la sauvegarde
  (a-t-elle eu lieu ?), avec la commande `&& curl` à ajouter à la tâche planifiée.
- **Mesures de référence** (guide de déploiement §9.4/§9.6, audit P1-9) : commande `manage.py mesure_reference`
  qui chronomètre les six écrans du quotidien, sur les données réelles, et peut servir de garde-fou planifié
  (`--seuil-ms`, `--json`). Mesuré sur 1 500 élèves (SQLite, 5 passes, médiane) :

  | Écran | Durée | Requêtes SQL | Page |
  |---|---|---|---|
  | Accueil | 28 ms | 25 | 66 Ko |
  | Élèves | 43 ms | 13 | 225 Ko |
  | Évaluations (saisie des notes) | 91 ms | 15 | 148 Ko |
  | Redevables | 325 à 402 ms | 16 | 2 161 Ko |
  | Paiements | 29 ms | 10 | 165 Ko |
  | Bulletins | 10 ms | 12 | 59 Ko |

  La liste des redevables (2,1 Mo de HTML pour 1 500 lignes) est la plus lente et la plus variable : elle reste
  sous le seuil de 2 000 ms, mais c'est la page à paginer en premier si l'effectif double.
- Documentation : guide d'utilisation §3.6 (carte « Restauration testée »), guide de déploiement §9.6 et §9.7
  (procédure d'essai trimestriel avec sortie attendue et consignation).
- Tests : 11 nouveaux (lecture du journal de restauration, alertes d'absence et d'ancienneté, lignes
  illisibles, sortie tableau et JSON de la commande, seuil, utilisateur inconnu).

## 5.47.1 — 2026-11-02

- **Couverture des modules sensibles.** Les écrans qui engagent une décision (conseil de classe, transfert,
  dépense, licence, prédiction) étaient les moins testés. Couverture des vues, mesurée module par module :

  | Module | Avant | Après |
  |---|---|---|
  | `pedagogie/views/predictions.py` | 25 % | **100 %** |
  | `viescolaire/views/conseils.py` | 36 % | **100 %** |
  | `finances/views/budget.py` | 39 % | **100 %** |
  | `inscriptions/views/transferts.py` | 40 % | **98 %** |
  | `licences/views.py` | 57 % | **100 %** |

- Nouveaux tests de parcours (77 tests) : risque de décrochage (filtres, recalcul unitaire, recalcul global,
  fragment htmx, PDF), prédictions (cycles à examen, pronostics, calcul POST, PDF), conseils de classe
  (création sans les abandons, décisions et mentions, PV PDF), appels de décision (contestabilité, instruction,
  modification de la décision, verrouillage), budget (catégories, dépenses, refus de dépassement, séparation
  saisie / approbation, trésorerie, export Excel), transferts (demande, approbation qui clôt le dossier et
  trace le parcours, refus, dossier PDF), licences (création, activation par jeton, renouvellement, révocation,
  outils de développement désactivés en production).
- **Aucun code de production modifié** : les seules lignes non couvertes sont les replis « WeasyPrint absent »
  des transferts (`import` en échec). Deux comportements réels ont été figés au passage : le saisisseur ne
  valide pas sa propre dépense, une échéance réglée n'apparaît plus dans le reste à payer d'un transfert.

## 5.47.0 — 2026-11-02

- **Listes lisibles sur téléphone.** Les tableaux de liste (élèves, paiements, personnel, classes, reçus,
  redevables, commandes, documents…) n'imposent plus de défilement horizontal : **sous 768 px**, chaque ligne
  devient une carte — nom en tête, informations avec leur libellé de colonne, actions en bas. Mesures sur la
  liste des élèves à 390 px : tableau de **809 px dans 356 px visibles avant**, **356 px sans débordement
  après** ; paiements 941 px → 356 px ; personnel 860 px → 356 px. Sur ordinateur, aucun changement.
- Mécanique unique et réversible : `static/js/tableaux_mobile.js` reprend les libellés du `<thead>` (aucun
  gabarit de liste modifié), `static/css/yelen.css` met la ligne en carte. Sans JavaScript, le tableau reste
  défilant — aucune régression possible.
- **Exclusions** : les matrices (`table-stats`, `edt-table`) et les tableaux marqués `data-cartes="non"` — la
  matrice des bulletins par classe et par trimestre reste un tableau. À l'impression, les listes reprennent
  leur forme tabulaire.
- Guide §18.9 ; tests : 4 garde-fous statiques et un parcours navigateur à 390 px (cartes, libellés, titre
  unique, absence de débordement, matrice préservée).
- Vérifié sans modification : la **saisie de notes sur téléphone** est déjà adaptée (champ de 88 × 52 px,
  police 22,4 px, clavier décimal, boutons Absent / Dispensé, enregistrement hors réseau).

## 5.46.9 — 2026-11-01

- **Guide §9.5 : inscription des enseignants détaillée.** La clé se saisit **dans l'application**
  (écran de connexion → menu ⋯ → « Use an auth key »), jamais dans la page web ; l'application Windows n'a
  pas de champ clé (`tailscale up --authkey`). Ajout de deux consignes qui évitent une réinstallation :
  **ne jamais cocher *Ephemeral*** (l'appareil est supprimé à la première déconnexion) et **désactiver
  l'expiration de clé** de chaque appareil (180 jours par défaut, sinon déconnexion en pleine année scolaire).
- Tableau de lecture de la liste *Machines* : pas de badge = durable, **Éphémère** = à refaire, **Cheminée** =
  Funnel actif (uniquement sur le serveur) ; piste des **tags** pour une traçabilité stricte des appareils.
  Dépannage : fenêtre « Choisir une clé d'accès » (passkey) et appareil qui disparaît de la liste.

## 5.46.8 — 2026-11-01

- **Consigne de redémarrage contradictoire dans `activer-acces-distance.bat`.** Le lanceur affichait
  « Redemarrez le serveur (`demarrer-autonome.bat`) » après avoir imprimé, une ligne plus haut, la consigne
  propre au mode d'installation (`demarrage.bat` en Docker). En production Docker, suivre la seconde relançait
  le serveur autonome. Le lanceur renvoie désormais à la consigne affichée par le script, qui seule connaît le
  mode. Exemple d'entrée Tailscale Serve ajouté à son en-tête.

## 5.46.7 — 2026-11-01

- **Accès du personnel par Tailscale Serve, avec port.** `activer-acces-distance.bat` accepte désormais
  `-Domaine <serveur>.<tailnet>.ts.net:8443 -EnvSeulement` : le nom part dans `ALLOWED_HOSTS` **sans** le port
  et l'origine complète, port compris, dans `CSRF_TRUSTED_ORIGINS` — sans quoi chaque enregistrement de notes
  était refusé (`403 CSRF verification failed`). Port hors limites ou non numérique : refusé avant toute
  écriture. `-Desactiver` avec port ne retire que l'origine avec port : une entrée Funnel sur le 443 du même
  nom reste utilisable.
- Cas d'usage : **saisie des notes de fin de trimestre** par les enseignants, sur un canal privé (réseau
  Tailscale), sans plafond de débit et sans exposition publique ; les parents gardent le Funnel sur le 443.
- Guide de déploiement **§9.5** : deux configurations (personnel seul / les deux en parallèle), inscription des
  enseignants (offre gratuite : 3 utilisateurs, 100 appareils — un compte « école » et une clé
  d'authentification), restriction du tailnet à la machine du serveur, charge attendue, dépannage.
- Tests PowerShell de `activer-acces-distance.ps1` : section « Port Tailscale Serve » (11 vérifications
  supplémentaires).

## 5.46.6 — 2026-11-01

- **Messages reçus : lisibles sur téléphone.** La boîte n'est plus un tableau de sept colonnes à défilement
  horizontal : chaque SMS occupe une carte pleine largeur (numéro et date en tête, famille identifiée,
  texte complet, badges compacts, actions sous le message). Sur téléphone la colonne « Message » tombait à
  **un caractère par ligne** (tableau de 934 px dans 356 px visibles, lignes de 235 px) ; le message occupe
  désormais 311 px de large et les cartes s'empilent sans défilement latéral. Sur ordinateur, le texte passe
  de 158 px à 1024 px, les trois actions de chaque message tiennent sur une ligne alignée à droite et le
  badge « Message libre » n'est plus répété quand la vue ne contient que des messages libres.
- Guide d'utilisation §32.6 : présentation en cartes décrite ; test de non-régression sur la structure de la
  liste (une carte par message, aucun tableau à défilement).

## 5.46.5 — 2026-11-01

- **Consigne de redémarrage corrigée** : `demarrer.bat` n'existe pas — le lanceur Docker est **`demarrage.bat`**
  (`demarrer-autonome.bat` ne concerne que le mode sans Docker). Corrigé dans le script d'accès à distance, les
  deux guides et le journal ; un test interdit désormais qu'un document cite un lanceur absent de la racine.
- Guide de déploiement §9.4 : Tailscale Funnel présenté comme **mode recommandé sans domaine**, avec les
  vérifications (`tailscale funnel status`, `/health/` local) et le rappel du redémarrage obligatoire après
  modification du `.env` (sinon `400 Bad Request`).
- Mise en service réelle le 01/11/2026 : portail parents joignable en 4G et en Wi-Fi via `https://<serveur>.<tailnet>.ts.net`.

## 5.46.4 — 2026-11-01

- **Accès à distance sans nom de domaine.** `activer-acces-distance.bat -Domaine <nom> -EnvSeulement` autorise
  seulement le nom public dans `.env` (`ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `ACCES_DISTANCE_DOMAINE`) sans
  installer de service Cloudflare : utilisable avec un accès assuré autrement — procédure **Tailscale Funnel**
  ajoutée au guide de déploiement §9.4, pour les cas où le domaine appartient à un compte Cloudflare
  inaccessible (zone « Serveurs de noms invalides »). Tests PowerShell : 36 vérifications.

## 5.46.3 — 2026-11-01

- **Parcours navigateur : plus d'échec intermittent « 500 » sur les pages lourdes.** La base de test d'un
  SQLite Django est `file:memorydb_default?mode=memory&cache=shared` : en mémoire **partagée**, SQLite verrouille
  au niveau de la **table** et non de la base. Deux requêtes simultanées — une page et les compteurs htmx
  qu'elle déclenche (`/notifications/badge/`, `/communication/messages-recus/compteur/`) — se bloquent donc sur
  `django_session`, avec `database table is locked` : `busy_timeout` n'y change rien (code SQLITE_LOCKED, pas
  SQLITE_BUSY). Reproduit hors navigateur : la même lecture réussit sur fichier + WAL, échoue en mémoire
  partagée. Les parcours utilisent désormais une base de test **sur fichier** (`core/tests/e2e/test_parcours.py`,
  via `django_db_modify_db_settings`), comme la production : trois exécutions consécutives vertes.
- **Sans effet en production** : une école utilise un fichier SQLite en WAL (`core/db_sqlite.py`) ; la mémoire
  partagée n'existe que dans les tests. Les 500 observés en CI n'ont jamais concerné les utilisateurs.

## 5.46.2 — 2026-11-01

- **Le contrôle de l'adresse publique ne confond plus un autre site avec YELEN.** `Test-PointDeSante` lisait
  le seul code HTTP : une page étrangère répondant 200 (page générique du domaine, `*.domaine`) était annoncée
  « [OK] ». Le script exige désormais le contenu de `/health/` (`"status"`) et distingue trois états : YELEN
  répond, **un autre site répond** (message rouge + consigne du tunnel), rien ne répond. Même exigence sur le
  port local, pour repérer un port occupé par une autre application. Tests PowerShell : 31 vérifications.

## 5.46.1 — 2026-11-01

- **Accès à distance sur une installation Docker.** `activer-acces-distance.ps1` reconnaît le mode de
  déploiement : si le conteneur `web` tourne (`docker compose … ps -q web`), il lit le port dans
  `YELEN_HTTP_PORT` et demande de relancer par **`demarrage.bat`** — les conteneurs doivent être recréés pour
  relire `.env`, un simple redémarrage ne suffit pas. En mode autonome, rien ne change (`PORT`,
  `demarrer-autonome.bat`). Guide de déploiement §9.4 complété (redémarrage selon le mode).

## 5.46.0 — 2026-11-01

- **Accès à distance du portail parents.** Nouveau `activer-acces-distance.bat` et
  `installer/activer-acces-distance.ps1` : le serveur publie le portail parents sur
  `https://yelenschoola.nayxus.com/` par un **tunnel Cloudflare sortant** — aucun port ouvert sur la box,
  HTTPS et certificat fournis, base de données jamais exposée. Le script installe `cloudflared` au besoin,
  autorise le nom public dans `.env` (`ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `ACCES_DISTANCE_DOMAINE`),
  installe le service Windows avec le jeton du tunnel (jamais écrit dans un fichier), puis contrôle
  `/health/` en local et sur l'adresse publique. `-Desactiver` referme l'accès ; relancer est sans effet
  de bord.
- **Correctif : le serveur autonome ignorait `.env`.** `demarrer-autonome.bat` lance `waitress-serve
  yelen_school.wsgi`, qui ne passe pas par `manage.py` : `SECRET_KEY`, `ALLOWED_HOSTS` et
  `CSRF_TRUSTED_ORIGINS` n'étaient pas lus (clé régénérée à chaque démarrage, donc sessions perdues ;
  nom public refusé en 400). Le lanceur charge désormais `.env` dans l'environnement du processus, comme
  `demarrer-autonome.sh` le faisait déjà, et ajoute l'adresse locale détectée aux hôtes autorisés.
  **Seule conséquence : les sessions ouvertes sont à renouveler une fois.**
- Guide de déploiement §9.4 (procédure, dépannage, sécurité) et guide d'utilisation §19.7.
- Tests : `installer/tests/test-acces-distance.ps1` (22 vérifications, exécuté dans l'intégration continue).

## 5.45.5 — 2026-10-31

- **Barre latérale : les sous-menus sont classés par ordre alphabétique.** Dans les treize menus
  (Inscriptions, Pédagogie, Bulletins, Présences, Examens, Vie scolaire, Personnel, Finances, Vacations,
  Communication, Manuels, Documents, Paramètres), les entrées de chaque sous-menu apparaissent désormais
  de A à Z, selon l'ordre alphabétique **français** : accents et casse sont ignorés (« Élèves » à E,
  « Évaluations » entre « Enseignements » et « Matières »), « & » compte comme séparateur (« Bourses &
  Aides » à Bourses).
- L'ordre des menus de premier niveau ne change pas ; aucun lien n'apparaît ni ne disparaît. Les entrées
  conditionnelles suivent la même règle : « Mes cours » (réservé aux enseignants) est sortie de l'imbrication
  « Appels » sans changer sa condition d'affichage, et « Paie du mois » (même droit que « Salaires ») a été
  séparée pour être triable.
- Vérifié : visibilité strictement identique pour les 8 comptes de démonstration (494 entrées), rendu réel
  contrôlé dans le navigateur ; nouveau test `core/tests/test_menu_alphabetique.py` (ordre lu sur la page
  rendue, les 13 sous-menus).

## 5.45.4 — 2026-10-31

- **Guide d'aide : cliquer une entrée du sommaire n'affichait pas la section.** Le script du sommaire appelait
  `scrollIntoView` sur le lien devenu actif ; cette méthode fait défiler **tous** les conteneurs de la page,
  y compris le document. Le guide mesurant ~255 000 px et le sommaire commençant à ~230 px, chaque titre
  observé ramenait la page en haut du sommaire : la section visée restait à 10 000 px et le clic semblait
  sans effet. Le sommaire fait désormais défiler son propre cadre (`scrollTop`), jamais la page.
- Sur cette page, les ancres amènent la section **immédiatement** (`html:has(.aide-layout) { scroll-behavior:
  auto }`) : le défilement « doux » parcourait des dizaines de milliers de pixels à chaque clic.
- Vérifié : ancre dans l'URL, clic dans le sommaire (305 entrées), liens de la table des matières du guide
  (301 liens, 0 cassé) ; défilement manuel stable. Nouveau parcours navigateur (6ᵉ) : il échoue sur le code
  d'origine, passe après correction.

## 5.45.3 — 2026-10-31

- **Disposition des boutons des en-têtes de page** (liste des élèves, et les 37 écrans qui partagent le même
  gabarit). Trois défauts corrigés, sans toucher aux gabarits :
  - sous 1 366 px, les cinq boutons du bandeau « Gestion des Élèves » sortaient de l'écran (633 px de large
    dans 480 px de place) : le bloc se replie désormais sous le titre, les boutons passant à la ligne ;
  - sur téléphone, le titre et les boutons débordaient horizontalement (page de 390 px élargie) : les actions
    occupent la largeur, les exports se rangent trois par ligne, l'action principale reste intacte à côté ;
  - une page dont l'en-tête ne contient que des boutons ne subit plus la largeur du bloc de titre.
- CSS seulement (`static/css/yelen.css`) : aucune modification de gabarit, aucun test modifié.

## 5.45.2 — 2026-10-31

- **Dossier documentaire d'un élève (page « Dossier documentaire ») : erreur 500 corrigée.** Le gabarit
  écrivait `{{ d.signataire_nom|default:d.signataire }}` ; Django évalue l'argument d'un filtre, et un
  `Document` n'a pas d'attribut `signataire` (le nom y est un instantané). La page échouait dès qu'un document
  généré — bulletin, reçu, certificat — figurait au dossier ; elle affiche désormais le tiret cadratin.
- Même défaut corrigé là où le gabarit citait un objet facultatif (`SET_NULL`) comme argument de `default:` :
  cahier de textes sans auteur, page d'un transfert sans demandeur. Les deux passent par `{% firstof %}`, qui
  tolère une variable absente ; les autres occurrences du projet (63 relevées) ne citent que des objets
  obligatoires. Couverture : un test par page, chacun vérifié en échec sur le gabarit d'origine.

## 5.45.1 — 2026-10-31

- `reinitialiser_demo` ne vide plus la base : la commande s'appuie sur `charger_demo --reset` et supprime en
  plus les élèves restés sans inscription (traces d'un visiteur). Sous PostgreSQL, un paiement comptabilisé
  est immuable : la commande s'arrête avec un message explicite au lieu d'échouer sur le vidage.
- `docker-compose.demo.yml` passe en SQLite (volume Docker), comme l'installation autonome : la remise à zéro
  nocturne redevient possible. Services `db`/`redis` retirés, `entrypoint.demo.sh` n'utilise plus
  `--sans-vidage` ; `.env.demo.example` et guide §39 alignés.

## 5.45.0 — 2026-10-31

### Offre hébergée et instance de démonstration (chantier B8)

Une instance d'essai publique peut désormais tourner sur un VPS avec **la même image que l'installation
d'école**, sans qu'aucune donnée ni message n'en sorte.

- `DEMO_MODE=true` (réglage, `.env.demo`) : commutateur unique, vérifié aux quatre points de sortie —
  `core.sms.sms_actifs()` (aucun SMS, rien n'est mis en file), `core.notifications` (e-mail retenu),
  `core.push.notifier()` (aucune poussée), `finances.paiements_mobiles.cinetpay_configure()` (demande Mobile
  Money réputée non configurée, aucun appel sortant). Détail : `core/mode_demo.py`.
- Bandeau **DÉMONSTRATION** fixe sur toutes les pages et sur l'écran de connexion, y compris à l'impression ;
  `/health/` expose `"demo": true`.
- Commande **`reinitialiser_demo`** : reconstruit l'établissement de démonstration (C4) et efface les traces
  des visiteurs ; refuse de s'exécuter hors mode démonstration, où elle effacerait les données d'une école.
- `docker-compose.demo.yml` + `entrypoint.demo.sh` + `.env.demo.example` : même image que l'école, base SQLite
  dans un volume, chargement du jeu au premier démarrage, service `reset` pour la remise à zéro nocturne.
- Garde-fou de configuration : `DEMO_MODE=true` avec `LICENSE_ENFORCEMENT=true` empêche le démarrage.
- Tests (14), guide §39.

## 5.44.2 — 2026-10-31

- Tests : le quota de connexion de l'API (5 tentatives par minute, tenu par le cache) n'était pas remis à zéro
  entre deux tests. Sous Redis — job CI « mode serveur » — les tentatives des tests d'API s'additionnaient et un
  test d'authentification réussie recevait 429. Le cache est vidé avant chaque test quand il n'est pas
  transactionnel (`conftest.py::quota_api_isole`).

## 5.44.1 — 2026-10-31

- `documents/test_signataires.py` : le cycle de test utilisait le code `PRIMAIRE` alors que
  `Cycle.code` est limité à 4 caractères (`PRES`, `PRIM`, `POST`, `SEC`). SQLite tolérait la valeur,
  PostgreSQL la refuse : la CI serveur échouait. Code corrigé en `PRIM`.

## 5.44.0 — 2026-10-31

### Découpage des gros fichiers et styles du gabarit (chantier C2)

Aucune ligne de code métier n'a été réécrite : les fichiers ont été répartis par domaine, chaque nom reste
importable à son ancienne adresse (réexport dans `__init__.py`).

| Avant | Après | Contenu |
|---|---|---|
| `parametres/models.py` (2 081 l.) | paquet `parametres/models/` — 8 modules | `etablissement`, `structure`, `annee`, `evaluation`, `tarifs`, `documents`, `vie_scolaire`, `droits` |
| `core/views.py` (1 766 l.) | paquet `core/views/` — 8 modules | `accueil`, `audit`, `notifications`, `portail`, `sms`, `exploitation`, `pwa`, `systeme` |
| `inscriptions/views.py` (1 634 l.) | paquet `inscriptions/views/` — 7 modules | `eleves`, `inscriptions`, `documents`, `rentree`, `parcours`, `transferts`, `preinscriptions` |
| `core/templates/core/base.html` | gabarit sans style en ligne ni bloc `<style>` | styles déplacés dans `static/css/yelen.css` (section « structure du gabarit de base ») |

- Chaque module ne reçoit que les imports qu'il utilise ; les dépendances internes au paquet sont explicites
  (`from .tarifs import RubriquePaiement`), les imports relatifs au module d'origine remontent d'un cran.
- `base.html` : les 15 attributs `style="…"` et le bloc `<style>` du sous-menu sont devenus des classes
  (`.sb-item-modern.is-info`, `.topbar-mobile`, `.app-footer`, `.sidebar-overlay`…). Le gabarit n'émet plus
  de CSS, la feuille reste mise en cache et soumise à la CSP.
- Tests : deux cibles de patch PDF suivent leur module (`inscriptions.views.eleves` / `.documents`) ; suite
  complète 1 530 tests, parcours navigateur 5/5, couverture 82,04 %.

## 5.43.0 — 2026-10-31

### Tests des modules transverses et deux défauts d'API corrigés (chantier C3)

- **Corrigés** — `api/urls.py` : `/api/annees/<id>/periodes/` était déclarée en `<int:annee_id>` alors que les
  clés de l'application sont des UUID : la route répondait 404 quelle que soit l'année demandée.
- **Corrigés** — `api/serializers.py` : `MoyenneGeneraleSerializer`, `PaiementSerializer` et
  `PresenceSerializer` déclaraient des champs inexistants (`nb_absences`, `nb_retards`, `statut`,
  `justifiee`) et une relation `inscription.resultats_trimestre` qui n'existe pas ; toute réponse contenant
  une moyenne, un paiement ou une présence levait une erreur 500. Les champs réels les remplacent
  (`moyenne_sur_20`, `nb_matieres_*`, `appreciation`, `mode_paiement`, `reference`, `minutes_retard`,
  `observations`).
- Tests (66) — vacations (validation des heures, bulletins mensuels et PDF, formulaire de contrat),
  établissements (fiche de configuration, périmètre du réseau, groupes, export XLSX), signataires de PDF
  (détection du cycle, replis, mono/multi-signataires, signature scannée), API (rotation et révocation des
  jetons, cloisonnement de chaque endpoint, permissions, licences absente/inactive) et manuels.
- Couverture des fichiers visés : `api/views.py` 78 → 98 %, `etablissements/views.py` 65 → 96 %,
  `vacations/views.py` 72 → 95 %, `manuels/views.py` 98 → 100 %, `signataire_tags.py` 77 → 92 %.
  Suite complète : 1 530 tests, couverture globale 81,90 %.

## 5.42.1 — 2026-10-31

- `charger_demo --reset` : sous PostgreSQL, la suppression de l'établissement cascade vers des paiements
  comptabilisés que le trigger d'immuabilité (`finances/0016`) refuse de supprimer. La commande traduit l'erreur
  SQL en message explicite (« choisissez un autre code ou une base d'essai SQLite ») ; sous SQLite (installation
  autonome) le comportement est inchangé. Tests (7), dont la traduction du garde-fou et le cas PostgreSQL.

## 5.42.0 — 2026-10-31

### Parcours navigateur vérifiés à chaque livraison (chantier C1)

- `core/tests/e2e/test_parcours.py` : cinq parcours dans un vrai navigateur (Chromium/Playwright) sur un
  serveur de test et le jeu de démonstration — connexion, encaissement avec reçu PDF, saisie de notes, bulletin
  PDF, portail parent. Balises `pytest.mark.e2e`, exclues de la suite ordinaire (`addopts`), ignorées sans
  Playwright.
- Job CI **`parcours`** : installation de Chromium (`python -m playwright install --with-deps chromium`),
  migrations, manifeste statique, puis `pytest -m e2e`.
- `requirements/dev.txt` : `playwright` ; `pytest.ini` : marqueur `e2e` et exclusion par défaut.
- `core/management/commands/charger_demo.py` : la fiche du personnel porte l'adresse du compte (l'enseignant
  titulaire est reconnu par son e-mail — `core.utils.get_membre_personnel`).
- Tests (5), guide §38.2.

## 5.41.0 — 2026-10-31

### Jeu de données de démonstration (chantier C4)

- `core/management/commands/charger_demo.py` : un établissement complet en une commande — identité et agrément
  (catégorie 2, zone 1), année en cours et année précédente, 3 cycles et 8 classes, statuts, 4 rubriques et tarifs
  conformes aux plafonds, 8 fiches de personnel et 10 comptes, élèves inscrits sur deux années, matières,
  enseignements, devoirs et compositions du 1er trimestre, notes, moyennes et rangs (via `CalculateurMoyenne`),
  paiements avec reçus, signataires des documents.
- Options `--eleves`, `--etablissement`, `--reset` ; commande **rejouable sans doublon**, limitée à l'établissement
  qu'elle crée.
- `core/demarrage.py` : l'étape « Signataires des documents » de l'assistant est désormais **calculée** (elle était
  toujours affichée comme non faite) ; un établissement de démonstration atteint 8/8.
- Tests (6), guide §3.13.

## 5.40.0 — 2026-10-31

### Export comptable SYSCOHADA

- `finances/export_comptable.py` : journal de caisse des recettes (571 Caisse / 521 Banques ↔ 706 Prestations de
  services, 707 Produits accessoires pour cantine, transport, internat) et journal des dépenses validées (661, 604,
  624, 605, 628, 625, 633, 658 → 571/521), récapitulatif débit/crédit/solde par compte ; comptes paramétrés dans
  `COMPTES_DEPENSES`.
- Vue `finances:export_comptable` (`/finances/export-comptable/`), fichier XLSX `ExcelExport`, bouton sur la page
  Dépenses, sélecteur d'année.
- Tests (2), guide §9.37.

## 5.39.0 — 2026-10-31

### Historisation pluriannuelle des indicateurs

- Modèle `core.IndicateurAnnee` (migration `core.0008`) : une ligne par établissement et par année — effectif
  (dont filles / garçons), moyenne générale, taux de réussite, de recouvrement et d'absentéisme, détails chiffrés,
  date de calcul.
- `core/indicateurs.py` : `calculer`, `mettre_a_jour` (idempotent) et `evolution` (écarts par rapport à l'année
  précédente) ; commande `historiser_indicateurs [--etablissement <uuid>]`.
- Page *Pilotage → Évolution pluriannuelle* (`core:indicateurs_evolution`, direction) : tableau des années, écarts
  colorés, bouton de recalcul ; lien depuis le tableau de bord direction.
- Tests (4), guide §3.12.

## 5.38.1 — 2026-10-31

- `core/demarrage.py` : `except NoReverseMatch` au lieu de `except Exception` (test « aucun except silencieux »).

## 5.38.0 — 2026-10-31

### Assistant de première configuration

- `core/demarrage.py` : les 8 étapes de mise en route (identité, année courante, cycles et classes, rubriques et
  tarifs, personnel, comptes de gestion, élèves, signataires) avec leur état **calculé dans la base** et le lien
  direct vers l'écran concerné ; fonction `avancement` (fait / total / pourcentage).
- Page `/demarrage/` (`core:demarrage`, réservée aux rôles accédant aux paramètres), barre de progression, état
  « Fait » / « À faire », carte d'accès dans *Paramètres*.
- Tests (2), guide §3.11.

## 5.37.1 — 2026-10-31

- Tests du dossier documentaire : import inutilisé retiré (ruff F401, job « Lint » de la CI).

## 5.37.0 — 2026-10-31

### Dossier documentaire par élève

- Modèle `inscriptions.PieceDossier` (migration `0023`) : type de pièce, précision, fichier PDF/image validé
  (`core.validators.validate_piece_jointe`, 5 Mo), inscription, déposant ; sous `media/eleves/dossier/`.
- Page *fiche élève → Dossier documentaire* (`inscriptions:eleve_dossier`) : **pièces déposées** (date, déposant,
  téléchargement, suppression) et **documents délivrés** (type, numéro, année, date d'émission, signataire, agent,
  PDF). Dépôt/téléchargement/suppression isolés par établissement.
- Export du dossier (§3.10) enrichi des pièces ; leurs fichiers sont supprimés à l'anonymisation.
- Tests (4), guide §4.4.

## 5.36.0 — 2026-10-31

### Portail élève au niveau du portail parent

- `/portail/eleve/` sert désormais les **mêmes vues et gabarits** que le portail parent (configuration `PORTAILS`
  dans `core/views.py`, navigation `core/partials/portail_nav.html`) : accueil, vie scolaire, cahier de textes,
  bulletins, notifications ; l'ancien gabarit `portail_eleve.html` est supprimé.
- **PWA élève** : manifeste `/manifest-eleve.json`, service worker `/sw-eleve.js` (cache `yelen-eleve-v1`),
  `static/js/pwa.js` lit `data-pwa-sw` / `data-pwa-scope` sur `<body>` ; notifications push via le partiel commun.
- **Bulletins** : consultation en lecture seule `portail_bulletin` (`/portail/{parent,eleve}/bulletins/<pk>/`) ;
  **Documents délivrés** (certificats, attestations…) listés sur la page Bulletins et téléchargeables par
  `portail_document` (`/portail/{parent,eleve}/documents/<pk>/`), restreints aux élèves liés au compte.
- Page Vie scolaire : sections **Notes récentes** et **Moyennes par matière** (parent et élève) ; le dépôt de
  justificatif reste réservé au parent.
- `notifier_bulletin_publie` notifie aussi le compte élève (lien `/portail/eleve/bulletins/`, sans SMS).
- Guide §19.6 (et §9.21 renvoyé).

## 5.35.0 — 2026-10-31

### Cycle de vie des données personnelles (loi n° 001-2021/AN)

- *Paramètres → Données personnelles* : **durée de conservation** (10 ans par défaut après la dernière année
  d'inscription), responsable du traitement, compte et aperçu des élèves sortis, bouton **Anonymiser** (confirmation,
  journal d'audit), **registre des traitements** (`parametres.PolitiqueDonnees`, migration 0044).
- Anonymisation (`core/donnees_personnelles.py`) : identité, contacts, parents/tuteur, santé, photo, justificatifs
  d'absence et PDF archivés (fichiers supprimés), payeur Mobile Money, pré-inscriptions expirées ; comptes parent/élève
  sans élève identifiable fermés ; inscriptions, notes et paiements conservés anonymes (`Eleve.anonymise_le`,
  migration `inscriptions.0022`).
- Fiche élève → **Exporter le dossier** (JSON complet, journalisé) : `inscriptions:eleve_export_donnees`.
- Commande `anonymiser_donnees [--dry-run]` pour une exécution planifiée.
- Guide §3.10.

## 5.34.1 — 2026-10-31

- Migration `parametres.0042` : le code du type de document « Attestation de conformité tarifaire » dépassait les
  20 caractères de `TypeDocument.code` (refusé par PostgreSQL, toléré par SQLite) → code `CONFORMITE_TARIFAIRE` ;
  migration `0043` corrige les installations SQLite déjà migrées.

## 5.34.0 — 2026-10-31

### Grille tarifaire réglementaire (décret n° 2026-0761)

- *Identité Établissement* : **catégorie réglementaire** (1 à 3) et **zone d'implantation** ; *Rubriques* : case
  **Frais plafonnés** (décochée pour cantine, transport, internat et frais autorisés par la tutelle).
- Grille des plafonds par cycle × catégorie × zone (`parametres/plafonds.py`, arrêté n° 2026-101 du 10/07/2026) ;
  **refus à la saisie** d'un tarif qui porterait le total plafonné d'une classe/statut au-delà du plafond, message
  explicite ; établissement non classé = aucun contrôle.
- Page *Tarifs → Conformité réglementaire* (total plafonné, plafond, écart, hors plafond par classe et statut) et
  **attestation de conformité tarifaire** PDF A4, délivrée seulement si tout est conforme, signée par le signataire
  du nouveau type de document (migration `parametres.0042`). Tests (5), guide §3.9.

## 5.33.1 — 2026-10-31

- CI : le paquet `libgdk-pixbuf-xlib-2.0-0` n'existe plus sur l'image `ubuntu-latest` (Ubuntu 26.04) et WeasyPrint 70
  ne l'utilise pas — retiré des deux jobs (`libpangoft2-1.0-0` ajouté). L'image Docker (Debian) est inchangée.

## 5.33.0 — 2026-10-31

### Remise en ordre du guide, guide de démarrage rapide, favicon

- **Numérotation continue** du guide d'utilisation : chapitres 1 à 37 et sections N.1…N.k dans l'ordre du
  document (plus de chapitre 3 manquant, de doublons « 10 » / « 14.4 » / « 27.7 », de « 6.0 », « 13.A » ou
  « 25.3b »). Table des matières régénérée (287 liens vérifiés), renvois internes `§ x.y` et ancres du plan
  contextuel de l'aide (`core/aide.py`) mis à jour ; copie égarée de « Emploi du temps » retirée du chapitre
  Finances. Un test impose désormais la continuité à chaque ajout. Les renvois des entrées antérieures de ce
  journal suivent l'ancienne numérotation.
- **Guide de démarrage rapide** (`docs/GUIDE_DEMARRAGE_RAPIDE.md`, dix pages) : premier jour, rentrée,
  quotidien, trimestre, fin d'année, communication, sécurité, dépannage, qui fait quoi, liste de contrôle —
  chaque étape renvoie au guide complet (75 renvois vérifiés par test). Rendu dans l'application à
  `/aide/demarrage/`, bouton **Démarrage rapide** ↔ **Guide complet** sur la page d'aide.
- **Favicon** : icône SVG `img/favicon.svg` déclarée dans l'application, la page de connexion et le portail
  parent ; route `/favicon.ico` (redirection vers l'icône PNG, cache 24 h, autorisée aux rôles Parent/Élève)
  pour toutes les autres pages — fin des 404 dans les journaux.

## 5.32.0 — 2026-10-31

### Thème clair au choix

- *Mon profil → Apparence* : **Sombre** (par défaut, inchangé), **Clair** ou **Selon l'appareil** (`prefers-color-scheme`,
  suivi en direct par `static/js/theme.js`). Préférence enregistrée sur le compte (`User.theme`, migration
  `accounts.0009`), rendue par l'attribut `data-theme` de `<html>` avant le premier affichage : aucun scintillement.
- Feuille de style : palette claire par surcharge des variables (`:root[data-theme="clair"]`), teintes blanches
  translucides exprimées via `--ink` (114 occurrences, identiques en sombre), fonds codés en dur du coffre de
  l'application (barre latérale, en-têtes de tableaux, champs, fenêtres modales) ramenés aux variables.
- Portail parent, page de connexion et PDF inchangés.

## 5.31.0 — 2026-10-31

### Cahier de textes et devoirs dans le portail parent

- Nouvelle page **Cahier de textes** (`/portail/parent/cahier/`), par enfant : tous les devoirs non échus (« pour
  aujourd'hui » signalé) puis les cours des 30 derniers jours — date, matière, horaire, contenu traité, devoirs donnés
  et date de remise.
- Accueil : la section « Travail à faire » est toujours affichée pour un enfant inscrit, avec le lien vers le cahier
  de textes et un état vide explicite ; sa requête réutilise `core.portail.devoirs_a_venir` (doublon supprimé).

## 5.30.0 — 2026-10-31

### Notifications push pour le personnel

- La carte « Notifications sur cet appareil » du portail parent est reprise en haut de la page Notifications de
  l'application : chaque membre du personnel peut recevoir sur son téléphone ou son PC, application fermée comprise,
  les notifications qui lui sont destinées — seuil d'absences atteint, alertes du serveur (5.29.0), rappels de
  licence. Toucher la notification ouvre la page concernée de l'application.
- Même mécanisme que pour les parents (`core/push.py`, clés VAPID de l'installation) : le service worker de
  l'application (`/app-sw.js`) affiche les notifications, le script `push.js` (ex-`push_parent.js`) pilote la carte
  pour les deux publics ; points d'abonnement déplacés sous `/notifications/push/…` et ouverts à tout utilisateur
  connecté. Aucune migration.

## 5.29.0 — 2026-10-31

### Alertes d'exploitation relayées à la direction

- Les alertes de la page Exploitation — aucune sauvegarde ou sauvegarde de plus de 36 h, espace disque faible, erreurs
  applicatives répétées, SMS en difficulté — ne sont plus seulement affichées : elles sont **relayées aux Directeurs /
  Proviseurs et Super Admin** par notification interne (+ e-mail si configuré) et, pour le niveau danger (sauvegarde,
  disque), par **SMS**. Une fois par jour tant que l'alerte dure ; registre = table des notifications (valable pour
  tous les processus, survit aux redémarrages).
- Sans planificateur ni configuration : `core/veille.py` (`VeilleMiddleware`) lance la vérification en arrière-plan à
  la première requête du jour de chaque processus (`/health/` de la surveillance compris). La surveillance Windows
  reste nécessaire pour le seul cas d'un serveur arrêté.
- Titre stable de l'alerte « Erreurs applicatives répétées » (le nombre passe dans le détail).

## 5.28.0 — 2026-10-31

### Rappels d'expiration de la licence

- **Bandeau** discret en tête de chaque page pour les administrateurs (Super Admin, Directeur / Proviseur, Directeur
  Réseau) dès **J-30** : « La licence expire dans N jours (date) », rouge à partir de J-7, puis « Licence expirée le … »
  tant qu'elle n'est pas renouvelée ; lien **Renouveler** pour le Super Admin.
- **Notification interne + SMS** (+ e-mail si configuré) au **Directeur / Proviseur** à **J-15** et à **J-7** — à défaut
  de compte Directeur, aux Super Admin de l'établissement. Un seul envoi par palier et par période de licence
  (alertes `J-30` / `J-15` / `J-7` / `J-1` de `Licences → Alertes`, marquées envoyées avec leurs destinataires).
- Sans planificateur ni configuration : la vérification part de la première page affichée chaque jour, et du contrôle
  des licences lorsqu'il est actif (`LicenceCheckMiddleware` délègue à `licences/rappels.py`, plus d'alertes
  silencieuses). Fonctionne quel que soit `LICENSE_ENFORCEMENT`.
- Connexion : les administrateurs ne reçoivent plus le message « Attention : la licence … expire » en double du
  bandeau (il reste affiché aux autres rôles). **Correctif** : licence expirée, le Super Admin — seul habilité à saisir
  le code de renouvellement — pouvait être refusé à la connexion comme tout le monde (impasse) ; il est désormais
  dirigé vers la page d'activation.

## 5.27.0 — 2026-10-30

### Notifications push du portail parent

- Le parent active, depuis la page Notifications du portail (ou l'invitation de l'accueil), les **notifications sur
  son téléphone** : chaque notification interne (absence, retard, bulletin publié, sanction, rappel de paiement,
  réunion) est poussée sur l'appareil, application fermée comprise ; **Tester** envoie une notification de test et
  rend compte du résultat ; **Désactiver** retire l'appareil. Toucher la notification ouvre la page du portail.
- Web Push standard (`core/push.py` : chiffrement aes128gcm, signature VAPID, remise HTTP) sans service tiers ni
  composant payant ; clés de l'installation générées à la première utilisation et conservées en base
  (`ClesWebPush`), abonnements par appareil (`AbonnementPush`, migration `core 0007`) ; un abonnement révoqué par le
  navigateur (404/410) est supprimé à l'envoi. Dépendances ajoutées : `py-vapid`, `http-ece`.
- Service worker du portail : affichage des notifications et ouverture de la page au toucher ; bannières
  d'installation et de mode hors ligne du portail de nouveau visibles (classe `pp-hidden`).
- Correctif : pour un parent connecté, le contrôle d'accès par rôle renvoyait `/sw.js`, `/manifest.json` et les icônes
  vers le portail — l'application ne pouvait ni s'installer ni recevoir de notifications ; ces ressources sont
  désormais autorisées (`RoleAccessMiddleware`).
- Mode autonome : les dépendances sont réinstallées quand `requirements/base.txt` change (`demarrer-autonome.bat`
  / `.sh`), au lieu d'une installation unique. Guide §20.3.

## 5.26.1 — 2026-10-30

### Un enseignant ne fait l'appel que de ses classes

- Module Présences : pour un compte **Enseignant**, les classes proposées (`Faire l'appel`), l'historique des appels,
  son export CSV et son impression se limitent aux classes de ses **enseignements actifs de l'année**
  (`Pédagogie › Enseignements`, fiche du personnel reliée par l'adresse e-mail) — même règle que la saisie des notes.
- La création d'un appel, sa saisie, le scanner QR, le pointage et les cartes QR d'une autre classe sont refusés avec
  un message explicite (classe non attribuée, ou fiche du personnel absente) ; la file hors réseau reçoit ce refus.
- Dans sa classe, la liste des matières se limite à celles qu'il y enseigne ; l'appel général reste possible.
- Direction, censeur, AVS, secrétariat : inchangé (toutes les classes). Guide §7.1.

## 5.26.0 — 2026-10-30

### Compte rendu quotidien du promoteur par SMS

- Nouveau déclencheur **Compte rendu quotidien du promoteur** (`Configuration → SMS automatiques`) : chaque jour à
  l'heure choisie, un SMS de 160 caractères au plus résume la journée — encaissements (total, nombre de reçus,
  remboursements, espèces en caisse), dépenses validées, arrêtés de caisse faits / caissiers et écart, absents et
  retards sur les appels saisis (`communication/compte_rendu.py`, mêmes calculs que le journal de caisse).
- Réglage sur la ligne du déclencheur : heure d'envoi (18:00 par défaut) et 1 à 5 numéros validés ; aperçu du
  message du jour avec son nombre de caractères ; **Tester** envoie immédiatement sans empêcher l'envoi du jour.
- Envoi par le service SMS existant (`sms_recus --boucle`, Docker `sms` / mode autonome), une seule fois par jour
  dès que l'heure est passée ; la tâche `sms_auto` du matin l'ignore (`--type COMPTE_RENDU` = envoi à la demande).
- Texte allégé automatiquement au-delà de 160 caractères (retards, puis nombre de reçus, puis espèces et écart),
  sans caractère hors du jeu GSM : un seul segment facturé.
- Migration `parametres 0041` (`heure_envoi`, `destinataires`). Guide §2.20.

## 5.25.0 — 2026-10-30

### Saisie hors réseau des notes et des appels (enseignants)

- Les pages **Saisie des notes** et **Appel** soumises alors que le serveur est injoignable sont conservées
  sur l'appareil par le Service Worker (`static/js/sw_saisies.js`, IndexedDB), puis **rejouées
  automatiquement** dès qu'une page de l'application est ouverte sur le réseau — par le même compte,
  avec le jeton CSRF courant (`static/js/saisies_hors_ligne.js`).
- Le rejeu porte l'en-tête `X-Saisie-Differee` : les vues répondent en JSON (`core.hors_ligne.saisie_differee`,
  session expirée → 401, saisie d'un autre compte → 403, droit retiré → 403 JSON par le middleware des rôles)
  et les messages de la vue sont restitués à l'enseignant au lieu de ressortir plus tard.
- Nouvelle page **Saisies hors réseau** (`/hors-ligne/saisies/`, pré-cachée, accessible sans serveur) :
  saisies en attente, nouvel essai d'une saisie refusée, retrait, transmission manuelle, pages de saisie
  consultables sans réseau, dernières transmissions. Pastille « N saisie(s) en attente » sur toutes les pages.
- Sur une page de saisie : mention « Disponible hors réseau » et **restauration des valeurs** d'une saisie
  en attente ou refusée (motif affiché).
- Titres des pages de saisie identifiables : `Notes — Devoir 1 — Mathématiques — 6e A`,
  `Appel — 5e B — Physique — 30/10/2026`.
- Page hors ligne : lien vers la file ; plus de boucle de rechargement quand l'appareil est connecté à un
  autre réseau que celui de l'établissement ; pré-cache des ressources par leur URL réelle (`static()`),
  donc page hors ligne stylée aussi en production.
- Correctif Service Worker : les pages et ressources visitées n'étaient en réalité jamais mises en cache
  (copie de la réponse faite après le début de sa lecture, erreur silencieuse) — copie immédiate et
  écriture garantie (`waitUntil`) ; les pages déjà ouvertes sont donc bien consultables sans réseau.
- Guide §28.6.

## 5.24.0 — 2026-10-30

### Lisibilité des nombres : séparateur de milliers
- Tous les montants affichés (écrans, PDF, confirmations) sont écrits « 150 000 » au lieu de « 150000 » : `floatformat:0` → `floatformat:"0g"` dans 65 gabarits (294 affichages), totaux de points des bulletins compris ; montants bruts de la situation élève, de la liste des paiements et de l'historique des versements alignés. Les champs de saisie numériques restent bruts.
- Effectifs du tableau de bord et du tableau de bord réseau groupés de même (« 1 250 élèves »).
- Messages et libellés calculés en Python : 24 montants passaient par le groupement anglais (« 150,000 FCFA », virgule lue comme décimale en français) → helper `core.utils.fcfa()` (« 150 000 FCFA »).
- Garde-fou : un test refuse tout nouveau `floatformat:0` hors attribut de saisie et tout `:,.0f` suivi de FCFA. 2 tests.

## 5.23.0 — 2026-10-30

### Liste alphabétique du personnel (Documents → Liste du personnel)
- Second tableau récapitulatif sous la liste, dans l'aperçu et le PDF : **personnel par titre de capacité et par genre** (Hommes / Femmes / Total, ligne TOTAL). Les titres sont regroupés sans tenir compte de la casse (graphie majoritaire affichée) ; les agents sans titre saisi figurent sur une ligne « Non renseigné », en dernier. En-têtes des récapitulatifs sur une seule ligne. 1 test.

## 5.22.1 — 2026-10-30
- Tests : isolation du cache de la matrice des droits entre les tests (fixture globale) — en mode serveur (Redis), un refus posé par un test survivait à sa transaction et faisait échouer le test suivant en CI. Aucun changement fonctionnel.

## 5.22.0 — 2026-10-30

### Suppression des messages envoyés aux parents
- Messages parents : bouton **Supprimer** sur chaque ligne de la liste (retour à la vue filtrée), cases à cocher avec case d'en-tête et **Supprimer la sélection** — en plus de la suppression par type / statut de 5.21.0. Même droit `Messages parents → supprimer`.
- Campagnes SMS : **Supprimer** sur la ligne de la campagne et sur sa page de suivi — la campagne et ses SMS sont effacés, les SMS encore en attente ne partent pas. Nouveau droit `Campagnes SMS → supprimer` (secrétariat et direction par défaut). 2 tests.

## 5.21.0 — 2026-10-30

### Communication bidirectionnelle : suppression par type et statut
- Liste des messages parents : avec un type et / ou un statut sélectionnés (recherche comprise), bouton **Supprimer les messages affichés** (nombre indiqué, confirmation) ; sans type ni statut, refus explicite. Fiche du message : **Supprimer**. Nouveau droit `Messages parents → supprimer` (secrétariat et direction par défaut).
- Suppression définitive : réponses du parent en cascade, fichiers justificatifs effacés du disque, SMS reçus conservés dans Messages reçus (détachés). Le compteur annoncé ne compte que les messages, pas les réponses supprimées en cascade.
- **Correction** : la page utilisait la clé de contexte `messages`, qui masquait les messages flash de Django (confirmation d'envoi, erreurs) sur la liste des messages parents et les rejouait sur la page suivante — clé renommée `messages_parents`. 2 tests.

## 5.20.0 — 2026-10-30

### Communication bidirectionnelle : renvoyer les messages non envoyés
- Liste des messages parents : colonne SMS avec l'état réel (*Non envoyé*, *En attente*, *Échec* avec motif, *Envoyé*) et bouton **Envoyer le SMS** / **Renvoyer** sur les lignes non envoyées ou en échec ; fiche du message : **Renvoyer le SMS** (confirmation si un SMS est déjà parti).
- `message_renvoyer_sms` recompose le SMS au format actuel (sigle, objet, contenu, consigne de réponse), relit le numéro sur la fiche élève (parent, sinon tuteur, sinon numéro d'origine), met en file une nouvelle ligne `SmsSortant` reliée au message ; refus explicite sans numéro, au-delà de 160 caractères ou SMS désactivés. Couvert par le droit existant *Messages parents → envoyer*. 2 tests.

## 5.19.0 — 2026-10-30

### Suppression des messages reçus
- `Communication → Messages reçus` : bouton **Supprimer** par ligne, cases à cocher (en-tête = toute la page) + **Supprimer la sélection**, et **Supprimer tous les lus** de la vue courante (libres / commandes / tous), chacun avec confirmation. Nouveau droit `Messages reçus → supprimer` (secrétariat et direction par défaut).
- Un message supprimé disparaît de la boîte, de la pastille du menu et du simulateur SMS Direct ; la ligne est conservée inactive (`is_active=False`) pour que la relève de la boîte du téléphone, qui dédoublonne par identifiant de SMS, ne le retraite pas (il réapparaîtrait sinon dans les 15 secondes avec une nouvelle réponse au parent). Aucune migration. 2 tests.

## 5.18.0 — 2026-10-30

### Communication bidirectionnelle par SMS, fin des « Commande invalide » en rafale
- **Cause** : le SMS envoyé au parent ne contenait que l'objet et un lien `https://<IP du réseau local>:8443/communication/repondre/…`, injoignable depuis le téléphone d'un parent (et l'envoi n'était pas coché par défaut) ; le parent répondait donc par SMS et chaque réponse recevait « Commande invalide. Envoyez AIDE… ». Un numéro de la SIM du téléphone passerelle présent sur une fiche élève faisait de plus boucler cette réponse sur elle-même toutes les 15 secondes.
- **Message en clair** : le SMS contient le sigle, l'objet, le contenu et la consigne de réponse selon le type (créneaux numérotés, « Repondez OK », date de règlement, motif) ; envoi coché par défaut ; refus explicite si le SMS dépasse 160 caractères ou si la fiche n'a aucun numéro ; `MessageParent.sms` (migration `communication 0007`) relie le message à sa ligne d'envoi — la fiche affiche le texte exact et l'état réel (en attente / envoyé le … / échec et motif).
- **Réponse du parent par SMS** (`communication/bidirectionnel.py`) : rattachée au dernier message envoyé à ce numéro depuis moins de 30 jours ; créneau (`2`, « je prends le 2 », libellé), accusé de réception, date de règlement (`15/11`) reconnus ; texte intégral conservé en commentaire horodaté ; message « Répondu » ; accusé « Reponse bien recue, merci… » ; journalisée `REPONSE` (`IncomingSMSLog.message_parent`) et affichée dans Messages reçus avec le lien vers le message.
- **Plus jamais de rafale** : un SMS libre reçoit « Votre message a bien ete recu par l'ecole… » au plus une fois par 24 h et par numéro ; une commande intégrée sans matricule (`NOTE`) reçoit le rappel du format ; un SMS identique à un SMS envoyé par l'école à ce même numéro depuis moins de 24 h est un écho : journalisé, jamais de réponse.
- 6 tests (`test_bidirectionnel.py`) ; guide §29, §10.3, §10.6.

## 5.17.1 — 2026-10-29

### Correctif de test
- `test_commandes_sms.py` : les mots-clés du test de troncature de `AIDE` dépassaient 20 caractères (accepté par SQLite, refusé par PostgreSQL en CI). Aucun changement applicatif.

## 5.17.0 — 2026-10-29

### Commandes SMS définies par l'école
- **Nouvelle page `Communication → Commandes SMS`** : l'école crée ses propres mots-clés avec réponse automatique (`HORAIRES`, `CONTACT`, `CANTINE`, `FRAIS`…), en plus de NOTE / SOLDE / ABS / AIDE. Mot-clé (2–20 lettres ou chiffres, mots intégrés réservés), synonymes acceptés, portée *générale* (mot seul, tout numéro) ou *élève* (mot + matricule, mêmes règles d'autorisation que les commandes intégrées), réponse ≤ 160 caractères avec compteur, activation / désactivation sans suppression, nombre d'utilisations.
- **Variables** remplacées à l'envoi : `{etablissement}` `{date}` `{annee}`, et en portée élève `{eleve}` `{prenom}` `{nom}` `{matricule}` `{classe}` `{moyenne}` `{rang}` `{trimestre}` `{absences}` `{excusees}` `{total_du}` `{total_paye}` `{reste}` ; seules les variables citées sont calculées. Variable inconnue, mot réservé, doublon ou réponse trop longue refusés à l'enregistrement.
- `AIDE` liste désormais les commandes intégrées puis celles de l'école (tronqué proprement à 160 caractères) ; le simulateur SMS Direct les affiche et les accepte ; Messages reçus les journalise (`PERSO`, lien vers la commande, `Count` des utilisations).
- Technique : modèle `communication.CommandeSms` + `IncomingSMSLog.commande` (migration `communication 0006`), module `communication/commandes.py` (`trouver`, `rendre`, `texte_aide`, `valider`), droit `Communication → Commandes SMS → gérer` (secrétariat par défaut), entrée de menu, admin. 7 tests (`test_commandes_sms.py`). Guide §10.2.

## 5.16.1 — 2026-10-29

### Relève des SMS reçus fiabilisée
- **Correction** : quand la boîte de l'app était vide à la première relève (app fraîchement installée), le tout premier SMS reçu ensuite était pris pour un SMS « antérieur à la mise en service » et ignoré sans réponse. Le plancher est maintenant posé même sur boîte vide.
- Relève : plancher initial fixe + dédoublonnage par identifiant (un SMS horodaté avant le dernier traité — deux SIM, horloges d'opérateurs — est traité quand même) ; dates comparées comme des instants (formats `…Z` / `…+01:00`) ; 100 derniers SMS relus à chaque passage.
- Carte « Réception des SMS des parents » : nombre de SMS présents dans la boîte de l'app et date du dernier reçu ; avertissement explicite quand l'app n'a enregistré aucun SMS (autorisation SMS de l'app, SIM du téléphone).
- Aucune réponse n'est envoyée aux codes courts et expéditeurs alphanumériques (SMS d'opérateurs) : journalisés dans Messages reçus, pas de SMS facturé. 3 tests ajoutés (14 au total pour la relève).

## 5.16.0 — 2026-10-29

### Réception des SMS des parents sans dépendre du webhook
- **Relève automatique de la boîte du téléphone** : nouveau service `sms` (`docker-compose.client.yml`, même image que `web`, démarré par `mettre-a-jour.bat`) qui exécute `python manage.py sms_recus --boucle` : toutes les 15 s, lecture de la boîte de réception de l'app SMS Gateway (`GET /inbox`, même adresse et mêmes identifiants que l'envoi) et traitement des SMS reçus (AIDE / NOTE / SOLDE / ABS, messages libres) exactement comme par le webhook — plus aucune condition côté téléphone (certificat, HTTPS, « Require Internet connection », webhook) pour que les parents reçoivent leur réponse. Le même passage renvoie les SMS sortants dont la reprise est due.
- **Un SMS, une réponse** : `IncomingSMSLog.message_id` (migration `communication 0005`) porte l'empreinte commune au webhook (`messageId`) et à la boîte (`id` « text:… ») ; un SMS arrivé par les deux chemins, ou un webhook rejoué par le téléphone, n'est traité qu'une fois (réponse `duplicate`). Première relève silencieuse : les SMS antérieurs à la mise en service ne reçoivent pas de réponse tardive.
- **Diagnostic** : carte « Réception des SMS des parents » en tête de `Paramètres → Configuration SMS` — dernière relève (verte / orange avec le motif : service non démarré, passerelle injoignable, SMS désactivés, app < 1.59), dernier SMS reçu et sort de la réponse (envoyée / en attente / échec et motif), bouton **Relever maintenant**. Le webhook devient le chemin instantané, facultatif.
- Technique : `communication/sms_recus.py` (`traiter_sms_recu` extrait du webhook, `relever_boite_reception`, `identifiant_message`) ; `core.sms.adresse_passerelle` / `requete_passerelle` partagés par l'envoi du webhook ; `restore-windows.ps1` / `restore-local.sh` arrêtent et relancent `sms` avec `web` (aucune session ouverte pendant la bascule de base). 11 tests.

## 5.15.1 — 2026-10-28

### Corrigé
- **Configuration SMS → Enregistrer sur le téléphone** : l'URL du webhook reprenait l'adresse de la page ouverte ; ouverte en `http://localhost:8000` sur le serveur (seul accès HTTP restant après `activer-https`), elle était refusée par l'app SMS Gateway (« url must start with https:// ») et, de toute façon, injoignable depuis le téléphone. L'URL est désormais toujours construite en HTTPS, sur le port du proxy (`YELEN_HTTPS_PORT`), avec l'adresse IP du serveur (`YELEN_HTTPS_HOSTS` quand la page est ouverte en localhost) ; un avertissement explicite bloque l'enregistrement si le HTTPS n'est pas activé ou si l'adresse n'est pas joignable. Guide §10.4.

## 5.15.0 — 2026-10-28

### Ajouté
- **Communication → Messages reçus** : boîte des SMS arrivés au numéro de l'école. Vue par défaut sur les **messages libres** des parents (réponses aux relances, questions…), filtre *Commandes automatiques* (NOTE / SOLDE / ABS / AIDE) et *Tous*, état lu / non lu ; famille identifiée d'après les numéros des fiches élèves quel que soit leur format ; **Marquer lu / non lu**, **Tout marquer comme lu**, **Répondre** par SMS (160 caractères, via la file SMS). Pastille du menu avec le nombre de messages libres non lus. Droit d'action *Marquer lu / non lu et répondre par SMS* dans la matrice des droits ; les requêtes du simulateur SMS Direct sont enregistrées déjà lues. Champs `lu_le` / `lu_par` sur le journal des SMS entrants (migration `communication 0004`). Guide §10.4, §10.6, §10.7.

## 5.14.3 — 2026-10-28

### Corrigé
- **Réception des SMS des parents (Parent-SMS Direct)** : le webhook `/communication/webhook/sms/` ne lisait que des champs à plat (`phoneNumber`, `message`) alors que l'app Android SMS Gateway envoie une enveloppe `{"event": "sms:received", "payload": {"sender", "message"}}` — tout SMS reçu était rejeté « Missing phoneNumber or message » et l'app réessayait 14 fois. L'enveloppe est comprise, les autres événements (`sms:sent`, `sms:delivered`, `system:ping`…) sont acquittés sans traitement, et la signature native de l'app (`X-Signature` = HMAC-SHA256(corps + `X-Timestamp`), ± 5 min) est acceptée quand un secret HMAC est configuré.

### Ajouté
- `Paramètres → Configuration SMS` : l'URL du webhook inclut le jeton (`?token=`, l'app ne sait pas ajouter d'en-tête) et le bouton **Enregistrer sur le téléphone** déclare cette URL à l'app SMS Gateway (`POST /webhooks`, événement `sms:received`, identifiant fixe, mêmes identifiants que l'envoi). Guide §2.17 et §10.4 (certificat YELEN sur le téléphone, « Require Internet connection » désactivé, vérification par `AIDE`).

## 5.14.2 — 2026-10-28

### Corrigé
- **SMS de relance** (`Finances → Relances → SMS`) : le montant partait d'un tarif pris au hasard (premier tarif de la rubrique, tous niveaux, statuts et années confondus, même inactif) et les élèves sans statut étaient relancés — des familles à jour recevaient un rappel, pour un montant faux, et la liste des SMS ne correspondait ni au compteur ni au PDF. Le compteur, le PDF et les SMS reposent désormais sur un calcul unique (`finances/redevables.py`), identique au formulaire de paiement : tarif du niveau × année × statut de l'élève, services et créances de la rubrique, bourses ciblées déduites, versements moins remboursements, plafonné au reste global de l'élève ; nombre de requêtes constant.
- **Modèles de messages** : un modèle citant une variable inconnue (`{eleve}`, `{reste}`…) était envoyé **tel quel** au parent, accolades comprises ; une accolade isolée faisait planter le rendu. Le rendu ne lève plus jamais d'exception, un modèle invalide est remplacé par le texte par défaut (signalé « Ignoré — variable inconnue » dans la liste) et l'enregistrement refuse variable inconnue, accolade isolée ou SMS de plus de 160 caractères (il serait tronqué). Les campagnes SMS partagent ce rendu.
- Relance SMS refusée (message explicite) quand l'envoi de SMS est désactivé, au lieu d'annoncer « N SMS envoyés » sans rien envoyer ; SMS mis en file par lot (un seul fil d'envoi) et tracés dans la file SMS au nom de l'élève et de la rubrique ; numéro de la fiche normalisé (`+226…`) dans l'historique ; résolution du numéro du parent (parent → tuteur → urgence) centralisée (`Eleve.telephone_parent_valide`) ; montant du rappel d'échéancier automatique formaté « 50 000 » et non « 50,000 ».

## 5.14.1 — 2026-10-28

### Ajouté
- **Environnement de test isolé** (`creer-environnement-test.bat` → `installer/creer-environnement-test.ps1`, guide de déploiement §3.5.7) : second YELEN SCHOOL complet à côté de la production (`C:\YELEN-TEST`, projet Docker `yelen-test`, image `yelen-school:test`, port 8001 sur 127.0.0.1, base et médias copiés de la dernière sauvegarde), `.env` dérivé de la production avec contrôle des licences actif (`LICENSE_ENFORCEMENT=true`, `LICENCE_BINDING_ENABLED=true`, `LICENCE_PUBLIC_KEY`), SMS, paiements mobiles, courriel et sauvegarde distante désactivés ; paire de clés de l'éditeur créée une seule fois dans `C:\YELEN-EDITEUR\cles-editeur.txt`. La production n'est jamais modifiée. Tests PowerShell `installer/tests/test-creer-environnement-test.ps1` (CI).
- **`installer/outils-editeur/emettre-licence.ps1`** : émission d'un code de licence `YELEN3` à partir du fichier des clés de l'éditeur (image Docker ou `.venv` autonome), sans afficher la clé privée.
- **Bandeau « ENVIRONNEMENT DE TEST »** (`YELEN_ENVIRONNEMENT=test`) sur la connexion, les pages de l'application et les pages licences.
- `docker-compose.client.yml` : nom de l'image paramétrable (`YELEN_IMAGE`, défaut `yelen-school:client`).

## 5.14.0 — 2026-10-28

### Ajouté
- **Absences du personnel** (`Personnel → Absences`, guide §9.33) : saisie (dates, motif, justifiée, retenue), bilan mensuel par agent, historique sur la fiche du membre ; la préparation de la paie propose une retenue de `salaire de base / 30 × jours non justifiés` dans « Autres retenues ». Modèle `AbsencePersonnel` (migration `personnel/0011`), droit « Absences du personnel ».
- **Sanction → parent** (guide §9.34) : case « Prévenir le parent » à la saisie d'une sanction (notification du portail parent + SMS, modèle `Sanction disciplinaire` avec `{nom_eleve} {classe} {date} {sanction} {motif} {etablissement}`), horodatage `parents_notifies_le` affiché dans la liste ; section « Sanctions disciplinaires » sur le portail parent (annulées exclues). Migrations `viescolaire/0009`, `parametres/0039`.
- **Fiche individuelle de l'élève** PDF A4 portrait signée (identité, photo, parents/tuteur, santé, personnes autorisées, parcours) depuis le dossier de l'élève (guide §9.35).
- **Attestation de travail** PDF A4 portrait signée (fonction, titre de capacité, date d'embauche, nature du contrat) depuis la fiche du membre (guide §9.36). Types de documents `FICHE_ELEVE` et `ATTESTATION_TRAVAIL` (migration `parametres/0040`, signataire repris de la catégorie).

### Corrigé
- **Examens** : les sessions, centres, salles et placements d'un autre établissement répondent désormais 404 (modification de session, inscription d'une classe, export CSV, PDF des candidats, centres, salles, placements) ; le formulaire de session ne propose que les années de l'établissement ; un centre d'une autre session ne peut plus être affecté.
- **Manuels** : le sélecteur d'élèves du formulaire d'attribution ignore une classe d'un autre établissement.
- **Sanctions** : l'ancien signal notifiait automatiquement chaque sanction créée (même importée) sans SMS ni trace — remplacé par la case à la saisie.
- Guide : front matter aligné (version 5.14.0, date, modules réels), variables des modèles SMS `Seuil d'absences` et `Sanction` listées dans l'écran des modèles.

### Tests
- 77 tests ajoutés : examens (35), manuels (15), personnel (13), vie scolaire (8), fiche élève (4), documents signés (2 : fiche élève, attestation de travail — 50 documents couverts). Suite : 1 293 tests, couverture 78,7 %.

## 5.13.1 — 2026-10-28

### Ajouté
- **Titre de capacité** sur la fiche du personnel (`Personnel → Nouveau membre`, volet « Carrière & Affectation », texte de 35 caractères, facultatif — ex. CAPES, CAP-CEG, Licence) ; affiché sur la fiche du membre. Champ `MembrePersonnel.titre_capacite` (migration `personnel/0010`).

## 5.13.0 — 2026-10-28

### Ajouté (audit — Lot I : confort)
- **Seuil d'absences** (`Présences → Alertes d'absences`) : la direction règle un seuil d'absences non justifiées (défaut 5, par trimestre ou par année, SMS au parent activable). À la **clôture de chaque appel**, tout élève absent qui atteint le seuil — puis chaque multiple (2×, 3×…) — déclenche une alerte : notification in-app du directeur et du censeur, SMS au parent (modèle `Seuil d'absences atteint`, modifiable dans `Paramètres → Modèles de messages`), message d'avertissement à l'enseignant qui clôture. La page liste les alertes à traiter (élève, classe, période, absences / seuil, SMS envoyé) ; « Traitée » enregistre la suite donnée (convocation, entretien) avec l'auteur et la date ; l'historique reste consultable. Une absence excusée par un justificatif accepté ne compte plus.
- **Santé et personnes autorisées** sur la fiche élève (section « Santé & personnes autorisées » du formulaire et de la fiche) : groupe sanguin, allergies, informations médicales (maladie chronique, traitement, consignes), médecin / centre de santé, **personnes autorisées à récupérer l'élève** (une par ligne : nom — lien — téléphone).
- **Référentiel des salles** (`Paramètres → Salles`) : nom, capacité, actif ; l'emploi du temps **propose les salles** à la saisie, **normalise** la casse (`salle 2` → `Salle 2`, donc les conflits de salle sont détectés quelle que soit la façon d'écrire) et **avertit** quand l'effectif de la classe dépasse la capacité de la salle. Page `Vie scolaire → Occupation des salles` : une ligne par salle, une colonne par jour, les séances de l'année dans chaque case (créneaux libres visibles), nombre de séances et heures par semaine, impression.
- **Pré-inscriptions** (`Inscriptions → Pré-inscriptions`) : dossier d'un nouvel élève **avant** l'inscription (année — par défaut l'année suivante dès qu'elle existe —, classe demandée, identité, origine scolaire, parent et téléphone), filtres année / classe / statut, **synthèse par classe** (en attente, acceptées, inscrites, effectif, capacité, places restantes, tension), décisions **Accepter / Refuser / Remettre en attente**, puis **Inscrire** : l'élève et son inscription (statut « Non affecté ») sont créés en un clic avec matricule, parent et téléphone repris, et le formulaire d'inscription s'ouvre pour compléter (statut, photo). Classe complète ou année clôturée refusées ; un dossier refusé ne peut pas être inscrit.
- **Sauvegarde depuis l'interface** (`Administration → Exploitation`, Super Admin / Directeur, mode autonome SQLite) : bouton **Sauvegarder maintenant** (base à chaud + archive ZIP des médias : photos, signatures, justificatifs), liste des sauvegardes disponibles (fichier, type, date, taille) avec **téléchargement** pour copie sur un support externe, rappel de la procédure de restauration. En mode serveur (PostgreSQL) la page renvoie vers `backup-windows.bat`.

### Technique
- `presences.SeuilAbsences` / `AlerteAbsences` (migration `presences/0007`), `presences/alertes.py` ; `inscriptions.Eleve` champs santé (migration `inscriptions/0020`) ; `parametres.Salle` + `Salle.canonique` (migration `parametres/0037`) ; `inscriptions.PreInscription` (migration `inscriptions/0021`), `inscriptions/preinscriptions.py` ; `ModeleMessage` type `SEUIL_ABSENCES` (migration `parametres/0038`) ; `core/sauvegarde.py` (`sauvegarder_maintenant`, `lister_sauvegardes`, `chemin_sauvegarde` — nom strictement validé, aucun chemin relatif), route `exploitation/sauvegardes/<nom>`. Heures d'occupation des salles affichées avec deux décimales.

## 5.12.0 — 2026-10-28

### Ajouté (audit — Lot H : communication, personnel, pilotage)
- **Campagnes SMS ciblées** (`Communication → Campagnes SMS`, direction / secrétariat / comptabilité) : public au choix — parents de tous les élèves inscrits, de classes cochées, des élèves ayant un reste à payer, des élèves absents un jour donné, ou membres du personnel — ; message à variables (`{eleve}`, `{classe}`, `{reste}`, `{etablissement}`, `{nom}`) ; **aperçu avant envoi** (nombre de destinataires joignables, élèves ou agents sans numéro valide, textes rendus, longueur du plus long message par rapport aux 160 caractères) ; un numéro partagé par plusieurs enfants reçoit **un seul SMS** qui les énumère ; les élèves partis (abandon) sont exclus. Les SMS sont mis en file en une fois et envoyés par **un seul fil d'arrière-plan** par paquets de 50. Historique des campagnes avec envoyés / échecs / en attente, détail par destinataire (statut, erreur) et **renvoi des échecs**.
- **Paie du mois** (`Personnel → Paie du mois`, bouton depuis `Salaires`) : tableau de bord du mois (bulletins par statut, totaux brut / retenues / net, agents permanents sans bulletin) ; **Préparer la paie** crée en une fois un brouillon pour chaque agent permanent (vacataires exclus) sans bulletin ce mois-ci, en reprenant salaire de base, indemnités et retenues CNSS / IUTS de son dernier bulletin, prime d'ancienneté recalculée, primes et retenues exceptionnelles à zéro (droit « Préparer la paie du mois en masse ») ; **Valider les brouillons** passe tout le mois en « Validé » (droit « Valider un salaire ») ; **Livre de paie** PDF (A4 paysage, une ligne par agent, totaux, signataire du bulletin de salaire) ; **Bulletins du mois** en un seul PDF (un bulletin par page, même gabarit que le bulletin unitaire).
- **Statistiques d'examen ventilées** (fiche de session → `Statistiques`, écran et PDF, droit « Statistiques de la session ») : inscrits, présents, admis, ajournés, absents, exclus et taux de réussite **garçons / filles / total**, par **classe d'origine**, par **centre**, par **mention**, répartition par **tranche de moyenne**, dix meilleures moyennes, candidats sans résultat saisi. Taux de réussite = admis / présents (les absents ne comptent pas au dénominateur).
- **Statistiques par enseignant** (`Pilotage → Statistiques par enseignant`, direction ; écran et PDF ; année ou période) : par enseignant puis par classe et discipline — nombre de classes et d'élèves, heures hebdomadaires (emploi du temps), évaluations terminées / créées (annulées exclues), **taux de saisie des notes** (notes saisies / élèves × évaluations, en rouge sous 80 %), moyenne et part d'élèves ≥ 10 (dispensés exclus), entrées du cahier de textes, appréciations rédigées. Les enseignements sans enseignant forment la ligne « Non attribué ».

### Technique
- `core.CampagneSms` + `SmsSortant.campagne` / `destinataire` (migration `core/0006`), `core.tasks.mettre_en_file_lot` / `_vider_file`, `communication/campagnes.py` ; `personnel/paie.py` ; `examens/statistiques.py` ; `pedagogie/statistiques_enseignants.py`. Quatre nouveaux PDF signés (`livre_paie`, `bulletins_salaire_lot`, `statistiques_session`, `statistiques_enseignants`).

## 5.11.0 — 2026-10-28

### Ajouté (audit — Lot G : portails)
- **Portail élève enrichi** : travail à faire (devoirs du cahier de textes à venir), quinze dernières notes, moyennes par matière et par période, emploi du temps de la semaine, absences et retards de l'année avec compteurs.
- **Portail parent — Vie scolaire** (`/portail/parent/vie-scolaire/`, barre de navigation commune Accueil · Vie scolaire · Bulletins · Frais · Notifications) : par enfant, emploi du temps, compteurs et dernières absences / retards, justificatifs déposés et leur statut.
- **Dépôt de justificatif d'absence par le parent** : période (au plus 30 jours, jamais à venir), motif, pièce jointe facultative (PDF, JPG ou PNG, 5 Mo, contenu vérifié). Le justificatif arrive « En attente » dans `Présences → Justifications` avec le badge **Portail parent** ; l'acceptation par le secrétariat excuse les absences comme aujourd'hui.
- **Appréciations par matière** (`Pédagogie → Appréciations par matière`, droit « Saisir les appréciations de ses disciplines ») : l'enseignant titulaire rédige, par période, l'appréciation de chaque élève pour sa discipline (200 caractères, suggestions, moyenne en regard) ; la direction voit toutes les disciplines. L'appréciation saisie est **imprimée sur le bulletin** en regard de la matière ; à défaut, la grille des moyennes s'applique comme avant. Une période clôturée est en lecture seule.
- **Comptes parents en masse** (`Utilisateurs → Comptes parents en masse`, direction) : les élèves de l'année sans compte parent sont regroupés par téléphone du parent ou du tuteur ; un compte par famille est créé (identifiant = numéro de téléphone, mot de passe provisoire de 12 caractères à changer à la première connexion), les enfants sont rattachés, un SMS d'accueil est mis en file si les SMS sont activés et un récapitulatif imprimable est affiché une seule fois. Les familles déjà équipées sont rattachées sans nouveau mot de passe ; les élèves sans téléphone sont listés.
- **Connexion par téléphone** : la page de connexion accepte l'e-mail ou le numéro de téléphone d'un compte parent créé en masse (toute mise en forme : espaces, +226, tirets).

### Corrigé
- Le recalcul des moyennes supprimait les lignes de résultat sans note : une appréciation saisie survit désormais au recalcul (ligne conservée sans moyenne).

### Technique
- `core/portail.py` (emploi du temps, assiduité, notes, devoirs, dépôt de justificatif), `core/validators.py::validate_piece_jointe`, `presences.Justification.deposee_par` (migration `presences/0006`), `pedagogie/views/appreciations.py`, `accounts/parents_masse.py`, `User.identifiant_connexion`. Le rôle PARENT accède aussi à `/bulletins/parent/` (consultation et signature du bulletin).

## 5.10.0 — 2026-10-28

### Ajouté (audit — Lot F : caisse et familles)
- **Journal de caisse par caissier** (`Finances → Journal de caisse`, PDF) : encaissements et remboursements d'une journée, totaux par mode de paiement, espèces théoriques en caisse (espèces − remboursements). Sans filtre, chaque utilisateur voit sa propre caisse ; « Toutes les caisses » pour la direction.
- **Arrêté de caisse** (droit « Arrêter sa caisse ») : le caissier saisit les espèces comptées ; l'écart est calculé et figé avec les totaux. Une caisse arrêtée refuse toute saisie de paiement ou de remboursement de ce caissier datée du jour arrêté ou d'un jour antérieur (« Votre caisse est arrêtée jusqu'au … »). Réouverture réservée à la direction (droit « Rouvrir une caisse »), historique des 15 derniers arrêtés.
- **Familles** (`Finances → Familles`) : fratries de l'année regroupées par compte parent, sinon par téléphone du parent ou du tuteur ; enfants (aîné d'abord), total dû, payé et reste à payer consolidés, recherche par nom / téléphone / enfant. La fiche financière de chaque élève affiche sa fratrie.
- **Remise fratrie automatique** (droit « Appliquer la remise fratrie ») : le type de bourse et le rang du premier enfant bénéficiaire (2e par défaut) se choisissent dans les paramètres financiers ; l'application attribue la bourse aux enfants de rang ≥ n qui ne l'ont pas encore (calcul sur le montant dû brut, pourcentage ou montant fixe), sans doublon à la ré-exécution.
- **Pénalités de retard** (`Échéanciers`, bandeau « Appliquer les pénalités », direction) : pour chaque échéance dépassée du délai de grâce, non cochée payée et non couverte par les versements (cumul des échéances dues à cette date > total payé), une créance « Pénalité de retard — <tranche> (échéance du …) » est émise sur la rubrique paramétrée (montant fixe ou % de la tranche). Une seule pénalité active par échéance ; annulable depuis la situation de l'élève.
- **Blocage des bulletins des élèves non à jour** (paramètre + seuil en % du montant dû) : portail parent, lien public de consultation / signature et API mobile n'affichent plus le bulletin tant que le seuil n'est pas atteint, avec le motif chiffré (« reste à payer … FCFA, x % requis »). La consultation interne (secrétariat, impression) n'est pas bloquée.
- **Paramètres financiers** (`Finances → Paramètres financiers`, droit d'approbation) : pénalités (mode, valeur, délai de grâce, rubrique), blocage des bulletins (seuil), remise fratrie (type de bourse, rang).
- **Portail parent** : vignette « Reste à payer » par enfant et section *Frais de scolarité* (montant dû net des bourses, versé net des remboursements, prochaine échéance, trois derniers reçus).

### Technique
- `finances.ParametresFinances` (un par établissement), `finances.ClotureCaisse`, `Creance.echeance` et origine `PENALITE` (migration `0023`) ; services `finances/caisse.py`, `familles.py`, `penalites.py`, `blocage.py` ; `_situations_financieres_en_lot` expose aussi `total_du_brut` et `total_reduction`. PDF « Journal de caisse » signé par le signataire du bilan des encaissements.


### Ajouté (audit — Lot E : rentrée et fin d'année)
- **Passage de classe en lot** (`Élèves → Réinscription`) : la page liste les élèves de l'année courante non encore inscrits pour l'année suivante, avec la dernière décision du conseil de classe et la classe de destination proposée (passage / rachat / sans décision → niveau supérieur, redoublement → même classe, exclusion / réorientation → aucune). Cases à cocher, classe modifiable ligne par ligne, inscription en un clic ; chaque refus (classe complète, déjà inscrit, année clôturée) est signalé nommément sans bloquer les autres. Filtre par classe, « Tout cocher », bouton **Détail** pour la réinscription individuelle.
- **Clôture d'année scolaire** (`Paramètres → Années scolaires`, boutons Clôturer / Rouvrir, droit « Clôturer / rouvrir une année scolaire ») : l'année courante ne se clôture pas ; la clôture verrouille les inscriptions de l'année (création, modification, transfert, abandon, réinscription vers cette année) et clôture toutes ses périodes d'évaluation ; une année clôturée ne peut plus être définie comme courante. La réouverture libère les inscriptions sans rouvrir les périodes.
- **Capacité des classes appliquée** : inscription, modification d'inscription et transfert refusent une classe pleine (« Classe 6e A complète : 50/50 places occupées pour 2025-2026 ») ; les abandons ne comptent pas.
- **Détection des homonymes** à la création d'un élève (nom + prénom + date de naissance, établissement courant) : bandeau listant les fiches existantes avec lien ; la création exige un second envoi de confirmation.

### Corrigé
- Réinscription : l'inscription était créée dans l'année **courante** (donc en double) au lieu de l'année suivante, sans statut élève ni marquage du redoublement ; l'année courante et l'année suivante étaient cherchées sans tenir compte de l'établissement (première année courante de la base). Désormais : année de l'établissement, inscription dans l'année suivante, statut élève repris, redoublant + classe redoublée renseignés, `last_classe` / `last_annee` de l'élève mis à jour.
- Formulaire d'inscription : la liste des années scolaires n'était pas limitée à l'établissement de l'utilisateur.

### Technique
- `inscriptions/services.py` (règles réinscription / capacité / clôture) ; `parametres/niveaux.py` (`cle_niveau`, `rang_niveau`, `niveau_suivant`) partagé avec les statistiques officielles.

## 5.8.1 — 2026-10-28

### Corrigé (audit — Lot D : dette technique)
- Assistant IA : les réponses ne sont plus calculées sur l'ensemble des établissements de la base mais sur celui de l'utilisateur connecté (effectifs, finances, absences, difficultés, moyennes, progression, recherche d'élève). Les montants attendus/encaissés reprennent le calcul du module Finances (tarifs + services + créances − bourses ; versements − remboursements) au lieu de l'ancienne table des frais. La page `/assistant/` est réservée à la Direction (Directeur, Censeur, Directeur réseau, Super Admin) ; une erreur interne affiche un message neutre et n'expose plus le détail technique. Reconnaissance de « Résumé des absences » et « Moyennes de la … » corrigée.
- Prédiction de réussite : le malus d'assiduité ne s'appliquait jamais (filtre sur un champ inexistant, masqué par un `except Exception` qui remplissait le journal). Les absences non justifiées (statut *Absent*) sont de nouveau comptées ; *Excusé* ne pénalise pas.
- SMS : modem série débranché ou port introuvable → échec propre consigné dans la file (au lieu d'une exception non rattrapée) ; `SMS_ENABLED` lu via `sms_actifs()` partout (notifications, convocation réunion, manuels, test de la passerelle).

### Technique
- Constante `StatutInscriptionChoices.ABANDON` à la place de 69 littéraux `'ABANDON'` dans 24 fichiers.
- `except Exception` : 93 → 75 (hors `licences/`, conçu pour ne jamais bloquer l'application : 39) ; les blocs restants journalisent la trace. Exceptions précises sur la 2FA, le chiffrement, les formulaires de paramétrage, la génération d'EDT, les modèles de SMS, la passerelle SMS.
- `parametres/views.py` (1 982 lignes) → paquet `parametres/views/` (scolarité, nomenclatures, tarifs, signataires, établissement, calendrier, messages/SMS) ; `viescolaire/views.py` (1 561 lignes) → paquet `viescolaire/views/` (conseils, sanctions, activités, EDT, suivi). Aucune URL ni nom de vue modifié.
- Tests : assistant IA (20), module SMS (40), prédictions (21) ; couverture mesurée 75 % (seuil CI 65 → 73).

## 5.8.0 — 2026-10-27

### Nouveau (audit — Lot C : exploitation)
- Emploi du temps : détection des conflits. Une séance est refusée si la classe a déjà cours, si l'enseignant est déjà en cours dans une autre classe ou si la salle est occupée au même moment (séances enchaînées autorisées) ; la génération automatique tient compte des cours des professeurs dans les autres classes et son application écarte les séances en conflit ; la grille d'une classe liste en tête les chevauchements déjà présents.
- SMS : file d'envoi persistante (`SmsSortant`). Chaque SMS est enregistré puis envoyé en arrière-plan ; les échecs passagers sont retentés (2 min, 10 min, 30 min, 2 h, abandon après 5 tentatives, immédiat pour un numéro invalide) par les envois suivants, la commande `sms_file`, la fin de `sms_auto` et le bouton « Réessayer maintenant ». Plus aucun message perdu au redémarrage. Administration Django.
- Exploitation : page `Administration → Exploitation` (Super Admin, Directeur) et bannière du tableau de bord : dernière sauvegarde (alerte au-delà de 36 h ou si aucune n'est visible), espace disque (alerte sous 5 Go ou 10 %), erreurs applicatives des dernières 24 h (journal `django.log`), état de la file SMS. Le dossier `backups\` du poste serveur est monté en lecture seule dans le conteneur (`docker-compose.client.yml`).

### Corrigé
- `SMS_ENABLED` enregistré à « False » depuis la page Configuration SMS était lu comme actif (chaîne non vide) : les envois étaient tentés puis échouaient. Lecture unifiée (`sms_actifs()`).

## 5.7.0 — 2026-10-27

### Nouveau (audit — Lot B, suite : créances individuelles)
- Finances : modèle **Créance** (dû individuel d'un élève, hors tarif et hors abonnement) compté dans le total dû au même titre qu'un service annexe : situation financière (carte *Créances individuelles*), reste à payer unitaire et en lot (redevables, relances, tableau de bord, certificats), formulaire de paiement (rubrique de la créance encaissable, plafond = tarif + services + créances de la rubrique). Action « Annuler une créance individuelle » (Direction) depuis la situation ; l'annulation ne touche pas aux versements encaissés. Administration Django.
- Manuels : `Non rendus → Facturer` émet une créance « Manuel non rendu » (prix de remplacement, rubrique MNR) au lieu d'un faux paiement ; le `Retour` du manuel annule automatiquement la créance. Colonne « Créance émise », messages et SMS reformulés (« frais à régler »).

### Corrigé
- Le faux paiement « Manuel non rendu » gonflait le total payé et bloquait tout encaissement réel sur la rubrique (plafond atteint). Migration de données : chaque attribution déjà facturée reçoit sa créance (annulée si le manuel a été rendu depuis) et le faux paiement, immuable comme tout paiement comptabilisé, est neutralisé par un remboursement de même montant. Le plafond d'encaissement par rubrique tient désormais compte des remboursements (une rubrique remboursée redevient payable).

## 5.6.0 — 2026-10-27

### Nouveau (audit — Lot B : intégrité des résultats)
- Clôture de période : `Paramètres → Périodes` propose « Clôturer » (cadenas) sur chaque période. Une période clôturée verrouille son trimestre : saisie des notes (formulaire désactivé), création et modification d'évaluations, import Excel de notes, saisie des compétences APC et calcul des moyennes sont refusés avec un message explicite ; moyennes, rangs et bulletins restent figés (une sanction prononcée après coup ne les modifie plus). « Rouvrir » lève le verrou ; chaque bascule est journalisée dans l'audit. Action « Clôturer / rouvrir une période » de la matrice des droits (Direction par défaut).
- Bulletins : absences justifiées (heures), non justifiées (heures) et retards sont relevés automatiquement dans **Présences** sur les dates du trimestre (absence excusée → justifiée ; séance sans horaire = 1 h). La fiche du conseil de classe s'ouvre pré-remplie et reste corrigeable ; sans fiche, liste, aperçu et PDF (unitaire et lot) impriment le relevé.

### Corrigé
- Calcul des moyennes : une note retirée ou une évaluation supprimée laissait une moyenne de discipline fantôme sur le bulletin ; ces résultats orphelins sont purgés au recalcul (les dispenses sont conservées) et un élève sans plus aucune note perd sa moyenne générale.
- Bulletins → « Publier tous » renvoyait une erreur 500 (variable `messages` masquée par un import local) : la publication en masse fonctionne de nouveau.

### Technique
- Bulletin annuel : un seul gabarit (`pedagogie/pdf/bulletin_annuel.html`) pour l'individuel et les lots de classe (`bulletin_annuel_batch.html` supprimé) ; `Trimestre.objects.pour_periode(periode)`, `Trimestre.verrouille`, `Bulletin.objects.obtenir(...)`, `bulletins.services.assiduite_depuis_presences(...)`.

## 5.5.22 — 2026-10-27

### Sécurité (audit — Lot A)
- Formulaire d'inscription : les trois points JSON (niveau et cycle d'une classe, code d'un statut) exigent désormais une session ouverte.
- Saisie des notes → sélection de la classe : limitée aux classes de l'établissement de l'utilisateur (elle listait toutes les classes de tous les établissements pour les non-enseignants).

### Qualité
- Module Manuels scolaires exécuté par la CI (`testpaths`) avec 13 tests : catalogue, cloisonnement par établissement, exemplaires, attribution/retour, non-rendus, PDF.
- Dépôt : l'outillage de développement IA (`.claude/`, `opencode/`, `skills/`, `plans/`, `yelen-school-bulletin-annuel/`, 70 fichiers) n'est plus versionné.

## 5.5.21 — 2026-10-27

### Corrigé
- Signature du directeur, cachet (Identité de l'établissement) et signature scannée des signataires : un scan de plus de 512 Ko était refusé (« L'image est trop volumineuse. Taille maximale : 0.5 Mo »). Ces images sont acceptées jusqu'à 5 Mo comme toute image de l'application, puis automatiquement ramenées à 800 px et ré-encodées (PNG si transparence, JPEG sinon) : fichiers légers dans les PDF, rien à redimensionner avant l'envoi.

## 5.5.20 — 2026-10-27

### Corrigé
- Bulletin de notes : une discipline dans laquelle l'élève n'avait aucune note disparaissait de son bulletin (seuls les élèves notés partout voyaient toutes les disciplines). Chaque bulletin liste désormais toutes les disciplines de la classe, dans le même ordre, avec « — » lorsque la moyenne n'existe pas ; la moyenne générale est inchangée.
- Les moyennes par discipline, les moyennes générales et les rangs sont recalculés automatiquement à chaque enregistrement de notes (saisie et import Excel) : les bulletins ne dépendent plus du dernier clic sur « Calculer les moyennes ».

## 5.5.19 — 2026-10-27

### Modifié
- Bulletins de notes (trimestriel et annuel) : un trait sépare désormais le titre de section (« Notes du trimestre », « Récapitulatif des moyennes ») de l'en-tête des colonnes du tableau.

## 5.5.18 — 2026-10-27

### Modifié
- Bulletin de notes trimestriel : l'en-tête des colonnes du tableau des notes (bandeau noir, texte blanc 7 pt) passe sur fond clair avec un texte sombre et net (7,5 pt, filet sous l'en-tête) ; même lisibilité appliquée au bulletin annuel. Le bulletin tient toujours sur une page A4.

## 5.5.17 — 2026-10-27

### Vérifié
- Les 43 documents PDF signés de l'application sont rendus réellement (WeasyPrint) avec le signataire configuré : fonction, NOM Prénom et signature scannée présents sur chacun (`core/tests/test_signataire_documents.py`). Tout nouveau document sans signataire fait échouer la suite.

### Corrigé
- Résolution du signataire : un signataire dont le membre du personnel a été supprimé laissait le document sans signature ; il est désormais ignoré au profit du candidat suivant (même document, même catégorie, même cycle, puis tout signataire actif).
- Circulaire : même résolution que les autres documents (signataire du cycle des classes destinataires) au lieu du premier signataire trouvé.

### Ajouté
- `python manage.py verifier_signataires` : affiche, par cycle et type de document, le signataire réellement imprimé, le repli utilisé et les anomalies (aucun signataire actif, membre supprimé, fichier de signature absent du disque, type référencé par un document mais absent du catalogue).

## 5.5.16 — 2026-10-26

### Corrigé
- `Paramètres → Signataires`, fenêtre « Modifier le signataire » : les listes Cycle, Catégorie de type de document et Nom et Prénom étaient vides (données jamais transmises au gabarit) — impossible de choisir un signataire ; elles sont renseignées et pré-sélectionnées.
- Fenêtre « Modifier le signataire » et page « Nouveau signataire » : la fonction choisie n'était pas enregistrée (champ posté sous un autre nom que celui lu par le formulaire) ; le document imprimait « Le Directeur » par défaut.

## 5.5.15 — 2026-10-26

### Corrigé
- Liste alphabétique du personnel d'un cycle : le bloc signataire restait vide alors que le directeur du cycle était configuré, dès lors que le type « Liste du Personnel » (`LISTE_PERSONNEL`) avait été désactivé, renommé ou supprimé dans `Paramètres → Types de documents` — le document s'arrêtait net. Tout document dont le type manque au catalogue se replie désormais sur le signataire configuré pour son cycle (puis sur le dernier signataire actif).
- `Configurer les Signataires` : un enregistrement refusé par le formulaire (titre honorifique trop long, membre hors établissement…) rechargeait la page sans un mot ; le motif est désormais affiché.

## 5.5.14 — 2026-10-26

### Corrigé
- Signataires : dix documents gardaient une case « Le Directeur » à signer à la main ou n'avaient aucune signature — le signataire configuré (fonction, signature scannée, NOM Prénom) ne pouvait pas y apparaître : contrat de travail, bulletin de salaire, bulletin de vacation, PV de conseil de classe, dossier de transfert, bulletin de compétences, liste des élèves (Inscriptions), liste des candidats, liste des boursiers, documents manuels scolaires (inventaire, attributions, non rendus). Tous l'impriment désormais ; la fiche de discipline porte la signature scannée de l'enseignant qui la certifie.
- Catalogue des types de documents : ajout de Dossier de Transfert, Liste des Candidats, Liste des Boursiers, Procès-Verbal de Conseil de Classe, Manuels Scolaires, Contrat de Travail, Bulletin de Salaire, Bulletin de Vacation (migration `parametres 0036`). Les types ajoutés reçoivent automatiquement, par cycle et année, le signataire déjà configuré pour leur catégorie ; à défaut de configuration, un document se replie sur le signataire de sa catégorie avant tout autre.
- Dossier de transfert : le PDF échouait (champ inexistant `nom_parent`) ; le parent/tuteur affiché est le tuteur, à défaut le père puis la mère.
- Garde-fou : la suite de tests refuse tout gabarit PDF sans signataire configuré (hors journal d'audit, avis Mobile Money, analyses indicatives et badge du personnel).

## 5.5.13 — 2026-10-26

### Corrigé
- Personnel › Exporter PDF (liste du personnel) : le document porte désormais le signataire configuré pour « Liste du Personnel » (fonction, signature scannée, NOM Prénom) ; ce gabarit n'avait aucun bloc signataire, contrairement à la liste du personnel du module Documents.

## 5.5.12 — 2026-10-26

### Corrigé
- Bulletins de vacation : « Valider » et « Marquer payé » provoquaient une erreur 500 pour tout utilisateur rattaché à un établissement (le contrôle d'établissement lisait un attribut inexistant du bulletin) ; le contrôle porte désormais sur l'année scolaire du bulletin. Les tests du module `vacations` sont ajoutés aux chemins de la suite (ils n'étaient exécutés ni en local ni en CI).

## 5.5.11 — 2026-10-26

### Corrigé
- PDF « Liste des élèves » (Élèves › Exporter PDF) : l'en-tête porte désormais le logo de l'établissement (et le cachet s'il est enregistré) ; la vue ne transmettait pas l'URL du logo au socle PDF.

## 5.5.10 — 2026-10-26

### Corrigé
- Plus aucun trait à l'emplacement de la signature du signataire : attestation de non-redevabilité, certificat de non-redevabilité (le libellé fixe « Le Responsable Financier » et son trait, en doublon du signataire configuré, sont retirés), emplois du temps de classe et de professeur, aperçu écran du certificat de scolarité (la signature scannée y remplace le trait). Les lignes à signer à la main par un tiers (récépissé du parent, contrat, bulletin de salaire, PV de conseil, dossier de transfert) sont conservées.

## 5.5.9 — 2026-10-26

### Corrigé
- Emplois du temps (classe et professeur) : le signataire imprimé (fonction, signature scannée, NOM Prénom) est celui configuré pour le type « Emploi du Temps » ; il n'existait pas et le dernier signataire enregistré sur le cycle, quel que soit son document, était utilisé.
- « Configurer les Signataires » propose dès l'installation tous les documents signés par l'application : Emploi du Temps, Convocation, Circulaire et Autorisation de Congé Personnel (auparavant absents jusqu'à la génération d'un premier document). Migration de données `parametres 0035`.

## 5.5.8 — 2026-10-26

### Corrigé
- Notes et moyennes toujours affichées avec deux décimales (16,00 et non 16 ou 16,0) : relevé de notes à l'écran (notes brutes, notes ramenées sur 20, moyennes de la classe, meilleure et plus basse moyenne, moyenne par évaluation), relevé de notes PDF, fiche discipline PDF et tableau des moyennes par discipline.

## 5.5.7 — 2026-10-26

### Corrigé
- Relevé de notes : un enseignant ne voit plus, dans la liste **Classe**, que les classes où il enseigne (année choisie) et, dans la liste **Discipline**, que ses propres disciplines ; un enseignement d'un collègue passé dans l'adresse est refusé (écran, PDF du relevé et fiche discipline). Direction et censeur conservent la vue complète.

## 5.5.6 — 2026-10-26

### Ajouté
- Carte scolaire (carte individuelle, cartes de classe et aperçu) : le **NOM** et le prénom du signataire sont imprimés sous sa signature, centrés sous la photo ; sans signature scannée, l'espace de 5 mm reste vierge au-dessus du nom. Mise en page de la carte inchangée.

## 5.5.5 — 2026-10-26

### Ajouté
- Carte scolaire (carte individuelle, cartes de classe et aperçu) : la signature scannée du signataire configuré pour la **Carte d'Identité Scolaire** (le directeur) est apposée sous la photo de l'élève, centrée, 5 mm de haut au plus ; la mise en page de la carte (85,6 × 54 mm) est inchangée et l'espace reste vierge sans signature enregistrée.

## 5.5.4 — 2026-10-26

### Corrigé
- Fenêtre « Nouveau type de document » / « Modifier le type de document » : la liste **Cycle** ne proposait que « Tous les cycles » (la vue ne transmettait pas les cycles au gabarit). Elle propose désormais les cycles de l'établissement, dans l'ordre configuré ; un cycle d'un autre établissement est refusé à l'enregistrement.

## 5.5.3 — 2026-10-26

### Corrigé
- Signature scannée du signataire absente de trois gabarits qui imprimaient sa fonction et son nom sans emplacement d'image : circulaire (partiel de signature partagé, également utilisé par la convocation sans bloc propre), emploi du temps de classe et emploi du temps du professeur. L'image occupe l'espace déjà réservé à la signature manuscrite (2 cm, 9 mm, 7 mm) : mise en page et nombre de pages inchangés.

## 5.5.2 — 2026-10-26

### Corrigé
- Signature scannée absente des documents de la catégorie Finance (reçu de paiement, certificat de non-redevabilité, historique des versements, listes et états, avis Mobile Money) ainsi que des PV de conseil, emplois du temps, listes de classe et du personnel, contrats et autorisations : ces PDF étaient rendus sans adresse de base et WeasyPrint ignorait l'URL relative de l'image (nom et fonction imprimés, signature manquante ; même cause pour le cachet de l'en-tête). `core.pdf.HTML` fournit désormais une base interne par défaut : les chemins `/media/` et `/static/` sont toujours résolus sur le disque.
- Relance de paiement : la signature scannée du signataire est apposée dans l'espace de 1 cm réservé entre sa fonction et son nom (mise en page et hauteur des coupons inchangées).

## 5.5.1 — 2026-10-26

### Corrigé
- Certificat de scolarité : le bloc QR code + signature et la barre du bas sont ancrés au bas de la page A5 (hors flux) ; le certificat ne peut plus déborder sur une deuxième page, quelle que soit la longueur de l'en-tête (nom de l'établissement, adresse, contacts), de la filiation ou de la fonction du signataire. Test de rendu réel en pire cas.

## 5.5.0 — 2026-10-26

### Ajouté
- Signataires des documents : champ facultatif **Signature scannée** dans la fenêtre « Configurer les Signataires » (PNG/JPEG, 512 Ko max., contrôle du contenu réel de l'image). L'image est enregistrée sur la fiche du membre du personnel et apposée automatiquement à l'emplacement de sa signature sur tous les documents PDF qu'il signe (bulletins trimestriels et annuels, duplicata, certificats de scolarité, attestations, convocations, autorisations de congé, reçus, listes…), sans changer la hauteur des blocs de signature ; case « Retirer la signature ». Migration `personnel 0009`.


### Corrigé
- Bulletins (trimestriel, duplicata, lot, annuel) : pied de page « Établissement — Généré le JJ/MM/AAAA HH:MM — Document officiel — Toute falsification expose à des poursuites » à gauche, pagination à droite.
- Duplicata du bulletin trimestriel : le bandeau gris est fondu dans le sous-titre (« Duplicata officiel délivré le … — Ce document est une reproduction du bulletin original ») ; le duplicata tient désormais sur une page dans les mêmes conditions que l'original (test étendu).


### Corrigé
- Documents PDF (bulletins, certificats, listes…) : suppression du bandeau de pied de page « Licence PREMIUM — clé — … — Nj restants — YELEN SCHOOL v3.4 — … ». Le filigrane diagonal discret est conservé.


### Corrigé
- Bulletin trimestriel PDF (individuel, duplicata, lot) : chaque bulletin tient sur une seule page A4, y compris avec 16 matières, des noms d'enseignants longs, des sanctions, l'assiduité, l'appréciation du conseil avec mentions et le signataire. Mise en page compactée sans retirer d'information : marges 8/12/10/12 mm, identité de l'élève sur deux lignes, Assiduité et Statistiques côte à côte, colonnes du tableau des notes 25/7/10/9/14/24/11 % (largeurs fixes), mode dense automatique au-delà de 12 matières, bloc signature resserré. Limite documentée : bulletin primaire APC garanti jusqu'à ≈ 10 compétences évaluées.


### Corrigé
- Textes générés automatiquement (appréciation du conseil proposée sur le bulletin, bilan de classe, facteurs de risque et de prédiction) : les nombres s'écrivent à la française — « 11,14/20 », « 66,7 % » — et non « 11.14/20 ».

## 5.3.8 — 2026-10-25

### Corrigé
- Impression par lot des bulletins (trimestriels et annuels) : chaque bulletin est paginé à part — « Page 1 / 1 » sur chaque bulletin, et non « Page 3 / 60 ». Le lot reste un seul fichier PDF (un document WeasyPrint par élève, pages assemblées par `core.pdf.HTML.lot`).

## 5.3.7 — 2026-10-25

### Modifié
- Bulletin trimestriel PDF : la colonne « Signature » du tableau des notes est vide (plus de ligne pointillée en face du nom de chaque professeur) ; l'en-tête de colonne est conservé.

## 5.3.6 — 2026-10-25

### Modifié
- Bulletin trimestriel PDF : colonne « Professeur » élargie (15 % → 21 %) aux dépens de la colonne « Appréciation » (19 % → 13 %) pour les noms et prénoms longs ; largeurs des autres colonnes inchangées, toujours une page par élève.

## 5.3.5 — 2026-10-25

### Corrigé
- Bulletin annuel : la moyenne annuelle est la moyenne des moyennes trimestrielles imprimées sur les bulletins, arrondie au centime supérieur comme elles (avec un seul trimestre saisi, l'annuel est identique au trimestre : 11,63 et non 11,62). Même règle pour le rang, les statistiques de classe et le palmarès annuel ; une moyenne trimestrielle de 0,00 s'imprime au lieu de « — ».

## 5.3.4 — 2026-10-25

- Bulletin trimestriel : légende du code QR supprimée ; « Mentions / distinctions » placées en dernière
  position de la carte « Appréciation du conseil de classe » (après l'appréciation) — idem aperçu écran
  et consultation parent.

## 5.3.3 — 2026-10-25

- Bulletin annuel (individuel et lot) : code QR dans la zone des signatures, sans légende — matricule,
  classe, année scolaire, moyenne annuelle (balise `qr_bulletin_annuel`).

## 5.3.2 — 2026-10-25

- Bulletins trimestriels (individuel, duplicata, classe) : code QR de vérification dans la zone des
  signatures — matricule, classe, trimestre + année, moyenne du trimestre (balise `qr_bulletin`).

## 5.3.1 — 2026-10-25

- Bulletin annuel (individuel et lot de classe) : le N° Agrément s'imprime sous le nom de l'établissement,
  comme sur les bulletins trimestriels.

## 5.3.0 — 2026-10-25

- Nouveau référentiel `Paramètres → Mentions / distinctions` (code, libellé, description, ordre, active ;
  droit d'accès dédié) amorcé avec Félicitations, Tableau d'honneur, Encouragements, Avertissement, Blâme.
- Saisie du bulletin : les mentions actives sont proposées en cases à cocher et enregistrées sur la fiche
  (élève × trimestre) ; badges dans le tableau de classe, impression sur les bulletins trimestriels
  (individuel, duplicata, classe), l'aperçu et la consultation parent.
- Migrations : `parametres 0034`, `bulletins 0006`.

## 5.2.9 — 2026-10-25

- Bulletins trimestriels (individuel, duplicata, classe, aperçu) : impression de la fiche saisie dans
  `Bulletins → Saisir` — carte « Assiduité du trimestre » (absences justifiées, absences non justifiées en
  heures, retards ; 0 sans fiche) et appréciation du conseil de classe saisie, prioritaire sur le commentaire
  généré automatiquement (conservé en repli). Libellé « Appréciation du conseil de classe » aligné sur la modale.

## 5.2.8 — 2026-10-25

### Modifié
- Bulletins trimestriels : le duplicata et le PDF de classe (un élève par page) reprennent exactement le modèle du bulletin individuel, désormais partagé (style et corps en `pedagogie/pdf/partials/`).
- En-tête des bulletins trimestriels : le N° Agrément de l'établissement apparaît sous son nom.

### Corrigé
- Sanctions disciplinaires : l'enregistrement échouait en production (journal d'audit) — représentation textuelle corrigée (`type_sanction` est une relation).

## 5.2.7 — 2026-10-24

### Corrigé
- Bulletins trimestriels (individuel, duplicata, classe) : dans le tableau des matières, la colonne « Rang » est remplacée par « Note pond. » = moyenne /20 × coefficient ; « — » si l'élève est dispensé. Le rang général de l'élève reste affiché dans le récapitulatif.
- Aperçu du bulletin à l'écran : la colonne « Points », restée vide, affiche désormais la même note pondérée.

## 5.2.6 — 2026-10-24

- Bulletins d'une classe : la colonne Actions (5 % de la largeur) rognait trois des quatre boutons ;
  largeurs de colonnes revues, les quatre boutons sont visibles dès 1280 px et passent à la ligne
  en dessous au lieu d'être coupés.

## 5.2.5 — 2026-10-24

- Bulletins trimestriels PDF : le total de points est rapporté au maximum possible (coefficients × 20),
  par exemple « 112,00 / 140 » ; le bulletin de classe affichait la somme des coefficients (« / 7,00 »).

## 5.2.4 — 2026-10-24

- `mettre-a-jour.bat` : la reconstruction de l'image échouait (« failed to get console: The handle is
  invalid ») car la progression interactive de Docker n'a pas de console quand la sortie est journalisée ;
  `--progress plain` sur les reconstructions (mise à jour et retour arrière).

## 5.2.3 — 2026-10-24

- Aperçu du bulletin : les boutons « Générer le PDF » / « Télécharger le PDF » renvoyaient une page
  introuvable (adresse écrite à la main) ; adresses désormais résolues par nom de route, retour de
  l'aperçu annuel corrigé.

## 5.2.2 — 2026-10-24

- Relance de paiement (PDF) : ligne « Contact parent » retirée du coupon.

## 5.2.1 — 2026-10-24

- Relance de paiement (PDF) : le signataire apparaît de nouveau — type de document « Relance de Paiement »
  (catégorie Finance) ajouté aux signataires configurables, signataires Finance existants repris
  (migration `parametres 0033`), résolution avec repli identique aux autres documents.

## 5.2.0 — 2026-10-24

- Performance : index de base de données sur les tables métier (appels et présences par date/statut,
  paiements par date, élèves par nom) — migrations `presences 0005`, `finances 0021`, `inscriptions 0019`.
- Accessibilité : lien d'évitement, états des menus (`aria-expanded`, `aria-current`), noms accessibles des
  boutons icône, étiquettes de champs, dialogues de confirmation au clavier, focus visible, animations
  réduites sur demande.
- Aide en ligne : le guide d'utilisation est consultable dans l'application (`/aide/`, sommaire latéral,
  captures d'écran, bouton **Aide** contextuel dans le menu) ; guide : blocs de code et structure du
  chapitre 6 corrigés.

## 5.1.0 — 2026-10-23

- Mise à jour en un clic : `mettre-a-jour.bat` (sauvegarde chiffrée, récupération GitHub, reconstruction,
  redémarrage, contrôle de `/health/`, retour arrière automatique ; journal `logs\mise-a-jour.log`).
- Version unique lue dans `VERSION` : menu latéral, page de connexion, `/health/`.
- Fin du Ctrl+F5 après mise à jour : cache du Service Worker nommé par version et rechargement
  automatique des pages ouvertes dès que le nouveau worker prend le contrôle.
- Gabarits PDF : socle commun (`templates/pdf/base.html`) et en-tête d'établissement unique.
- Qualité : seuil de couverture 65 %, exceptions journalisées, dépendances Dependabot alignées.

## 5.0 — versions antérieures

Historique dans `git log` et dans le guide d'utilisation (§33).
