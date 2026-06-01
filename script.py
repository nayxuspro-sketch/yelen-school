import sys
with open(r'e:\yelen-school\core\templates\core\base.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()
# keep lines before <style> (lines 0 to 13) and lines after </style> (line 867 onwards)
new_lines = lines[:14] + lines[867:]
with open(r'e:\yelen-school\core\templates\core\base.html', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
