from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_add_notification'),
    ]

    operations = [
        migrations.AddField(
            model_name='notification',
            name='sms_envoye',
            field=models.BooleanField(default=False, verbose_name='SMS envoyé'),
        ),
    ]
