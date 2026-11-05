"""Classe d'affectation de l'enseignant (5.55.0) : sélection dans la fenêtre « Ajouter un membre », puis
signature des bulletins de notes et de la liste alphabétique de sa classe."""
from datetime import date

import pytest
from django.template import Context, Template
from django.urls import reverse
from model_bakery import baker

from personnel.forms import MembrePersonnelForm
from personnel.models import MembrePersonnel

pytestmark = pytest.mark.django_db


@pytest.fixture
def ecole(client):
    etab = baker.make('etablissements.Etablissement', nom='LE SAVOIR', code='SAV')
    autre = baker.make('etablissements.Etablissement', nom='AUTRE', code='AUT')
    cycle = baker.make('parametres.Cycle', etablissement=etab, code='PRIM', nom='Primaire', ordre=1)
    classe = baker.make('parametres.Classe', etablissement=etab, cycle=cycle, nom='CP1', niveau='CP1')
    ailleurs = baker.make('parametres.Classe', etablissement=autre,
                          cycle=baker.make('parametres.Cycle', etablissement=autre, code='PRIM', nom='Primaire'),
                          nom='CP2', niveau='CP2')
    baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2026-2027', est_courante=True,
               date_debut=date(2026, 10, 1), date_fin=date(2027, 6, 30))
    user = baker.make('accounts.User', etablissement=etab, role='DIRECTEUR', must_change_password=False)
    client.force_login(user)
    return {'etab': etab, 'autre': autre, 'cycle': cycle, 'classe': classe, 'ailleurs': ailleurs, 'client': client}


def _donnees(ecole, **extra):
    base = {
        'qualite_affectation': 'TITULAIRE',
        'nom': 'OUEDRAOGO', 'prenom': 'Awa', 'genre': 'F', 'date_naissance': '1990-01-01',
        'lieu_naissance': 'Ouagadougou', 'nationalite': 'Burkinabè', 'fonction': 'Enseignant',
        'date_embauche': '2026-09-01', 'situation_matrimoniale': 'CELIBATAIRE', 'nombre_enfants': 0,
        'etablissement': ecole['etab'].pk, 'cycles': [ecole['cycle'].pk],
        'classe_affectation': ecole['classe'].pk,
    }
    base.update(extra)
    return base


# ── Fenêtre « Ajouter un membre » ───────────────────────────────────────────

def test_la_fenetre_ajouter_un_membre_propose_la_classe_d_affectation(ecole):
    page = ecole['client'].get(reverse('personnel:create'))
    assert page.status_code == 200
    html = page.content.decode()
    assert 'name="classe_affectation"' in html
    assert 'CP1' in html and 'CP2' not in html          # classes de l'établissement uniquement
    # même section du formulaire : après les cycles, avant le bloc « Contact »
    assert html.index('Cycles d') < html.index('name="classe_affectation"') < html.index('Contact &amp; Adresse')

    form = page.context['form']
    assert list(form.fields['classe_affectation'].queryset) == [ecole['classe']]


def test_creation_d_un_enseignant_avec_sa_classe(ecole):
    reponse = ecole['client'].post(reverse('personnel:create'), _donnees(ecole))
    assert reponse.status_code == 302
    membre = MembrePersonnel.objects.get(nom='OUEDRAOGO')
    assert membre.classe_affectation == ecole['classe']
    assert ecole['classe'].enseignant_titulaire == membre


def test_classe_d_un_autre_etablissement_refusee(ecole):
    form = MembrePersonnelForm(_donnees(ecole, classe_affectation=ecole['ailleurs'].pk),
                               etablissement=ecole['etab'])
    assert not form.is_valid()
    assert 'classe_affectation' in form.errors


def test_agent_sans_classe_accepte(ecole):
    donnees = _donnees(ecole, fonction='Secrétaire', classe_affectation='')
    reponse = ecole['client'].post(reverse('personnel:create'), donnees)
    assert reponse.status_code == 302
    assert MembrePersonnel.objects.get(nom='OUEDRAOGO').classe_affectation is None


