"""Fichier d'inscription des candidats (Excel) : colonnes officielles, contenu, filtre par centre, isolation."""
import datetime
from io import BytesIO

import openpyxl
import pytest
from django.urls import reverse
from model_bakery import baker

from examens.views import COLONNES_CANDIDATS


@pytest.fixture
def session_bac():
    etab = baker.make('etablissements.Etablissement', nom='LE SAVOIR')
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2025-2026', est_courante=True)
    classe = baker.make('parametres.Classe', etablissement=etab, cycle=baker.make('parametres.Cycle', etablissement=etab),
                        niveau='Terminale', nom='Tle D', est_classe_examen=True, type_examen='BAC', serie_bac='D')
    eleve = baker.make('inscriptions.Eleve', matricule='LS-2026-0042', nom='Ouédraogo', prenom='Awa Marie', genre='F',
                       date_naissance=datetime.date(2008, 4, 9), lieu_naissance='Koudougou', nationalite='Burkinabè',
                       nom_pere='Ouédraogo Issa', nom_mere='Kaboré Mariam', telephone_parent='70123456',
                       etablissement_origine='Lycée Zinda')
    inscription = baker.make('inscriptions.Inscription', eleve=eleve, classe=classe, annee_scolaire=annee, statut='AFFECTE', est_redoublant=True)
    session = baker.make('examens.SessionExamen', annee_scolaire=annee, type_examen='BAC', libelle='BAC 2026')
    centre = baker.make('examens.CentreExamen', session=session, nom='Lycée Philippe Zinda Kaboré', code_centre='C01')
    baker.make('examens.InscriptionExamen', session=session, inscription=inscription, centre=centre, numero_table='1042')
    autre = baker.make('inscriptions.Inscription', classe=classe, annee_scolaire=annee, statut='AFFECTE',
                       eleve=baker.make('inscriptions.Eleve', nom='Zongo', prenom='Ali', genre='M', date_naissance=datetime.date(2007, 12, 1)))
    baker.make('examens.InscriptionExamen', session=session, inscription=autre)
    return {'etab': etab, 'session': session, 'centre': centre}


def _lignes(reponse):
    return list(openpyxl.load_workbook(BytesIO(reponse.content)).active.iter_rows(values_only=True))


@pytest.mark.django_db
class TestFichierCandidats:
    def test_colonnes_et_contenu(self, client, session_bac):
        client.force_login(baker.make('accounts.User', role='CENSEUR', etablissement=session_bac['etab'], must_change_password=False))
        reponse = client.get(reverse('examens:candidats_session_xlsx', args=[session_bac['session'].pk]))
        assert reponse['Content-Disposition'].endswith('Candidats_BAC_2025-2026.xlsx"')
        lignes = _lignes(reponse)
        assert lignes[0][0] == "Fichier d'inscription des candidats — BAC 2026" and lignes[1][0].startswith('LE SAVOIR · 2025-2026 · BAC')
        assert list(lignes[3]) == COLONNES_CANDIDATS
        assert lignes[4] == (1, 'LS-2026-0042', 'OUÉDRAOGO', 'Awa Marie', 'F', '09/04/2008', 'Koudougou', 'Burkinabè',
                             'Tle D', 'BAC', 'D', 'Officiel', 'Oui', 'Ouédraogo Issa', 'Kaboré Mariam', '70123456',
                             'Lycée Zinda', 'Lycée Philippe Zinda Kaboré', '1042')
        assert lignes[5][:6] == (2, lignes[5][1], 'ZONGO', 'Ali', 'M', '01/12/2007') and lignes[5][17:] == (None, None)
        assert len(lignes) == 6

    def test_filtre_par_centre(self, client, session_bac):
        client.force_login(baker.make('accounts.User', role='CENSEUR', etablissement=session_bac['etab'], must_change_password=False))
        reponse = client.get(reverse('examens:candidats_session_xlsx', args=[session_bac['session'].pk]), {'centre': session_bac['centre'].pk})
        assert len(_lignes(reponse)) == 5
        html = client.get(reverse('examens:candidats_session', args=[session_bac['session'].pk])).content.decode()
        assert "Fichier d'inscription (Excel)" in html

    def test_autre_etablissement_refuse(self, client, session_bac):
        client.force_login(baker.make('accounts.User', role='CENSEUR', must_change_password=False,
                                      etablissement=baker.make('etablissements.Etablissement')))
        reponse = client.get(reverse('examens:candidats_session_xlsx', args=[session_bac['session'].pk]))
        assert reponse.status_code == 302 and reponse.url == reverse('examens:session_list')
