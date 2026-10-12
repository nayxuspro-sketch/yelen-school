"""Transfert de données : exporter_donnees → base vierge → importer_donnees."""
import io
import json
import zipfile
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.contrib.auth.models import Group, Permission
from django.core.management import CommandError, call_command
from django.test import override_settings
from model_bakery import baker

from accounts.models import User
from core.migration_donnees import MEMBRE_DONNEES, MEMBRE_MANIFESTE, effectifs_base
from core.models import AuditLog
from finances.models import Remboursement
from inscriptions.models import Eleve, Inscription
from licences.models import Licence, StatutLicence, TypeLicence
from parametres.models import TypeDocument

pytestmark = pytest.mark.django_db(transaction=True)


def _reecrire_manifeste(archive, modifier):
    with zipfile.ZipFile(archive) as zf:
        donnees = zf.read(MEMBRE_DONNEES)
        manifeste = json.loads(zf.read(MEMBRE_MANIFESTE))
    modifier(manifeste)
    with zipfile.ZipFile(archive, 'w') as zf:
        zf.writestr(MEMBRE_DONNEES, donnees)
        zf.writestr(MEMBRE_MANIFESTE, json.dumps(manifeste))


@pytest.fixture
def archive(tmp_path):
    """Jeu de données réaliste exporté, puis base vidée comme une installation cible vierge."""
    recu, _ = TypeDocument.objects.get_or_create(code='RECU_PAIEMENT', defaults={'libelle': 'Reçu de Paiement'})
    etab = baker.make('etablissements.Etablissement', code='TR', nom='Lycée Transfert')
    admin = baker.make('accounts.User', email='admin@transfert.bf', etablissement=etab, role='SUPER_ADMIN',
                       is_staff=True, is_superuser=True, must_change_password=False)
    admin.set_password('Transfert-2026!')
    admin.save()
    caisse = Group.objects.create(name='Caisse')
    caisse.permissions.add(Permission.objects.get(codename='view_paiement', content_type__app_label='finances'))
    admin.groups.add(caisse)
    caissier = baker.make('accounts.User', email='caisse@transfert.bf', etablissement=etab, created_by=admin)
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=True, libelle='2026-2027')
    cycle = baker.make('parametres.Cycle', etablissement=etab)
    classe = baker.make('parametres.Classe', etablissement=etab, cycle=cycle, niveau='6E', nom='6ème A')
    statut = baker.make('parametres.StatutEleve', etablissement=etab, nom='Non affecté')
    rubrique = baker.make('parametres.RubriquePaiement', etablissement=etab, actif=True, code='SCOL', nom='Scolarité')
    for eleve in baker.make('inscriptions.Eleve', _quantity=3, created_by=admin):
        inscription = baker.make('inscriptions.Inscription', eleve=eleve, classe=classe, annee_scolaire=annee,
                                 statut_eleve=statut, created_by=admin, updated_by=caissier)
    paiement = baker.make('finances.Paiement', inscription=inscription, rubrique=rubrique, statut_eleve=statut,
                          montant=Decimal('25000'), encaisse_par=caissier, created_by=caissier)
    baker.make('finances.Remboursement', paiement=paiement, montant=Decimal('5000'), motif='Trop-perçu',
               rembourse_par=caissier, created_by=caissier)
    Licence(etablissement=etab, type_licence=TypeLicence.STANDARD, statut=StatutLicence.ACTIVE,
            date_expiration=date.today() + timedelta(days=365)).save()
    AuditLog(user=admin, action='LOGIN', app_label='accounts', model_name='user',
             object_id=str(admin.pk), object_repr='admin').save()

    chemin = tmp_path / 'transfert.zip'
    call_command('exporter_donnees', str(chemin), stdout=io.StringIO())
    with zipfile.ZipFile(chemin) as zf:
        effectifs = json.loads(zf.read(MEMBRE_MANIFESTE))['effectifs']
    source = {
        'effectifs': effectifs,
        'eleves': set(Eleve.objects.values_list('pk', flat=True)),
        'inscription': (inscription.pk, inscription.updated_at),
        'recu_pk': recu.pk,
        'audit': list(AuditLog.objects.order_by('id').values_list('id', 'entry_hash')),
    }
    call_command('flush', interactive=False, verbosity=0)
    # Ce que `migrate` crée sur une base vierge : les types de documents (migrations de données).
    TypeDocument.objects.bulk_create([TypeDocument(code='RECU_PAIEMENT', libelle='Reçu de Paiement'),
                                      TypeDocument(code='CERT_SCOL', libelle='Certificat de Scolarité')])
    return chemin, source


