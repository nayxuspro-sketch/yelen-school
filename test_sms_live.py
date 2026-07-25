"""
Script de test fonctionnel live — Parent-SMS Direct
Lance les 6 scénarios contre le webhook de l'application en cours.
"""
import urllib.request
import json


def post_json(url, payload):
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode('utf-8'))


BASE = 'http://localhost:8000/communication/webhook/sms/'
HEADERS = {'Content-Type': 'application/json'}
PHONE_OK = '+22670048114'       # Parent de SALAM Kaboré
PHONE_BAD = '+22699999999'      # Numéro inconnu
MATRICULE = '01-2026-0002'

TESTS = [
    (
        'TEST 1 — AIDE (numéro quelconque)',
        {'phoneNumber': '+22600000000', 'message': 'AIDE'},
        {'expected_status': 'success', 'expected_in_response': 'Yelen - Commandes:'},
    ),
    (
        'TEST 2 — NOTE T2 (parent autorisé)',
        {'phoneNumber': PHONE_OK, 'message': f'NOTE {MATRICULE} T2'},
        {'expected_status': 'success', 'expected_in_response': '/20'},
    ),
    (
        'TEST 3 — ABS (parent autorisé)',
        {'phoneNumber': PHONE_OK, 'message': f'ABS {MATRICULE}'},
        {'expected_status': 'success', 'expected_in_response': 'absence'},
    ),
    (
        'TEST 4 — SOLDE (parent autorisé)',
        {'phoneNumber': PHONE_OK, 'message': f'SOLDE {MATRICULE}'},
        {'expected_status': 'success', 'expected_in_response': 'FCFA'},
    ),
    (
        'TEST 5 — NOTE (numéro NON autorisé)',
        {'phoneNumber': PHONE_BAD, 'message': f'NOTE {MATRICULE} T2'},
        {'expected_status': 'error', 'expected_in_response': 'pas autorise'},
    ),
    (
        'TEST 6 — Commande invalide',
        {'phoneNumber': PHONE_OK, 'message': 'BONJOUR'},
        {'expected_status': 'error', 'expected_in_response': 'invalide'},
    ),
]

passed = 0
failed = 0

print("\n" + "=" * 62)
print("   YELEN SCHOOL — Tests Fonctionnels Parent-SMS Direct")
print("=" * 62)

for titre, payload, expectations in TESTS:
    try:
        status_code, data = post_json(BASE, payload)

        http_ok = status_code == 200
        status_ok = data.get('status') == expectations['expected_status']
        content_ok = expectations['expected_in_response'].lower() in data.get('response', '').lower()
        ok = http_ok and status_ok and content_ok

        icon = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        else:
            failed += 1

        print(f"\n[{icon}]  {titre}")
        print(f"   HTTP         : {status_code}")
        print(f"   Status JSON  : {data.get('status')}")
        print(f"   Reponse SMS  : {data.get('response', '')}")
        if not ok:
            print(f"   [ATTENDU]    : status={expectations['expected_status']}, contient='{expectations['expected_in_response']}'")

    except Exception as e:
        failed += 1
        print(f"\n[FAIL]  {titre}")
        print(f"   ERREUR : {e}")

print("\n" + "=" * 62)
print(f"   RESULTATS : {passed} PASS / {failed} FAIL / {len(TESTS)} total")
print("=" * 62 + "\n")

# Afficher le journal d'audit
try:
    import django
    import os
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yelen_school.settings')
    django.setup()
    from communication.models import IncomingSMSLog
    logs = IncomingSMSLog.objects.order_by('-created_at')[:6]
    print("JOURNAL D'AUDIT (6 derniers SMS recus):")
    print("-" * 62)
    for log in logs:
        auth = "OUI" if log.is_authorized else "NON"
        ok = "OK " if log.processed_successfully else "ERR"
        print(f"  [{ok}] [{auth}] {log.command_type:<8} | {log.sender_number:<16} | {log.response_text[:50]}")
    print()
except Exception as e:
    print(f"(Audit log non disponible : {e})")
