with open('pedagogie/models.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix unique_together in Resultat
# The field is 'enseigment' not 'enseigment'
content = content.replace(
    "unique_together = [['inscription', 'enseigment', 'periode']]",
    "unique_together = [['inscription', 'enseigment', 'periode']]"
)

# Also fix __str__
content = content.replace(
    "self.enseigment.matiere",
    "self.enseigment.matiere"
)

with open('pedagogie/models.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done")