class TestImporterDonnees:
    def test_restaure_tout_a_l_identique(self, archive):
        chemin, source = archive
        assert source['effectifs']['inscriptions.eleve'] == 3
        assert AuditLog.objects.count() == 0 and User.objects.count() == 0
        sortie = io.StringIO()

        call_command('importer_donnees', str(chemin), stdout=sortie)

        assert effectifs_base(source['effectifs']) == source['effectifs']
        assert set(Eleve.objects.values_list('pk', flat=True)) == source['eleves']
        inscription_pk, updated_at = source['inscription']
        assert Inscription.objects.get(pk=inscription_pk, updated_by__email='caisse@transfert.bf').updated_at == updated_at
        admin = User.objects.get(email='admin@transfert.bf')
        assert admin.check_password('Transfert-2026!')
        assert admin.groups.get(name='Caisse').permissions.filter(codename='view_paiement').exists()
        assert Remboursement.objects.get().paiement.montant == Decimal('25000')
        # Types de documents : ceux de la source remplacent ceux créés par migrate, sans doublon.
        assert TypeDocument.objects.get(code='RECU_PAIEMENT').pk == source['recu_pk']
        # Journal d'audit : identifiants et chaîne de hachage intacts, aucune entrée ajoutée par l'import.
        assert list(AuditLog.objects.order_by('id').values_list('id', 'entry_hash')) == source['audit']
        assert all(entree.verifier_chaine() for entree in AuditLog.objects.all())
        AuditLog(action='SECURITY', app_label='core', model_name='test', object_id='1', object_repr='séquence').save()
        assert Licence.objects.get().verifier_signature()
        assert 'effectifs conformes' in sortie.getvalue()
        assert 'Licences : 1 vérifiée(s)' in sortie.getvalue()

    def test_refuse_une_base_cible_non_vide(self, archive):
        chemin, _ = archive
        baker.make('accounts.User', email='autre@transfert.bf')

        with pytest.raises(CommandError, match=r'Base cible non vide : accounts\.user \(1\)'):
            call_command('importer_donnees', str(chemin), stdout=io.StringIO())
        assert Eleve.objects.count() == 0

    def test_refuse_des_cles_differentes(self, archive):
        chemin, _ = archive

        with override_settings(SECRET_KEY='une-autre-cle'), pytest.raises(CommandError, match='SECRET_KEY'):
            call_command('importer_donnees', str(chemin), stdout=io.StringIO())
        assert Eleve.objects.count() == 0

    def test_refuse_des_versions_differentes(self, archive):
        chemin, _ = archive
        _reecrire_manifeste(chemin, lambda m: m['migrations'].append('inscriptions.9999_future'))

        with pytest.raises(CommandError, match=r'Versions différentes.*inscriptions\.9999_future'):
            call_command('importer_donnees', str(chemin), stdout=io.StringIO())
        assert Eleve.objects.count() == 0

    def test_annule_tout_si_les_effectifs_divergent(self, archive):
        chemin, _ = archive
        _reecrire_manifeste(chemin, lambda m: m['effectifs'].__setitem__('inscriptions.eleve', 4))

        with pytest.raises(CommandError, match=r'Import annulé.*inscriptions\.eleve attendu 4 obtenu 3'):
            call_command('importer_donnees', str(chemin), stdout=io.StringIO())
        assert Eleve.objects.count() == 0 and User.objects.count() == 0


class TestExporterDonnees:
    def test_refuse_d_ecraser_un_fichier(self, tmp_path):
        chemin = tmp_path / 'existant.zip'
        chemin.write_bytes(b'')

        with pytest.raises(CommandError, match='existe déjà'):
            call_command('exporter_donnees', str(chemin), stdout=io.StringIO())
