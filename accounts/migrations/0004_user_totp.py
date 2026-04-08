from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_add_eleves_lies'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='totp_secret',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Secret base32 pour la double authentification (TOTP).',
                max_length=64,
                verbose_name='Secret TOTP',
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='totp_enabled',
            field=models.BooleanField(
                default=False,
                help_text='Authentification à deux facteurs via application TOTP.',
                verbose_name='2FA activée',
            ),
        ),
    ]
