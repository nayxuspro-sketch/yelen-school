# Skill 01 — Django Models Expert

## Rôle
Tu es expert en modèles Django pour YELEN SCHOOL.
Chaque modèle que tu crées respecte ces règles sans exception.

## Règles obligatoires

### Héritage
- TOUS les modèles héritent de `BaseModel` (core/models.py)
- BaseModel contient : id (UUID), created_at, updated_at, is_active

### Champs
- Matricule élève    : BF-AAAA-NNNNN — généré auto dans save(), jamais modifiable
- Matricule personnel: PERS-AAAA-NNNNN — même logique
- Âge               : PropertyField calculé depuis date_naissance, jamais stocké
- Monnaie           : DecimalField en FCFA, max_digits=12, decimal_places=0
- Notes             : DecimalField sur 20, max_digits=4, decimal_places=2

### Relations
- ForeignKey toujours avec on_delete explicite
- related_name toujours défini
- verbose_name et verbose_name_plural toujours en français

### Meta
- ordering défini sur chaque modèle
- verbose_name en français
- constraints pour les unicités métier

### Migrations
- Une migration par feature
- Jamais de RunPython sans reverse_code