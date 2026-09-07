"""
Etablissement.cycles : ArrayField (PostgreSQL only) -> JSONField (portable).

- PostgreSQL : conversion réelle de la colonne varchar(20)[] vers jsonb, avec
  préservation des données (to_jsonb(array)). Rollback possible.
- SQLite / autres : la colonne a été créée directement en JSON par les migrations
  0002/0003 (voir _compat.py) ; seul l'état Django est mis à jour, sans toucher
  au schéma.
"""
from django.db import migrations, models

import etablissements.models

TABLE = 'etablissements_etablissement'


def array_to_jsonb(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    schema_editor.execute(f"ALTER TABLE {TABLE} ALTER COLUMN cycles DROP DEFAULT;")
    schema_editor.execute(
        f"ALTER TABLE {TABLE} ALTER COLUMN cycles TYPE jsonb "
        "USING COALESCE(to_jsonb(cycles), '[]'::jsonb);"
    )
    schema_editor.execute(f"ALTER TABLE {TABLE} ALTER COLUMN cycles SET DEFAULT '[]'::jsonb;")


def jsonb_to_array(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    # PostgreSQL n'accepte pas de sous-requête dans USING : on passe par une
    # fonction IMMUTABLE temporaire pour convertir jsonb -> varchar[].
    schema_editor.execute(
        "CREATE OR REPLACE FUNCTION pg_temp.yelen_jsonb_to_varchar_array(j jsonb) "
        "RETURNS varchar(20)[] LANGUAGE sql IMMUTABLE AS $$ "
        "SELECT COALESCE(ARRAY(SELECT jsonb_array_elements_text(j))::varchar(20)[], '{}'::varchar(20)[]) $$;"
    )
    schema_editor.execute(f"ALTER TABLE {TABLE} ALTER COLUMN cycles DROP DEFAULT;")
    schema_editor.execute(
        f"ALTER TABLE {TABLE} ALTER COLUMN cycles TYPE varchar(20)[] "
        "USING pg_temp.yelen_jsonb_to_varchar_array(cycles);"
    )
    schema_editor.execute(f"ALTER TABLE {TABLE} ALTER COLUMN cycles SET DEFAULT '{{}}';")


class Migration(migrations.Migration):

    dependencies = [
        ('etablissements', '0004_groupe_etablissements'),
    ]

    operations = [
        # 1. PostgreSQL uniquement : conversion physique de la colonne
        migrations.RunPython(array_to_jsonb, jsonb_to_array),
        # 2. Tous SGBD : mise à jour de l'état Django du champ (aucun DDL)
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name='etablissement',
                    name='cycles',
                    field=models.JSONField(
                        blank=True,
                        default=list,
                        validators=[etablissements.models.validate_cycles],
                        verbose_name='Cycles proposés',
                    ),
                ),
            ],
            database_operations=[],
        ),
    ]
