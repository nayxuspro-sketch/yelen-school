"""Assistant IA (moteur local) : intentions, extraction, requêtes limitées à l'établissement, formats, vue."""
from datetime import date
from decimal import Decimal

import pytest
from django.urls import reverse
from model_bakery import baker

from core import chatbot

pytestmark = pytest.mark.django_db


@pytest.fixture
def monde():
    """Deux établissements : les réponses ne doivent jamais mélanger leurs données."""
    etab, autre = baker.make('etablissements.Etablissement', nom='LE SAVOIR'), baker.make('etablissements.Etablissement', nom='AILLEURS')
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=True, libelle='2026-2027',
                       date_debut=date(2026, 10, 1), date_fin=date(2027, 6, 30))
    annee_autre = baker.make('parametres.AnneeScolaire', etablissement=autre, est_courante=True,
                             date_debut=date(2026, 10, 1), date_fin=date(2027, 6, 30))
    cycle = baker.make('parametres.Cycle', etablissement=etab, nom='Collège', code='SEC')
    classe = baker.make('parametres.Classe', etablissement=etab, cycle=cycle, nom='6e A', niveau='6e', actif=True)
    statut = baker.make('parametres.StatutEleve')
    rubrique = baker.make('parametres.RubriquePaiement', etablissement=etab, code='SCOL', actif=True)
    baker.make('parametres.TarifScolarite', etablissement=etab, classe=classe, annee_scolaire=annee, statut_eleve=statut,
               rubrique=rubrique, montant=100000, actif=True)
    awa = baker.make('inscriptions.Inscription', classe=classe, annee_scolaire=annee, statut_eleve=statut, statut='AFFECTE',
                     eleve__nom='OUEDRAOGO', eleve__prenom='Awa', eleve__matricule='M001', eleve__date_naissance=date(2014, 5, 3))
    issa = baker.make('inscriptions.Inscription', classe=classe, annee_scolaire=annee, statut_eleve=statut, statut='AFFECTE',
                      eleve__nom='TRAORE', eleve__prenom='Issa', eleve__matricule='M002', eleve__date_naissance=date(2014, 1, 9))
    baker.make('inscriptions.Inscription', classe=classe, annee_scolaire=annee, statut_eleve=statut, statut='ABANDON',
               eleve__nom='PARTI', eleve__prenom='Tôt', eleve__date_naissance=date(2014, 1, 9))
    baker.make('inscriptions.Inscription', classe__etablissement=autre, classe__nom='6e A', annee_scolaire=annee_autre,
               statut='AFFECTE', eleve__nom='OUEDRAOGO', eleve__prenom='Fanta', eleve__date_naissance=date(2014, 1, 9))
    baker.make('finances.Paiement', inscription=awa, rubrique=rubrique, montant=100000)
    baker.make('finances.Paiement', inscription=issa, rubrique=rubrique, montant=40000)
    t1, t2 = (baker.make('pedagogie.Trimestre', annee_scolaire=annee, numero=n, nom=f'T{n}',
                         date_debut=date(2026, 10, 1), date_fin=date(2027, 6, 30)) for n in (1, 2))
    for ins, m1, m2 in ((awa, '14.50', '15.25'), (issa, '9.80', '7.90')):
        baker.make('pedagogie.MoyenneGenerale', inscription=ins, trimestre=t1, moyenne=Decimal(m1),
                   moyenne_sur_20=Decimal(m1))
        baker.make('pedagogie.MoyenneGenerale', inscription=ins, trimestre=t2, moyenne=Decimal(m2),
                   moyenne_sur_20=Decimal(m2))
    a1, a2 = (baker.make('presences.Appel', classe=classe, annee_scolaire=annee, date=date(2026, 11, j)) for j in (3, 4))
    baker.make('presences.Presence', appel=a1, inscription=issa, statut='ABSENT')
    baker.make('presences.Presence', appel=a2, inscription=issa, statut='ABSENT')
    baker.make('presences.Presence', appel=a1, inscription=awa, statut='EXCUSE')
    baker.make('presences.Presence', appel=a2, inscription=awa, statut='PRESENT')
    return {'etab': etab, 'autre': autre, 'annee': annee, 'classe': classe, 'awa': awa, 'issa': issa}


