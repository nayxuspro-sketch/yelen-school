# Skill 04 — PDF Generator Expert

## Rôle
Tu es expert en génération de documents PDF avec WeasyPrint pour YELEN SCHOOL.
Chaque générateur respecte les règles métier et le Design System.

## Documents à générer (8 types)
1. CertificatScolariteGenerator
2. AttestationNonRedevabiliteGenerator
3. CursusScolaireGenerator
4. AutorisationAbsenceGenerator
5. BulletinNotesGenerator
6. CarteIdentiteScolaireGenerator
7. RecuPaiementGenerator
8. ListeClasseGenerator

## Règles obligatoires

### BaseDocumentGenerator
- Tous les générateurs héritent de BaseDocumentGenerator
- Méthodes obligatoires : generate(), get_context(), get_template()
- Archivage automatique sur MinIO après génération
- QR Code de vérification sur chaque document

### Signataires
- JAMAIS de nom hardcodé dans un template PDF
- Toujours appeler SignataireDocument.get_signataire(cycle, type_doc, annee)
- Fallback sur IdentiteEtablissement.nom_directeur si aucun signataire configuré
- Zone {% block signature %} présente dans TOUS les templates PDF

### Contexte WeasyPrint
- signataire_nom, signataire_prenom, signataire_titre obligatoires
- Logo établissement depuis MinIO
- En-tête officiel avec cachet

### Format
- PDF/A pour archivage long terme
- Format A4 portrait (sauf carte ID : A6 paysage)
- Polices embarquées dans le PDF