# -*- coding: utf-8 -*-
with open('viescolaire/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the field lookup - use correct FK field name
content = content.replace('ensemble_id__in=issements_ids', 'ensemble__in=issements')

with open('viescolaire/views.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed!')