@pytest.mark.parametrize('message, intention', [
    ('Quel est le taux de recouvrement ?', 'finances'),
    ('Combien d\'élèves par classe ?', 'effectifs'),
    ('Résumé des absences de la 6e A', 'absences'),
    ('Élèves sous 8/20 en 6e A', 'difficultes'),
    ('Élèves en baisse ce trimestre', 'progression'),
    ('Moyennes de la 6e A au trimestre 2', 'moyennes'),
    ('Cherche l\'élève Ouedraogo', 'eleve'),
    ('Comment générer un bulletin ?', 'guide'),
    ('mot de passe oublié', 'guide'),
    ('Bonjour', 'inconnu'),
])
def test_intentions(message, intention):
    assert chatbot._intent(message) == intention


def test_extraction():
    assert chatbot._extract_classe('moyennes de la 3ème B svp') == '3ème B'
    assert chatbot._extract_classe('effectif Terminale D') == 'Terminale D'
    assert chatbot._extract_classe('cm2') == 'cm2' and chatbot._extract_classe('bonjour') is None
    assert chatbot._extract_trimestre('trimestre 2') == 2 and chatbot._extract_trimestre('au T3') == 3
    assert chatbot._extract_trimestre('premier trimestre') == 1 and chatbot._extract_trimestre('rien') is None
    assert chatbot._extract_seuil('sous 8,5/20') == 8.5 and chatbot._extract_seuil('inférieure à 12') == 12.0
    assert chatbot._extract_seuil('faibles') == 10.0
    assert chatbot._extract_nom("cherche l'élève Ouedraogo Awa") == ('Ouedraogo', 'Awa')
    assert chatbot._extract_nom('fiche de Traore') == ('Traore', None)
    assert chatbot._extract_nom('Sawadogo ?') == ('Sawadogo', None) and chatbot._extract_nom('rien ici') == (None, None)


def test_effectifs_et_isolation(monde):
    texte = chatbot._process('Combien d\'élèves par classe ?', monde['etab'])
    assert 'Effectifs 2026-2027 — 2 élèves inscrits' in texte and '6e A (Collège) : 2 élèves' in texte, 'abandon et autre établissement exclus'
    assert chatbot._req_effectifs(monde['autre'])['total'] == 1
    assert chatbot._process('combien d\'inscrits', baker.make('etablissements.Etablissement')) == \
        'Données indisponibles : Aucune année scolaire courante configurée.'


def test_finances_coherentes_avec_le_module_finances(monde):
    d = chatbot._req_finances(monde['etab'])
    assert (d['attendu'], d['encaisse'], d['taux'], d['nb_payes'], d['nb_retard']) == (200000, 140000, 70.0, 1, 1)
    texte = chatbot._process('Quel est le taux de recouvrement ?', monde['etab']).replace('\u202f', ' ').replace('\xa0', ' ')
    assert 'Montant attendu   : 200 000 FCFA' in texte and 'Taux de recouvrement : 70.0 %' in texte and 'Élèves à jour : 1/2' in texte
    assert chatbot._req_finances(monde['autre'])['attendu'] == 0
    assert 'montant attendu inconnu' in chatbot._fmt_finances(chatbot._req_finances(monde['autre']))


def test_absences(monde):
    texte = chatbot._process('Résumé des absences', monde['etab'])
    assert "Taux d'assiduité : 25.0 %" in texte and 'Absences non justifiées : 2   |   Justifiées (excusées) : 1' in texte
    assert '1. TRAORE Issa (6e A) — 2 absence(s)' in texte
    assert 'Aucune présence enregistrée' in chatbot._fmt_absences(chatbot._req_absences(monde['autre']))


