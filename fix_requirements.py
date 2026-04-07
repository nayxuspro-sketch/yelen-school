content = open('requirements/base.txt', encoding='utf-16').read()
packages = [p.strip() for p in content.strip().splitlines() if p.strip()]
if 'xhtml2pdf' not in '\n'.join(packages):
    packages.append('xhtml2pdf==0.2.17')
packages.sort(key=str.lower)
open('requirements/base.txt', 'w', encoding='utf-8', newline='\n').write('\n'.join(packages) + '\n')
print('OK - xhtml2pdf ajouté, encodage corrigé en UTF-8')
print(f'Total: {len(packages)} packages')