def test_la_classe_s_efface_proprement_quand_le_membre_est_supprime(ecole):
    membre = baker.make('personnel.MembrePersonnel', etablissement=ecole['etab'], classe_affectation=ecole['classe'],
                        nom='ZONGO', prenom='Paul')
    classe_pk = ecole['classe'].pk
    membre.delete()
    assert ecole['classe'].__class__.objects.filter(pk=classe_pk).exists()   # la classe survit au départ de l'agent


# ── Signature : bulletins et liste alphabétique ────────────────────────────

def _rendre(gabarit, contexte):
    return Template('{% load signataire_tags %}' + gabarit).render(Context(contexte))


def test_le_titulaire_signe_le_bulletin_et_la_liste_de_sa_classe(ecole):
    baker.make('personnel.MembrePersonnel', etablissement=ecole['etab'], nom='KABORE', prenom='Salif',
               fonction='Enseignant', classe_affectation=ecole['classe'])
    baker.make('personnel.MembrePersonnel', etablissement=ecole['etab'], nom='DIRECTRICE', prenom='Awa',
               classe_affectation=ecole['classe'], is_active=False)      # un agent désactivé ne signe pas

    html = _rendre('{% signataire_classe as bloc %}{{ bloc }}', {'classe': ecole['classe']})
    assert 'KABORE Salif' in html and 'DIRECTRICE' not in html
    assert 'Enseignant titulaire' in html        # échappement HTML de l'apostrophe

    # Contexte d'un bulletin : la classe est portée par l'inscription.
    inscription = baker.make('inscriptions.Inscription', classe=ecole['classe'])
    html = _rendre('{% signataire_classe as bloc %}{{ bloc }}', {'inscription': inscription})
    assert 'KABORE Salif' in html


def test_sans_titulaire_le_document_est_signe_comme_avant(ecole):
    sortie = _rendre('{% signataire_classe as bloc %}{{ bloc }}', {'classe': ecole['classe']})
    assert sortie.strip() == ''
    # Aucun contexte de classe (liste globale des élèves) : pas de bloc non plus.
    assert _rendre('{% signataire_classe as bloc %}{{ bloc }}', {}).strip() == ''


# ── Suppléant de la classe : second signataire des bulletins (5.56.0) ───────

def test_titulaire_et_suppleant_signent_tous_deux_le_bulletin(ecole):
    baker.make('personnel.MembrePersonnel', etablissement=ecole['etab'], nom='KABORE', prenom='Salif',
               fonction='Enseignant', classe_affectation=ecole['classe'], qualite_affectation='TITULAIRE')
    baker.make('personnel.MembrePersonnel', etablissement=ecole['etab'], nom='SAWADOGO', prenom='Aline',
               fonction='Enseignante', classe_affectation=ecole['classe'], qualite_affectation='SUPPLEANT')

    assert ecole['classe'].enseignant_titulaire.nom == 'KABORE'
    assert ecole['classe'].enseignant_suppleant.nom == 'SAWADOGO'

    blocs = _rendre('{% signataires_classe as blocs %}{% for bloc in blocs %}[{{ bloc }}]{% endfor %}',
                    {'classe': ecole['classe']})
    assert blocs.count('[') == 2                          # deux colonnes de signature
    assert 'KABORE Salif' in blocs and 'SAWADOGO Aline' in blocs
    assert 'Enseignant titulaire' in blocs and 'Enseignant suppléant' in blocs
    assert blocs.index('KABORE') < blocs.index('SAWADOGO')          # titulaire en premier

    # Sans suppléant : un seul bloc, comme avant.
    ecole['classe'].enseignants_titulaires.filter(qualite_affectation='SUPPLEANT').delete()
    assert len(_rendre('{% signataires_classe as blocs %}{{ blocs|length }}', {'classe': ecole['classe']})) == 1


