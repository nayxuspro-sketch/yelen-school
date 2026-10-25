import pytest
from django.urls import reverse
from model_bakery import baker


@pytest.mark.django_db
class TestBulletinsViews:
    def test_index_redirect_anon(self, client):
        url = reverse('bulletins:index')
        response = client.get(url)
        assert response.status_code == 302

    def test_index_logged_in(self, client):
        etab = baker.make('etablissements.Etablissement')
        user = baker.make('accounts.User', etablissement=etab)
        client.force_login(user)
        url = reverse('bulletins:index')
        response = client.get(url)
        assert response.status_code == 200

    def test_index_sans_etablissement(self, client):
        user = baker.make('accounts.User', etablissement=None)
        client.force_login(user)
        url = reverse('bulletins:index')
        response = client.get(url)
        assert response.status_code == 200


@pytest.mark.django_db
def test_bulletin_annuel_pdf_une_page_a5_portrait(client, mocker):
    """Le bulletin annuel (individuel et lot de classe) tient sur une page A5 portrait par élève."""
    import datetime
    from decimal import Decimal
    import core.pdf
    from parametres.models import TypeDocument

    documents, sources = [], []

    class HTMLEspion(core.pdf.HTML):
        def __init__(self, *args, **kwargs):
            sources.append(kwargs.get('string', ''))
            super().__init__(*args, **kwargs)

        def write_pdf(self, target=None, **kwargs):
            document = self.render()
            documents.append(document)
            return document.write_pdf(target, **kwargs)

    mocker.patch('bulletins.views.HTML', HTMLEspion)

    etab = baker.make('etablissements.Etablissement', nom='LE SAVOIR')
    baker.make('parametres.IdentiteEtablissement', etablissement=etab, nom_etablissement='COMPLEXE SCOLAIRE LE SAVOIR',
               devise='Discipline — Travail — Succès', adresse_complete='Secteur 15, Ouaga 2000', ville='Ouagadougou',
               telephone='+226 25 36 47 58', numero_agrement_mena='N°2024-0147/MENAPLN/SG/DGEPFIC')
    client.force_login(baker.make('accounts.User', is_superuser=True, role='SUPER_ADMIN', etablissement=etab))
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=True, libelle='2025-2026')
    cycle = baker.make('parametres.Cycle', etablissement=etab, code='POST', nom='Post-primaire')
    classe = baker.make('parametres.Classe', etablissement=etab, cycle=cycle, nom='6ème A')
    trimestres = [baker.make('pedagogie.Trimestre', annee_scolaire=annee, numero=i, nom=f'Trimestre {i}',
                             date_debut=datetime.date(2025, 10, 1), date_fin=datetime.date(2026, 6, 30)) for i in (1, 2, 3)]
    inscriptions = []
    for nom, prenom, base in (('OUEDRAOGO', 'Abdoul Rasmané', '13.5'), ('SAWADOGO', 'Mariam Rasmata', '9.25'), ('KABORE', 'Issouf', '11')):
        eleve = baker.make('inscriptions.Eleve', nom=nom, prenom=prenom, date_naissance=datetime.date(2012, 5, 12), photo='')
        inscription = baker.make('inscriptions.Inscription', eleve=eleve, classe=classe, annee_scolaire=annee)
        for k, trimestre in enumerate(trimestres):
            moyenne = Decimal(base) + Decimal(k) / 2
            baker.make('pedagogie.MoyenneGenerale', inscription=inscription, trimestre=trimestre, moyenne=moyenne,
                       total_points=moyenne * 24, total_coefficients=Decimal('24'))
        inscriptions.append(inscription)
    type_doc, _ = TypeDocument.objects.get_or_create(code='BULLETIN', defaults={'nom': 'Bulletin', 'actif': True})
    membre = baker.make('personnel.MembrePersonnel', etablissement=etab, nom='KABORE', prenom='Salimata')
    baker.make('parametres.SignataireDocument', cycle=cycle, type_document=type_doc, annee_scolaire=annee,
               membre_personnel_id=membre.id, fonction='Le Directeur des Études',
               titres_honorifiques=["Chevalier de l'Ordre du Mérite"], actif=True)

    individuel = client.get(reverse('bulletins:bulletin_annuel_pdf', kwargs={'inscription_id': inscriptions[0].pk, 'annee_pk': annee.pk}))
    lot = client.get(reverse('bulletins:bulletin_annuel_batch_pdf', kwargs={'class_id': classe.pk, 'annee_pk': annee.pk}))

    assert individuel.status_code == 200 and lot.status_code == 200 and len(documents) == 2
    assert len(documents[0].pages) == 1 and len(documents[1].pages) == 3   # un élève = une page
    # A5 portrait : 148 × 210 mm, soit 559,4 × 793,7 px CSS (WeasyPrint)
    for page in documents[0].pages + documents[1].pages:
        assert round(page.width) == 559 and round(page.height) == 794
    # N° Agrément sous le nom de l'établissement, sur l'individuel et sur chacun des 3 bulletins du lot
    agrement = 'N° Agrément : N°2024-0147/MENAPLN/SG/DGEPFIC</div>'
    assert sources[0].count(agrement) == 1 and sources[1].count(agrement) == 3
    assert sources[0].index('COMPLEXE SCOLAIRE LE SAVOIR</div>') < sources[0].index(agrement) < sources[0].index('Discipline — Travail — Succès')


