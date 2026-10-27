"""
Manuels scolaires — catalogue, exemplaires, attributions, retours, non-rendus, PDF.
Le module n'avait aucun test et n'était pas exécuté par la CI (absent de `testpaths`).
"""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
from django.urls import reverse
from model_bakery import baker

from manuels.models import AttributionManuel, ExemplaireManuel, ManuelScolaire

pytestmark = pytest.mark.django_db


@pytest.fixture
def monde(client):
    etab = baker.make('etablissements.Etablissement', nom='LE SAVOIR', code='SAV')
    autre = baker.make('etablissements.Etablissement', nom='AUTRE', code='AUT')
    user = baker.make('accounts.User', etablissement=etab, role='SECRETAIRE', must_change_password=False)
    client.force_login(user)
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2026-2027', est_courante=True,
                       date_debut=date(2026, 10, 1), date_fin=date(2027, 6, 30))
    cycle = baker.make('parametres.Cycle', etablissement=etab, code='SEC', nom='Secondaire')
    classe = baker.make('parametres.Classe', etablissement=etab, cycle=cycle, nom='6e A', actif=True)
    eleve = baker.make('inscriptions.Eleve', nom='TRAORE', prenom='Awa', photo='')
    inscription = baker.make('inscriptions.Inscription', eleve=eleve, classe=classe, annee_scolaire=annee, statut='ACTIF')
    manuel = baker.make(ManuelScolaire, etablissement=etab, titre='Mathématiques 6e', prix_remplacement=Decimal('4500'))
    etranger = baker.make(ManuelScolaire, etablissement=autre, titre='Manuel d\'ailleurs')
    return SimpleNamespace(client=client, user=user, etab=etab, annee=annee, classe=classe, inscription=inscription,
                           manuel=manuel, etranger=etranger)


@pytest.mark.parametrize('nom_url, kwargs', [
    ('manuels:catalogue', {}), ('manuels:manuel_create', {}), ('manuels:attributions_list', {}),
    ('manuels:attribution_create', {}), ('manuels:non_rendus', {}), ('manuels:attributions_annee_pdf', {}),
    ('manuels:non_rendus_pdf', {}), ('manuels:htmx_eleves', {}), ('manuels:htmx_exemplaires', {}),
])
def test_acces_reserve_aux_utilisateurs_connectes(client, nom_url, kwargs):
    reponse = client.get(reverse(nom_url, kwargs=kwargs))
    assert reponse.status_code == 302 and reverse('accounts:login') in reponse.url


def test_catalogue_creation_modification_suppression(monde):
    c = monde.client
    html = c.get(reverse('manuels:catalogue')).content.decode()
    assert 'Mathématiques 6e' in html and 'Manuel d&#x27;ailleurs' not in html, 'catalogue limité à l\'établissement'

    # Titre obligatoire
    reponse = c.post(reverse('manuels:manuel_create'), {'titre': '', 'prix_remplacement': '3000'})
    assert reponse.status_code == 200 and 'Le titre est obligatoire.' in reponse.content.decode()
    assert ManuelScolaire.objects.filter(etablissement=monde.etab).count() == 1

    # Création (prix saisi « 3 500 » accepté, FCFA sans décimales)
    reponse = c.post(reverse('manuels:manuel_create'), {
        'titre': 'Français 6e', 'auteur': 'Collectif', 'cycle': 'SECONDAIRE', 'classe': str(monde.classe.pk),
        'annee_edition': '2024', 'prix_remplacement': '3 500'})
    assert reponse.status_code == 302
    francais = ManuelScolaire.objects.get(titre='Français 6e')
    assert francais.etablissement == monde.etab and francais.prix_remplacement == Decimal('3500')
    assert francais.classe == monde.classe and francais.annee_edition == 2024

    # Modification puis suppression (POST obligatoire)
    c.post(reverse('manuels:manuel_edit', kwargs={'pk': francais.pk}), {'titre': 'Français 6e — 2e éd.', 'prix_remplacement': '4000'})
    francais.refresh_from_db()
    assert francais.titre == 'Français 6e — 2e éd.' and francais.prix_remplacement == Decimal('4000')
    assert c.get(reverse('manuels:manuel_delete', kwargs={'pk': francais.pk})).status_code == 405
    assert c.post(reverse('manuels:manuel_delete', kwargs={'pk': francais.pk})).status_code == 302
    francais.refresh_from_db()
    assert not francais.actif, 'retrait du catalogue = suppression logique'
    assert 'Français 6e' not in c.get(reverse('manuels:catalogue')).content.decode()


def test_manuel_d_un_autre_etablissement_inaccessible(monde):
    for nom_url in ('manuels:manuel_detail', 'manuels:manuel_edit'):
        assert monde.client.get(reverse(nom_url, kwargs={'pk': monde.etranger.pk})).status_code == 404
    assert monde.client.post(reverse('manuels:manuel_delete', kwargs={'pk': monde.etranger.pk})).status_code == 404
    assert ManuelScolaire.objects.filter(pk=monde.etranger.pk).exists()


