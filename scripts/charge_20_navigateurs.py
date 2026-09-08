"""
scripts/charge_20_navigateurs.py — Test de charge de bout en bout
==================================================================

Simule N utilisateurs (par défaut 20), chacun avec son propre navigateur
(session + cookies), qui se connectent à l'application et enchaînent des
parcours réalistes PENDANT UNE DURÉE DONNÉE, en parallèle et sans pause
(bien plus agressif qu'un humain).

Parcours par rôle :
  - Enseignant  : accueil, liste élèves, saisie de notes (POST réel), consultation
  - Comptable   : liste paiements, recherche, enregistrement paiement (POST réel), reçus
  - Secrétaire  : recherche élèves, fiche élève, appel (présences)

Usage :
    python scripts/charge_20_navigateurs.py --url http://localhost:8000 --users 20 --duree 60
"""
import argparse
import random
import re
import statistics
import threading
import time
from collections import defaultdict
from http.cookiejar import CookieJar
from urllib import parse, request
from urllib.error import HTTPError, URLError

PWD = 'Yelen2026!'
RUBRIQUE_ID = ''  # renseigné au démarrage (rubrique 'Scolarité' de l'établissement de test)
REFLEXION = (0.0, 0.0)  # pause humaine min/max entre deux actions (s)
CSRF_RE = re.compile(r'name="csrfmiddlewaretoken" value="([^"]+)"')
UUID_RE = re.compile(r'/inscriptions/eleve/([0-9a-f-]{36})/')
EVAL_RE = re.compile(r'/pedagogie/evaluations/([0-9a-f-]{36})/saisie/')
CLASSE_RE = re.compile(r'/presences/appel/classe/([0-9a-f-]{36})/')
INS_RE = re.compile(r'/finances/situation/eleve/([0-9a-f-]{36})/')
INPUT_NOTE_RE = re.compile(r'name="note_([0-9a-f-]{36})"')

lock = threading.Lock()
stats = defaultdict(list)     # label -> [latences]
errors = defaultdict(int)     # label -> nb erreurs
error_samples = {}
stop_at = 0.0


class Navigateur:
    def __init__(self, base, email):
        self.base = base.rstrip('/')
        self.email = email
        self.jar = CookieJar()
        self.opener = request.build_opener(request.HTTPCookieProcessor(self.jar))
        self.opener.addheaders = [('User-Agent', 'YelenLoadTest/1.0')]
        self.rnd = random.Random(email)

    def _req(self, label, path, data=None, headers=None):
        url = self.base + path
        body = parse.urlencode(data).encode() if data is not None else None
        req = request.Request(url, data=body, headers=headers or {})
        if data is not None:
            req.add_header('Referer', url)
        t0 = time.perf_counter()
        try:
            with self.opener.open(req, timeout=120) as r:
                html = r.read().decode('utf-8', 'replace')
                code = r.status
        except HTTPError as e:
            html, code = e.read().decode('utf-8', 'replace'), e.code
        except URLError as e:
            html, code = str(e), 0
        dt = time.perf_counter() - t0
        with lock:
            stats[label].append(dt)
            if code >= 400 or code == 0:
                errors[label] += 1
                error_samples.setdefault(label, (code, html[:300]))
        if REFLEXION[1] > 0:
            time.sleep(self.rnd.uniform(*REFLEXION))  # temps de lecture / saisie de l'utilisateur
        return code, html

    def get(self, label, path):
        return self._req(label, path)

    def post(self, label, path, data):
        csrf = next((c.value for c in self.jar if c.name == 'csrftoken'), '')
        data = {'csrfmiddlewaretoken': csrf, **data}
        return self._req(label, path, data)

    def login(self):
        _, html = self.get('login GET', '/accounts/login/')
        m = CSRF_RE.search(html)
        data = {'username': self.email, 'password': PWD}
        if m:
            data['csrfmiddlewaretoken'] = m.group(1)
        code, html = self._req('login POST', '/accounts/login/', data)
        return code == 200 and 'logout' in html.lower() or 'connexion' not in html.lower()

    # ── Parcours ──────────────────────────────────────────────────────────
    def parcours_enseignant(self):
        self.get('accueil', '/')
        _, html = self.get('liste élèves', '/inscriptions/')
        _, html = self.get('liste évaluations', '/pedagogie/evaluations/')
        evals = EVAL_RE.findall(html)
        if evals:
            ev = self.rnd.choice(evals[:200])
            _, page = self.get('saisie notes GET', f'/pedagogie/evaluations/{ev}/saisie/')
            ids = INPUT_NOTE_RE.findall(page)
            if ids:
                data = {f'note_{i}': f'{self.rnd.uniform(5, 19):.2f}' for i in ids}
                self.post('saisie notes POST (≈38 notes)', f'/pedagogie/evaluations/{ev}/saisie/', data)
        self.get('recherche élève', f'/inscriptions/?q={self.rnd.choice(["OUEDRAOGO", "KDG-2026-0", "Aminata", "ZONGO"])}')

    def parcours_comptable(self):
        self.get('accueil', '/')
        _, html = self.get('liste paiements', '/finances/paiements/')
        self.get('recherche paiement', f'/finances/paiements/?q=KDG-2026-{self.rnd.randint(1, 1500):04d}')
        inscs = INS_RE.findall(html)
        if inscs:
            ins = self.rnd.choice(inscs[:300])
            self.get('situation élève', f'/finances/situation/eleve/{ins}/')
            _, form = self.get('paiement GET', '/finances/paiements/nouveau/')
            data = {'inscription': ins, 'mode_paiement': 'ESPECES', 'date_paiement': time.strftime('%Y-%m-%d'),
                    'observation': 'test de charge', 'rubrique_ids[]': RUBRIQUE_ID, 'montants[]': '5000',
                    'echeances[]': ''}
            self.post('paiement POST', '/finances/paiements/nouveau/', data)
        self.get('redevables', '/finances/redevables/')

    def parcours_secretaire(self):
        self.get('accueil', '/')
        _, html = self.get('recherche élève', f'/inscriptions/?q={self.rnd.choice(NOMS)}')
        ids = UUID_RE.findall(html)
        if ids:
            self.get('fiche élève', f'/inscriptions/eleve/{self.rnd.choice(ids[:100])}/')
        _, html = self.get('choix classe appel', '/presences/classes/')
        classes = CLASSE_RE.findall(html)
        if classes:
            self.get('appel classe', f'/presences/appel/classe/{self.rnd.choice(classes)}/')
        self.get('bulletins', '/bulletins/')

    def run(self, role):
        if not self.login():
            with lock:
                errors['login POST'] += 1
            return 0
        parcours = {'ENSEIGNANT': self.parcours_enseignant, 'COMPTABLE': self.parcours_comptable,
                    'SECRETAIRE': self.parcours_secretaire}[role]
        n = 0
        while time.time() < stop_at:
            parcours()
            n += 1
        return n


