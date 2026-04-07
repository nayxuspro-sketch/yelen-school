# Fix references to Periode

with open('pedagogie/models.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace Periode references with Trimestre
content = content.replace('Periode,', 'Trimestre,')
content = content.replace('periode =', 'trimestre =')
content = content.replace("periode',", "trimestre',")
content = content.replace("periode.", "trimestre.")
content = content.replace("'periode'", "'trimestre'")

with open('pedagogie/models.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done")

# Also fix admin.py
with open('pedagogie/admin.py', 'r', encoding='utf-8') as f:
    admin_content = f.read()

admin_content = admin_content.replace('periode', 'trimestre')
admin_content = admin_content.replace('Trimestre,', 'Trimestre,')
admin_content = admin_content.replace('Periode', 'Trimestre')

with open('pedagogie/admin.py', 'w', encoding='utf-8') as f:
    f.write(admin_content)

print("Admin done")
