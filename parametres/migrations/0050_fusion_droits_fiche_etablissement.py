from django.db import migrations


FONCTIONNALITE_UNIQUE = '/parametres/etablissement/'
ANCIENNE_IDENTITE = '/parametres/identite-etablissement/'


def _autorisation_par_defaut(DroitAcces, RolePersonnalise, alias, role):
    """Valeur de repli commune aux deux anciennes fonctionnalités."""
    base = RolePersonnalise.objects.using(alias).filter(code=role).values_list('base', flat=True).first()
    roles = [role]
    if base and base != role:
        roles.append(base)

    for candidat in roles:
        module = DroitAcces.objects.using(alias).filter(
            role=candidat, module='parametres', fonctionnalite='', action='',
        ).first()
        if module is not None:
            return module.autorise

    return (base or role) in {'DIRECTEUR', 'CENSEUR'}


def fusionner_droits(apps, schema_editor):
    """Regroupe les droits des deux anciennes pages sans retirer un accès auparavant disponible."""
    DroitAcces = apps.get_model('parametres', 'DroitAcces')
    RolePersonnalise = apps.get_model('parametres', 'RolePersonnalise')
    alias = schema_editor.connection.alias

    anciens = list(DroitAcces.objects.using(alias).filter(
        module='parametres', fonctionnalite=ANCIENNE_IDENTITE,
    ))
    for ancien in anciens:
        valeur_par_defaut = _autorisation_par_defaut(
            DroitAcces, RolePersonnalise, alias, ancien.role,
        )
        courant = DroitAcces.objects.using(alias).filter(
            role=ancien.role, module=ancien.module,
            fonctionnalite=FONCTIONNALITE_UNIQUE, action=ancien.action,
        ).first()

        if courant is not None:
            autorise = courant.autorise or ancien.autorise
            if courant.autorise != autorise:
                DroitAcces.objects.using(alias).filter(pk=courant.pk).update(autorise=autorise)
            ancien.delete(using=alias)
        elif valeur_par_defaut or not ancien.autorise:
            # La fiche unique reste accessible si l'une des deux anciennes pages l'était.
            # Une interdiction de l'ancienne identité ne doit pas écraser l'accès par défaut à Établissement.
            ancien.delete(using=alias)
        else:
            # Seul un ancien accès autorisé change le repli « refusé » et doit être conservé explicitement.
            DroitAcces.objects.using(alias).filter(pk=ancien.pk).update(
                fonctionnalite=FONCTIONNALITE_UNIQUE,
            )


def restaurer_droits(apps, schema_editor):
    """Au retour arrière, recrée une règle d'accès équivalente pour l'ancienne URL."""
    DroitAcces = apps.get_model('parametres', 'DroitAcces')
    alias = schema_editor.connection.alias
    for droit in DroitAcces.objects.using(alias).filter(
        module='parametres', fonctionnalite=FONCTIONNALITE_UNIQUE,
    ).iterator():
        DroitAcces.objects.using(alias).get_or_create(
            role=droit.role, module=droit.module,
            fonctionnalite=ANCIENNE_IDENTITE, action=droit.action,
            defaults={'autorise': droit.autorise},
        )


class Migration(migrations.Migration):

    dependencies = [
        ('parametres', '0049_directions_cycles_and_identity_labels'),
    ]

    operations = [
        migrations.RunPython(fusionner_droits, restaurer_droits),
    ]