NOMS = ['OUEDRAOGO', 'SAWADOGO', 'KABORE', 'ZONGO', 'TRAORE', 'COMPAORE', 'ILBOUDO', 'NIKIEMA']


def main():
    global stop_at, RUBRIQUE_ID, REFLEXION
    ap = argparse.ArgumentParser()
    ap.add_argument('--url', default='http://localhost:8000')
    ap.add_argument('--users', type=int, default=20)
    ap.add_argument('--duree', type=int, default=60)
    ap.add_argument('--rubrique', default='', help='UUID de la rubrique de paiement (Scolarité)')
    ap.add_argument('--reflexion', default='0-0', help="Pause humaine entre actions, en s (ex. '5-15'). '0-0' = stress sans pause")
    args = ap.parse_args()
    RUBRIQUE_ID = args.rubrique
    REFLEXION = tuple(float(x) for x in args.reflexion.split('-'))

    roles = ['COMPTABLE', 'SECRETAIRE', 'SECRETAIRE'] + ['ENSEIGNANT'] * 17
    roles = (roles * ((args.users // 20) + 1))[:args.users]
    print(f"→ {args.users} navigateurs simultanés pendant {args.duree} s sur {args.url} — pause humaine {args.reflexion} s")
    print(f"  rôles : {roles.count('ENSEIGNANT')} enseignants, {roles.count('COMPTABLE')} comptable(s), {roles.count('SECRETAIRE')} secrétaires\n")

    stop_at = time.time() + args.duree
    results = [0] * args.users
    threads = []
    for i in range(args.users):
        nav = Navigateur(args.url, f'user{(i % 20) + 1:02d}@yelen.bf')

        def worker(idx=i, nav=nav, role=roles[i]):
            results[idx] = nav.run(role)
        t = threading.Thread(target=worker, daemon=True)
        threads.append(t)
        t.start()
        time.sleep(0.15)  # arrivée progressive des utilisateurs (3 s pour 20)
    t_start = time.time()
    for t in threads:
        t.join()
    duree = time.time() - t_start

    total = sum(len(v) for v in stats.values())
    total_err = sum(errors.values())
    print(f"{'Action':<34}{'Nb':>6}{'Erreurs':>9}{'Médiane':>10}{'p95':>10}{'Max':>10}")
    print('─' * 79)
    for label, lat in sorted(stats.items(), key=lambda kv: -statistics.median(kv[1])):
        lat_s = sorted(lat)
        p95 = lat_s[min(len(lat_s) - 1, int(len(lat_s) * 0.95))]
        print(f"{label:<34}{len(lat):>6}{errors[label]:>9}{statistics.median(lat) * 1000:>8.0f}ms{p95 * 1000:>8.0f}ms{lat_s[-1] * 1000:>8.0f}ms")
    print('─' * 79)
    print(f"Total : {total} requêtes HTTP en {duree:.0f} s → {total / duree:.1f} req/s soutenues, "
          f"{total_err} erreur(s) ({100 * total_err / max(total, 1):.2f} %)")
    print(f"Parcours complets réalisés : {sum(results)} (≈ {sum(results) / args.users:.1f} par utilisateur)")
    if error_samples:
        print("\nExemples d'erreurs :")
        for label, (code, body) in error_samples.items():
            print(f"  [{label}] HTTP {code} : {body[:200]!r}")


if __name__ == '__main__':
    main()