def test_difficultes_moyennes_et_progression(monde):
    texte = chatbot._process('Élèves sous 8/20 en 6e A', monde['etab'])
    assert 'moyenne < 8.0/20 (Trimestre 2)' in texte and 'TRAORE Issa (6e A) : 7.9/20' in texte and 'OUEDRAOGO' not in texte
    assert 'Aucun élève sous ce seuil.' in chatbot._process('élèves sous 5/20 au trimestre 1', monde['etab'])

    texte = chatbot._process('Moyennes de la 6e A au T1', monde['etab'])
    assert 'Moyennes — 6e A | Trimestre 1' in texte and 'Moyenne de la classe : 12.15/20   |   Max : 14.5/20   |   Min : 9.8/20' in texte
    assert 'Meilleurs élèves' in texte and 'Élèves sous 10/20 :\n  • TRAORE Issa : 9.8/20' in texte
    assert chatbot._process('moyennes de la 6e A', monde['etab']).startswith('Moyennes — 6e A | Trimestre 2')
    assert chatbot._process('moyennes de la', monde['etab']) == 'Précisez la classe, par exemple : « Moyennes de la 3ème A ».'
    assert 'introuvable ou sans inscrits' in chatbot._process('moyennes de la 4ème C', monde['etab'])

    texte = chatbot._process('Élèves en baisse', monde['etab'])
    assert '1 élève(s)' in texte and '▼ TRAORE Issa (6e A) : 9.8/20 (T1) → 7.9/20 (T2) (-1.90)' in texte
    texte = chatbot._process('Élèves en hausse', monde['etab'])
    assert '▲ OUEDRAOGO Awa (6e A) : 14.5/20 (T1) → 15.25/20 (T2) (+0.75)' in texte
    assert 'Aucun élève en hausse' in chatbot._process('élèves en hausse', monde['autre'])


def test_recherche_eleve_dans_l_etablissement_seulement(monde):
    texte = chatbot._process("Cherche l'élève Ouedraogo", monde['etab']).replace('\u202f', ' ').replace('\xa0', ' ')
    assert '1 élève(s) trouvé(s)' in texte and 'OUEDRAOGO Awa  (matricule : M001)' in texte and 'Fanta' not in texte
    assert 'Classe : 6e A — 2026-2027' in texte and 'Statut : Affecté' in texte
    assert 'Dernière moyenne (T2) : 15.25/20' in texte and 'Total payé : 100 000 FCFA' in texte
    assert chatbot._process('cherche Zzzz', monde['etab']) == 'Aucun élève trouvé avec ce nom ou prénom dans la base de données.'
    assert chatbot._fmt_eleve(chatbot._req_eleve(monde['etab'])) == 'Recherche impossible : Fournissez au moins un nom ou un prénom.'


def test_guide_et_aide(monde, mocker):
    assert chatbot._process('Comment générer un bulletin ?', monde['etab']).startswith(chatbot._search_guide('bulletin')['réponse'][:20])
    assert chatbot._process('Bonjour', monde['etab']) == chatbot._AIDE
    assert chatbot._search_guide('zzzz') is None
    mocker.patch('core.chatbot._search_guide', return_value=None)
    assert 'Je n\'ai pas trouvé de réponse précise' in chatbot._process('comment xyzxyz ?', monde['etab'])


def test_erreur_journalisee_sans_fuite(monde, mocker):
    mocker.patch('core.chatbot._req_effectifs', side_effect=RuntimeError('secret interne'))
    texte = chatbot._process('combien d\'inscrits', monde['etab'])
    assert texte.startswith('Une erreur est survenue') and 'secret' not in texte


def test_chat_conserve_vingt_messages(monde):
    historique = [{'role': 'user', 'text': 'x'}] * 19
    reponse, maj = chatbot.chat(historique, 'Bonjour', monde['etab'])
    assert reponse == chatbot._AIDE and len(maj) == 20 and maj[-1] == {'role': 'assistant', 'text': chatbot._AIDE}


def test_vue_reservee_a_la_direction(client, monde):
    url = reverse('core:chatbot')
    client.force_login(baker.make('accounts.User', role='ENSEIGNANT', etablissement=monde['etab'], must_change_password=False))
    assert client.get(url).status_code == 403
    client.force_login(baker.make('accounts.User', role='DIRECTEUR', etablissement=monde['etab'], must_change_password=False))
    assert client.get(url).status_code == 200
    reponse = client.post(url, {'message': "Combien d'élèves par classe ?"}, HTTP_HX_REQUEST='true')
    assert '2 élèves inscrits' in reponse.content.decode()
    assert len(client.session['chatbot_display']) == 2
    assert client.post(url, {'action': 'clear'}).status_code == 302 and 'chatbot_display' not in client.session
