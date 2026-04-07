# Fix pedagogie/models.py

with open('pedagogie/models.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace Periode with a simpler version that uses related_name
# Find and replace the Periode class
old_periode = '''
class Periode(BaseModel):
    """
    Périodes de l'année scolaire (Trimestres, Semestres).
    """
    
    class TypePeriodeChoices(models.TextChoices):
        TRIMESTRE = 'TRIMESTRE', _('Trimestre')
        SEMESTRE = 'SEMESTRE', _('Semestre')
    
    annee_scolaire = models.ForeignKey(
        'parametres.AnneeScolaire',
        on_delete=models.CASCADE,
        related_name='periodes_pedagogie',
        verbose_name=_("Année scolaire")
    )
    
    type_periode = models.CharField(
        max_length=20,
        choices=TypePeriodeChoices.choices,
        default=TypePeriodeChoices.TRIMESTRE,
        verbose_name=_("Type de période")
    )
    
    nom = models.CharField(
        max_length=50,
        verbose_name=_("Nom"),
        help_text=_("Ex: Trimestre 1, Semestre 1")
    )
    
    numero = models.IntegerField(
        default=1,
        verbose_name=_("Numéro")
    )
    
    date_debut = models.DateField(
        verbose_name=_("Date de début")
    )
    
    date_fin = models.DateField(
        verbose_name=_("Date de fin")
    )
    
    # Notes fermées pour cette période
    notes_saisies = models.BooleanField(
        default=False,
        verbose_name=_("Saisie des notes terminée")
    )
    
    date_fermeture = models.DateField(
        blank=True,
        null=True,
        verbose_name=_("Date de fermeture de la saisie")
    )
    
    class Meta:
        verbose_name = _("Période")
        verbose_name_plural = _("Périodes")
        ordering = ['annee_scolaire', 'numero']
        unique_together = [['annee_scolaire', 'numero']]
    
    def __str__(self):
        return f"{self.nom} - {self.annee_scolaire.libelle}"
'''

# We'll keep the Periode class but add a different related_name
# Actually, let me just fix the Periode to use a different related_name
# to avoid conflict with parametres.PeriodeEvaluation

# Replace the related_name in Periode
content = content.replace(
    "related_name='periodes_pedagogie'",
    "related_name='pedagogie_periodes'"
)

# Also need to fix admin.py to use the correct field names
# Let's see if there's an issue with the admin too

# First let's just check if the Periode model has an issue
# Actually, let's just rename Periode to Trimestre to avoid conflicts

# Replace Periode class name with Trimestre
content = content.replace('class Periode(BaseModel):', 'class Trimestre(BaseModel):')
content = content.replace('verbose_name = _("Période")', 'verbose_name = _("Trimestre")')
content = content.replace('verbose_name_plural = _("Périodes")', 'verbose_name_plural = _("Trimestres")')

with open('pedagogie/models.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done fixing models.py")

# Now fix admin.py to use Trimestre instead of Periode
with open('pedagogie/admin.py', 'r', encoding='utf-8') as f:
    admin_content = f.read()

admin_content = admin_content.replace('from .models import (', 'from .models import (\n    Trimestre,')
admin_content = admin_content.replace('Periode,', 'Trimestre,')
admin_content = admin_content.replace('@admin.register(Periode)', '@admin.register(Trimestre)')
admin_content = admin_content.replace('class PeriodeAdmin', 'class TrimestreAdmin')

with open('pedagogie/admin.py', 'w', encoding='utf-8') as f:
    f.write(admin_content)

print("Done fixing admin.py")