def test_suppleant_desactive_ne_signe_pas(ecole):
    baker.make('personnel.MembrePersonnel', etablissement=ecole['etab'], nom='KABORE', prenom='Salif',
               classe_affectation=ecole['classe'], qualite_affectation='TITULAIRE')
    baker.make('personnel.MembrePersonnel', etablissement=ecole['etab'], nom='SAWADOGO', prenom='Aline',
               classe_affectation=ecole['classe'], qualite_affectation='SUPPLEANT', is_active=False)
    assert ecole['classe'].enseignant_suppleant is None
    blocs = _rendre('{% signataires_classe as blocs %}{{ blocs|length }}', {'classe': ecole['classe']})
    assert blocs == '1'


def test_qualite_du_suppleant_enregistree_depuis_la_fiche(ecole):
    reponse = ecole['client'].post(reverse('personnel:create'),
                                   _donnees(ecole, nom='SAWADOGO', prenom='Aline',
                                            qualite_affectation='SUPPLEANT'))
    assert reponse.status_code == 302
    membre = MembrePersonnel.objects.get(nom='SAWADOGO')
    assert (membre.classe_affectation, membre.qualite_affectation) == (ecole['classe'], 'SUPPLEANT')


def test_le_suppleant_ne_signe_pas_la_liste_alphabetique(ecole):
    """La liste alphabétique reste signée par le titulaire, pas par le suppléant."""
    baker.make('personnel.MembrePersonnel', etablissement=ecole['etab'], nom='SAWADOGO', prenom='Aline',
               classe_affectation=ecole['classe'], qualite_affectation='SUPPLEANT')
    html = _rendre('{% signataire_classe as bloc %}{{ bloc }}', {'classe': ecole['classe']})
    assert html.strip() == ''


def test_la_liste_alphabetique_pdf_porte_la_signature_du_titulaire(ecole, mocker):
    """Bout en bout : le PDF de la liste alphabétique d'une classe signée par son titulaire."""
    maitre = baker.make('personnel.MembrePersonnel', etablissement=ecole['etab'], nom='KABORE', prenom='Salif',
                        fonction='Enseignant', classe_affectation=ecole['classe'])
    eleve = baker.make('inscriptions.Eleve', genre='M', date_naissance=date(2015, 1, 1))
    baker.make('inscriptions.Inscription', eleve=eleve, classe=ecole['classe'],
               annee_scolaire=ecole['etab'].annees_scolaires.first())

    weasy = mocker.patch('core.pdf.HTML')
    weasy.return_value.write_pdf.return_value = b'%PDF-1.7 test'
    url = reverse('documents:liste_classe_pdf', kwargs={'classe_id': ecole['classe'].pk})
    assert ecole['client'].get(url + '?format=pdf').status_code == 200

    html = weasy.call_args.kwargs['string']
    assert 'KABORE Salif' in html and 'Enseignant titulaire' in html
    assert maitre.pk and ecole['classe'].nom in html


def test_la_liste_alphabetique_sans_titulaire_est_inchangee(ecole, mocker):
    """Sans classe d'affectation renseignée, le document ne porte pas de bloc supplémentaire."""
    eleve = baker.make('inscriptions.Eleve', genre='F', date_naissance=date(2015, 1, 1))
    baker.make('inscriptions.Inscription', eleve=eleve, classe=ecole['classe'],
               annee_scolaire=ecole['etab'].annees_scolaires.first())

    weasy = mocker.patch('core.pdf.HTML')
    weasy.return_value.write_pdf.return_value = b'%PDF-1.7 test'
    url = reverse('documents:liste_classe_pdf', kwargs={'classe_id': ecole['classe'].pk})
    assert ecole['client'].get(url + '?format=pdf').status_code == 200
    assert 'Enseignant titulaire' not in weasy.call_args.kwargs['string']
