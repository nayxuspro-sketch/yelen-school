import os
from http.server import HTTPServer, BaseHTTPRequestHandler

FILES = {
    'app_zip': ('yelen-school-v5.0.zip', '/home/user/yelen-school/yelen-school-v5.0.zip', 'application/zip'),
    'zip': ('outils-editeur-anti-copie.zip', '/home/user/yelen-school/outils-editeur-anti-copie.zip', 'application/zip'),
    'docx_deploiement': ('GUIDE_DEPLOIEMENT_WINDOWS.docx', '/home/user/yelen-school/docs/GUIDE_DEPLOIEMENT_WINDOWS.docx', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'),
    'docx_utilisation': ('GUIDE_UTILISATION_YELEN_SCHOOL.docx', '/home/user/yelen-school/docs/GUIDE_UTILISATION_YELEN_SCHOOL.docx', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'),
    'bat_unlock': ('deverrouiller-dossier-anti-copie.bat', '/home/user/yelen-school/installer/outils-editeur/deverrouiller-dossier-anti-copie.bat', 'text/plain'),
}

class DownloadHandler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        for key, (filename, filepath, content_type) in FILES.items():
            if self.path in (f'/{filename}', f'/download/{key}'):
                if os.path.exists(filepath):
                    self.send_response(200)
                    self.send_header('Content-Type', content_type)
                    self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
                    self.send_header('Content-Length', str(os.path.getsize(filepath)))
                    self.send_header('Cache-Control', 'no-cache')
                    self.end_headers()
                    return
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()

    def do_GET(self):
        for key, (filename, filepath, content_type) in FILES.items():
            if self.path in (f'/{filename}', f'/download/{key}'):
                if not os.path.exists(filepath):
                    self.send_response(404)
                    self.end_headers()
                    self.wfile.write(b"Fichier introuvable.")
                    return
                with open(filepath, 'rb') as f:
                    data = f.read()
                self.send_response(200)
                self.send_header('Content-Type', content_type)
                self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
                self.send_header('Content-Length', str(len(data)))
                self.send_header('Cache-Control', 'no-cache')
                self.end_headers()
                self.wfile.write(data)
                return

        html = """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Centre de Téléchargement — YELEN SCHOOL v5.0</title>
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, sans-serif;
            background: #0B132B;
            color: #E2E8F0;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            margin: 0;
            padding: 24px;
        }
        .card {
            background: #1C2541;
            padding: 36px 32px;
            border-radius: 14px;
            box-shadow: 0 12px 30px rgba(0,0,0,0.5);
            max-width: 680px;
            width: 100%;
            border: 1px solid #3A506B;
        }
        .header {
            text-align: center;
            margin-bottom: 26px;
        }
        .badge {
            display: inline-block;
            background: #00A86B;
            color: #ffffff;
            font-size: 0.75rem;
            font-weight: 700;
            padding: 4px 12px;
            border-radius: 20px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 10px;
        }
        h1 {
            font-size: 1.6rem;
            margin: 0 0 8px 0;
            color: #6FFFE9;
        }
        p.subtitle {
            color: #94A3B8;
            font-size: 0.95rem;
            margin: 0;
        }
        .list {
            display: flex;
            flex-direction: column;
            gap: 14px;
        }
        .item {
            background: #0B132B;
            border: 1px solid #2B3A55;
            border-radius: 10px;
            padding: 16px 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            transition: border-color 0.2s, transform 0.15s;
        }
        .item-featured {
            background: #0d1b38;
            border: 1.5px solid #00A86B;
            box-shadow: 0 4px 15px rgba(0, 168, 107, 0.15);
        }
        .item:hover {
            border-color: #5BC0BE;
            transform: translateY(-2px);
        }
        .item-info {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }
        .item-title {
            font-weight: 600;
            font-size: 1rem;
            color: #F8FAFC;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .item-desc {
            font-size: 0.82rem;
            color: #94A3B8;
            line-height: 1.4;
        }
        .item-tag {
            display: inline-block;
            font-size: 0.7rem;
            padding: 2px 7px;
            border-radius: 4px;
            background: #2563EB33;
            color: #60A5FA;
            font-weight: 600;
        }
        .item-tag-green {
            background: #00A86B33;
            color: #4ADE80;
        }
        .btn {
            background: #00A86B;
            color: #FFFFFF;
            text-decoration: none;
            padding: 10px 18px;
            border-radius: 8px;
            font-weight: 600;
            font-size: 0.85rem;
            transition: all 0.2s;
            white-space: nowrap;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }
        .btn:hover {
            background: #008f5a;
            box-shadow: 0 4px 12px rgba(0, 168, 107, 0.35);
        }
        .btn-featured {
            background: #10B981;
            padding: 12px 22px;
            font-size: 0.92rem;
        }
        .btn-featured:hover {
            background: #059669;
            box-shadow: 0 4px 15px rgba(16, 185, 129, 0.45);
        }
        .btn-blue {
            background: #2563EB;
        }
        .btn-blue:hover {
            background: #1D4ED8;
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.35);
        }
        .btn-amber {
            background: #D97706;
        }
        .btn-amber:hover {
            background: #B45309;
            box-shadow: 0 4px 12px rgba(217, 119, 6, 0.35);
        }
        .footer {
            margin-top: 24px;
            text-align: center;
            font-size: 0.8rem;
            color: #64748B;
            border-top: 1px solid #2B3A55;
            padding-top: 16px;
        }
    </style>
</head>
<body>
    <div class="card">
        <div class="header">
            <span class="badge">Version 5.0 Déployée &bull; Prête</span>
            <h1>📦 Téléchargement YELEN SCHOOL v5.0</h1>
            <p class="subtitle">Téléchargez l'application complète, la suite d'outils et la documentation</p>
        </div>
        
        <div class="list">
            <!-- ARCHIVE COMPLÈTE DU PROJET -->
            <div class="item item-featured">
                <div class="item-info">
                    <span class="item-title">
                        🚀 Application Complète YELEN SCHOOL
                        <span class="item-tag item-tag-green">v5.0 &bull; ZIP (8.8 Mo)</span>
                    </span>
                    <span class="item-desc">Code source complet, migrations, triggers PostgreSQL, chaîne d'audit, suite installer/ et scripts Windows & Linux.</span>
                </div>
                <a class="btn btn-featured" href="/download/app_zip" download="yelen-school-v5.0.zip">⬇️ Télécharger l'App</a>
            </div>

            <!-- OUTILS EDITEUR -->
            <div class="item">
                <div class="item-info">
                    <span class="item-title">
                        🔐 Trousse Clé USB Anti-Copie
                        <span class="item-tag">Éditeur &bull; ZIP</span>
                    </span>
                    <span class="item-desc">Scripts confidentiels : enregistrement empreinte matérielle, verrouillage NTFS et déverrouillage maître.</span>
                </div>
                <a class="btn" href="/download/zip" download="outils-editeur-anti-copie.zip">⬇️ Télécharger .zip</a>
            </div>

            <!-- GUIDE UTILISATION -->
            <div class="item">
                <div class="item-info">
                    <span class="item-title">
                        📘 Guide d'Utilisation
                        <span class="item-tag">Word &bull; .docx</span>
                    </span>
                    <span class="item-desc">Documentation détaillée : chaîne d'audit SHA-256, triggers financiers et section 13.A anti-copie.</span>
                </div>
                <a class="btn btn-blue" href="/download/docx_utilisation" download="GUIDE_UTILISATION_YELEN_SCHOOL.docx">⬇️ Télécharger .docx</a>
            </div>

            <!-- GUIDE DEPLOIEMENT -->
            <div class="item">
                <div class="item-info">
                    <span class="item-title">
                        📗 Guide de Déploiement Windows
                        <span class="item-tag">Word &bull; .docx</span>
                    </span>
                    <span class="item-desc">Procédure d'installation locale sous Windows, `demarrage.bat` et section 3.5 procédure éditeur.</span>
                </div>
                <a class="btn btn-blue" href="/download/docx_deploiement" download="GUIDE_DEPLOIEMENT_WINDOWS.docx">⬇️ Télécharger .docx</a>
            </div>

            <!-- SCRIPT DEVERROUILLAGE AUTONOME -->
            <div class="item">
                <div class="item-info">
                    <span class="item-title">
                        🔑 Script Déverrouillage Maître
                        <span class="item-tag">Script &bull; .bat</span>
                    </span>
                    <span class="item-desc">Script autonome pour lever les verrous NTFS en cas d'intervention technique.</span>
                </div>
                <a class="btn btn-amber" href="/download/bat_unlock" download="deverrouiller-dossier-anti-copie.bat">⬇️ Télécharger .bat</a>
            </div>
        </div>

        <div class="footer">
            YELEN SCHOOL &copy; 2026 &bull; Plateforme de Gestion Scolaire Sécurisée
        </div>
    </div>
</body>
</html>
"""
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', 8080), DownloadHandler)
    server.serve_forever()
