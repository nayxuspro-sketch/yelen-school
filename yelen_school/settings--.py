# ═══════════════════════════════════════════════════════════════
#  CORRECTIONS À APPORTER DANS yelen_school/settings.py
#  (2 blocs à modifier)
# ═══════════════════════════════════════════════════════════════

# ─────────────────────────────────────────────────────────────
#  CORRECTION 1 — TEMPLATES
#  Problème actuel : 'DIRS': []  →  base.html introuvable
#  Solution : ajouter BASE_DIR / 'templates'
# ─────────────────────────────────────────────────────────────

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],   # ← AJOUTÉ
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]


# ─────────────────────────────────────────────────────────────
#  CORRECTION 2 — STATIC FILES
#  Problème actuel : STATIC_URL seul, sans STATICFILES_DIRS
#  Solution : déclarer le dossier static/ de la racine
# ─────────────────────────────────────────────────────────────

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']   # ← AJOUTÉ
# STATIC_ROOT est utilisé uniquement en production (collectstatic)
# STATIC_ROOT = BASE_DIR / 'staticfiles'


# ═══════════════════════════════════════════════════════════════
#  TIMEZONE — OPTIONNEL MAIS RECOMMANDÉ
#  Burkina Faso = UTC+0 (pas de changement d'heure)
#  Mettre USE_TZ = True + TIME_ZONE = 'Africa/Ouagadougou'
# ═══════════════════════════════════════════════════════════════

TIME_ZONE = 'Africa/Ouagadougou'   # ← REMPLACE 'UTC'
USE_TZ = True


# ═══════════════════════════════════════════════════════════════
#  RÉSUMÉ DES CHANGEMENTS
# ═══════════════════════════════════════════════════════════════
#
#  Avant  | TEMPLATES > DIRS : []
#  Après  | TEMPLATES > DIRS : [BASE_DIR / 'templates']
#
#  Avant  | STATIC_URL = 'static/'  (seul)
#  Après  | + STATICFILES_DIRS = [BASE_DIR / 'static']
#
#  Avant  | TIME_ZONE = 'UTC'
#  Après  | TIME_ZONE = 'Africa/Ouagadougou'
#
# ═══════════════════════════════════════════════════════════════
