import subprocess
import os

env = os.environ.copy()
env['DJANGO_SETTINGS_MODULE'] = 'yelen_school.settings'

result = subprocess.run(
    [r'venv\Scripts\python.exe', 'manage.py', 'makemigrations', 'etablissements'],
    capture_output=True,
    text=True,
    env=env
)
with open('makemigrations_error.log', 'w', encoding='utf-8') as f:
    f.write(result.stderr)
