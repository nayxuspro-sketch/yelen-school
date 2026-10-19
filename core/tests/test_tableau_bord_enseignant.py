"""Tableau de bord enseignant : « Évaluations récentes » affiche ses évaluations, lisibles."""
import datetime

import pytest
from model_bakery import baker


@pytest.mark.django_db
def test_evaluations_recentes_lisibles_et_limitees_a_l_enseignant(client):
    etab = baker.make('etablissements.Etablissement')
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=True)
    trimestre = baker.make('pedagogie.Trimestre', annee_scolaire=annee)
    cycle = baker.make('parametres.Cycle', etablissement=etab)
    classe = baker.make('parametres.Classe', etablissement=etab, cycle=cycle, nom='6ème A')
    matiere = baker.make('pedagogie.Matiere', nom='Mathématiques')
    moi = baker.make('personnel.MembrePersonnel', etablissement=etab, email='prof@ecole.bf')
    collegue = baker.make('personnel.MembrePersonnel', etablissement=etab, email='collegue@ecole.bf')
    mien = baker.make('pedagogie.Enseignement', annee_scolaire=annee, classe=classe, matiere=matiere,
                      personnel=moi, est_actif=True)
    sien = baker.make('pedagogie.Enseignement', annee_scolaire=annee, classe=classe, personnel=collegue, est_actif=True)
    baker.make('pedagogie.Evaluation', enseignement=mien, trimestre=trimestre, titre='Devoir n°1',
               date_planifiee=datetime.date(2026, 10, 12), statut='TERMINEE')
    baker.make('pedagogie.Evaluation', enseignement=sien, trimestre=trimestre, titre='Devoir du collègue',
               date_planifiee=datetime.date(2026, 10, 13))

    client.force_login(baker.make('accounts.User', etablissement=etab, role='ENSEIGNANT', email='PROF@ecole.bf',
                                  must_change_password=False))
    html = client.get('/').content.decode()

    assert 'Évaluations récentes' in html
    for attendu in ('Devoir n°1', '6ème A', 'Mathématiques', '12/10/2026', 'badge-success">Terminée'):
        assert attendu in html, attendu
    assert 'Devoir du collègue' not in html
    assert '<div class="stat-value">1</div><div class="stat-label">Enseignements</div>' in html
