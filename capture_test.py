import subprocess

with open('pytest_output.log', 'w', encoding='utf-8') as f:
    result = subprocess.run(
        [r'venv\Scripts\python.exe', 'manage.py', 'test', 'etablissements.tests.test_models'],
        capture_output=True,
        text=True,
        env={"DJANGO_SETTINGS_MODULE": "yelen_school.settings"}
    )
    f.write(result.stdout)
    f.write("\n--- STDERR ---\n")
    f.write(result.stderr)