@pytest.mark.django_db
def test_saisie_bulletin_mentions_distinctions(client):
    """La modale « Saisir » propose les mentions actives en cases à cocher et enregistre la sélection."""
    import re
    from parametres.models import Distinction
    from bulletins.models import Bulletin

    etab = baker.make('etablissements.Etablissement')
    client.force_login(baker.make('accounts.User', etablissement=etab, is_superuser=True, must_change_password=False))
    ins = baker.make('inscriptions.Inscription', classe__etablissement=etab)
    tri = baker.make('pedagogie.Trimestre', annee_scolaire=ins.annee_scolaire, nom='Trimestre 1', numero=1)
    baker.make(Distinction, code='INACTIVE', libelle='Mention désactivée', actif=False)
    felicitations = Distinction.objects.get(code='FELICITATIONS')
    tableau = Distinction.objects.get(code='TABLEAU_HONNEUR')
    url = reverse('bulletins:bulletin_saisir', kwargs={'inscription_id': ins.pk, 'trimestre_id': tri.pk})

    html = client.get(url, HTTP_HX_REQUEST='true').content.decode()
    cases = re.findall(r'<input type="checkbox" name="distinctions" value="([^"]+)"( checked)?>', html)
    assert len(cases) == 5 and not any(c[1] for c in cases), 'les 5 mentions amorcées, aucune cochée'
    assert 'Mention désactivée' not in html

    reponse = client.post(url, {
        'absences_justifiees': '2', 'absences_non_justifiees': '0', 'retards': '1',
        'appreciation_conseil': 'Très bon trimestre.', 'distinctions': [str(felicitations.pk), str(tableau.pk)],
    }, HTTP_HX_REQUEST='true')
    assert reponse.status_code == 204 and reponse.headers['HX-Trigger'] == 'bulletinUpdated'
    fiche = Bulletin.objects.get(inscription=ins, trimestre=tri)
    assert set(fiche.distinctions.values_list('code', flat=True)) == {'FELICITATIONS', 'TABLEAU_HONNEUR'}

    html = client.get(url, HTTP_HX_REQUEST='true').content.decode()
    assert html.count(' checked>') == 2

    # Tableau de classe : badges des mentions cochées
    html = client.get(reverse('bulletins:bulletins_classe', kwargs={'class_id': ins.classe.pk, 'trimestre_id': tri.pk})).content.decode()
    assert html.count('>Félicitations</span>') == 1 and 'Tableau d&#x27;honneur</span>' in html

    # Mention désactivée après coup : reste proposée (cochée) tant qu'elle est attribuée ; décochée → retirée
    Distinction.objects.filter(pk=tableau.pk).update(actif=False)
    html = client.get(url, HTTP_HX_REQUEST='true').content.decode()
    assert f'value="{tableau.pk}" checked>' in html
    reponse = client.post(url, {'absences_justifiees': '2', 'retards': '1', 'distinctions': [str(felicitations.pk)]}, HTTP_HX_REQUEST='true')
    assert reponse.status_code == 204
    assert list(fiche.distinctions.values_list('code', flat=True)) == ['FELICITATIONS']

    # Valeur forgée : erreur affichée dans la modale, pas d'erreur serveur
    reponse = client.post(url, {'absences_justifiees': '2', 'distinctions': ['pas-un-uuid']}, HTTP_HX_REQUEST='true')
    assert reponse.status_code == 200 and reponse.context['error']