def test_exemplaires_attribution_retour_et_non_rendus(monde):
    c = monde.client
    # Trois exemplaires d'un coup, codes uniques générés
    reponse = c.post(reverse('manuels:exemplaire_create', kwargs={'manuel_pk': monde.manuel.pk}),
                     {'etat': 'NEUF', 'annee_acquisition': '2026', 'nombre': '3'})
    assert reponse.status_code == 302
    exemplaires = list(ExemplaireManuel.objects.filter(manuel=monde.manuel).order_by('code_exemplaire'))
    assert len(exemplaires) == 3 and len({e.code_exemplaire for e in exemplaires}) == 3
    assert all(e.est_disponible for e in exemplaires)
    premier = exemplaires[0]

    # HTMX : élèves de la classe, exemplaires disponibles du manuel
    html = c.get(reverse('manuels:htmx_eleves'), {'classe': str(monde.classe.pk)}).content.decode()
    assert 'TRAORE' in html
    html = c.get(reverse('manuels:htmx_exemplaires'), {'manuel': str(monde.manuel.pk)}).content.decode()
    assert premier.code_exemplaire in html

    # Attribution
    donnees = {'exemplaire': str(premier.pk), 'inscription': str(monde.inscription.pk),
               'date_attribution': '2026-10-05', 'etat_sortie': 'NEUF'}
    assert c.post(reverse('manuels:attribution_create'), donnees).status_code == 302
    attribution = AttributionManuel.objects.get(exemplaire=premier)
    assert attribution.inscription == monde.inscription and not attribution.est_rendu
    premier.refresh_from_db()
    assert not premier.est_disponible

    # Le même exemplaire ne peut pas être attribué une seconde fois
    reponse = c.post(reverse('manuels:attribution_create'), donnees)
    assert reponse.status_code == 200 and 'déjà attribué' in reponse.content.decode()
    assert AttributionManuel.objects.filter(exemplaire=premier).count() == 1

    # Liste des attributions et des non-rendus de l'année
    assert premier.code_exemplaire in c.get(reverse('manuels:attributions_list')).content.decode()
    assert 'TRAORE' in c.get(reverse('manuels:non_rendus')).content.decode()

    # Retour : l'exemplaire redevient disponible et sort des non-rendus
    reponse = c.post(reverse('manuels:attribution_retour', kwargs={'pk': attribution.pk}),
                     {'date_retour': '2027-06-15', 'etat_retour': 'BON', 'observation': 'RAS'})
    assert reponse.status_code == 302
    attribution.refresh_from_db()
    assert attribution.est_rendu and attribution.etat_retour == 'BON' and attribution.date_retour == date(2027, 6, 15)
    assert premier.est_disponible
    assert 'TRAORE' not in c.get(reverse('manuels:non_rendus')).content.decode()


def test_pdf_inventaire_attributions_et_non_rendus(monde, mocker):
    weasy = mocker.patch('core.pdf.HTML')
    weasy.return_value.write_pdf.return_value = b'%PDF-1.7'
    exemplaire = baker.make(ExemplaireManuel, manuel=monde.manuel, etat='BON')
    baker.make(AttributionManuel, exemplaire=exemplaire, inscription=monde.inscription,
               date_attribution=date(2026, 10, 5), etat_sortie='BON')
    for nom_url, kwargs in (('manuels:inventaire_classe_pdf', {'classe_pk': monde.classe.pk}),
                            ('manuels:attributions_annee_pdf', {}), ('manuels:non_rendus_pdf', {})):
        reponse = monde.client.get(reverse(nom_url, kwargs=kwargs))
        assert reponse.status_code == 200 and reponse['Content-Type'] == 'application/pdf', nom_url
        html = weasy.call_args.kwargs['string']
        assert 'TRAORE' in html and exemplaire.code_exemplaire in html, nom_url
    assert monde.client.get(reverse('manuels:inventaire_classe_pdf', kwargs={'classe_pk': monde.etranger.pk})).status_code == 404


