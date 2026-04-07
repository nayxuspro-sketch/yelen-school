import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('E:/yelen-school/parametres/views.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if 'def rubric_form' in line:
        print(f'Line {i+1}: {repr(line)}')