def test_facturer_un_non_rendu_emet_une_creance_et_le_retour_l_annule(monde):
    """« Facturer » n'enregistre plus un faux paiement : il émet une créance « Manuel non rendu » qui entre dans le
    reste à payer de l'élève ; le retour tardif du manuel l'annule."""
    from finances.models import Creance, Paiement
    from finances.views.commun import _calcul_situation_financiere
    c = monde.client
    exemplaire = baker.make(ExemplaireManuel, manuel=monde.manuel, code_exemplaire='MAT-0007')
    attribution = baker.make(AttributionManuel, exemplaire=exemplaire, inscription=monde.inscription,
                             date_attribution=date(2026, 10, 5), date_retour=None)
    facturer = reverse('manuels:facturer_non_rendu', kwargs={'pk': attribution.pk})

    reponse = c.post(facturer, follow=True)
    assert 'Créance de 4,500 FCFA émise' in reponse.content.decode()
    attribution.refresh_from_db()
    creance = Creance.objects.get(attribution_manuel=attribution)
    assert attribution.facture_genere and attribution.creance == creance
    assert (creance.origine, creance.montant, creance.rubrique.code, creance.rubrique.etablissement) == \
        ('MANUEL', 4500, 'MNR', monde.etab)
    assert creance.libelle == 'Manuel non rendu : Mathématiques 6e (MAT-0007)' and creance.emise_par == monde.user
    assert not Paiement.objects.filter(inscription=monde.inscription).exists(), 'aucun faux paiement, aucun reçu'
    assert _calcul_situation_financiere(monde.inscription)['reste_a_payer'] == 4500
    assert c.post(facturer).status_code == 404, 'une seule créance par attribution'
    assert 'Créance émise' in c.get(reverse('manuels:non_rendus')).content.decode()

    reponse = c.post(reverse('manuels:attribution_retour', kwargs={'pk': attribution.pk}),
                     {'date_retour': '2027-06-20', 'etat_retour': 'BON', 'observation': ''}, follow=True)
    assert 'est annulée' in reponse.content.decode()
    creance.refresh_from_db()
    assert not creance.actif and creance.observation == 'Manuel rendu le 20/06/2027'
    assert _calcul_situation_financiere(monde.inscription)['reste_a_payer'] == 0


def test_migration_convertit_les_faux_paiements_en_creances(monde):
    """Les « paiements » créés par l'ancien bouton Facturer deviennent des créances (annulées si le manuel a été
    rendu depuis) ; le faux paiement, immuable, est neutralisé par un remboursement et sa rubrique redevient
    encaissable."""
    from django.apps import apps
    from finances.models import Creance, Paiement, Remboursement
    from finances.views.commun import _calcul_situation_financiere, _payment_overage_errors
    from parametres.models import RubriquePaiement
    import importlib
    migration = importlib.import_module('manuels.migrations.0002_creance')
    rubrique = RubriquePaiement.objects.create(etablissement=monde.etab, code='MNR', nom='Manuel non rendu')
    ex1, ex2 = (baker.make(ExemplaireManuel, manuel=monde.manuel, code_exemplaire=code) for code in ('MAT-0101', 'MAT-0102'))
    perdu = baker.make(AttributionManuel, exemplaire=ex1, inscription=monde.inscription, date_attribution=date(2026, 10, 5),
                       date_retour=None, facture_genere=True)
    rendu = baker.make(AttributionManuel, exemplaire=ex2, inscription=monde.inscription, date_attribution=date(2026, 10, 5),
                       date_retour=date(2027, 6, 18), facture_genere=True)
    for attribution in (perdu, rendu):
        Paiement.objects.create(inscription=monde.inscription, rubrique=rubrique, montant=Decimal('4500'),
                                date_paiement=date(2027, 6, 10), mode_paiement='ESPECES',
                                observation=f"Manuel non rendu : Mathématiques 6e ({attribution.exemplaire.code_exemplaire})")
    vrai = Paiement.objects.create(inscription=monde.inscription, rubrique=rubrique, montant=Decimal('1000'),
                                   date_paiement=date(2027, 6, 11), mode_paiement='ESPECES', observation='Acompte')

    migration.convertir_faux_paiements(apps, None)

    assert Paiement.objects.filter(inscription=monde.inscription).count() == 3, 'un paiement comptabilisé reste'
    assert sorted(r.paiement.observation[-9:-1] for r in Remboursement.objects.filter(montant=4500)) == ['MAT-0101', 'MAT-0102']
    assert not Remboursement.objects.filter(paiement=vrai).exists()
    sit = _calcul_situation_financiere(monde.inscription)
    assert (sit['total_du'], sit['total_paye'], sit['reste_a_payer']) == (4500, 1000, 3500)
    assert _payment_overage_errors(monde.inscription, [(rubrique, Decimal('3500'), None)]) == []
    assert len(_payment_overage_errors(monde.inscription, [(rubrique, Decimal('3501'), None)])) == 1
    perdu.refresh_from_db()
    rendu.refresh_from_db()
    assert perdu.creance.actif and perdu.creance.montant == 4500 and perdu.creance.date_creance == date(2027, 6, 10)
    assert perdu.creance.observation.startswith('Reprise du faux paiement REC-')
    assert not rendu.creance.actif and rendu.creance.observation == 'Manuel rendu le 18/06/2027'
    assert Creance.objects.count() == 2
    migration.convertir_faux_paiements(apps, None)                      # rejouable sans doublon
    assert Creance.objects.count() == 2
